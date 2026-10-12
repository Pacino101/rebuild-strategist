"""数据源层测试。

覆盖：中文编码兜底、CSV/JSON/JSONL/XLSX 解析、文档哈希与完整性校验、
HTTP 取数与密钥处理。

XLSX 夹具用标准库 zipfile 手工构造，因此测试不依赖 openpyxl——
CI 上也不需要装任何东西。
"""
import json
import os
import sys
import tempfile
import unittest
import urllib.error
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sources import (  # noqa: E402
    DocumentStore,
    MAX_CONTENT_CHARS,
    SourceError,
    files,
    http_api,
    sha256_of,
)

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def make_xlsx(path, rows, with_workbook=True):
    """构造一个最小 xlsx：字符串走 sharedStrings，数字走 <v>。"""
    shared = []

    def sid(value):
        if value not in shared:
            shared.append(value)
        return shared.index(value)

    sheet_rows = []
    for r, row in enumerate(rows, 1):
        cells = []
        for c, value in enumerate(row):
            ref = f"{chr(ord('A') + c)}{r}"
            if isinstance(value, str):
                cells.append(f'<c r="{ref}" t="s"><v>{sid(value)}</v></c>')
            else:
                cells.append(f'<c r="{ref}"><v>{value}</v></c>')
        sheet_rows.append(f'<row r="{r}">{"".join(cells)}</row>')

    sheet = (f'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="{MAIN_NS}">'
             f'<sheetData>{"".join(sheet_rows)}</sheetData></worksheet>')
    shared_xml = (f'<?xml version="1.0" encoding="UTF-8"?><sst xmlns="{MAIN_NS}">'
                  + "".join(f"<si><t>{v}</t></si>" for v in shared) + "</sst>")

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
        archive.writestr("xl/sharedStrings.xml", shared_xml)
        if with_workbook:
            archive.writestr("xl/workbook.xml",
                             f'<?xml version="1.0"?><workbook xmlns="{MAIN_NS}" '
                             f'xmlns:r="{REL_NS}"><sheets>'
                             f'<sheet name="Sheet1" sheetId="1" r:id="rId1"/>'
                             f'</sheets></workbook>')
            archive.writestr("xl/_rels/workbook.xml.rels",
                             f'<?xml version="1.0"?><Relationships xmlns="{PKG_NS}">'
                             f'<Relationship Id="rId1" Target="worksheets/sheet1.xml"/>'
                             f'</Relationships>')
    return path


class TempDirCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


# ---------------------------------------------------------------- 文件解析

class EncodingTests(TempDirCase):
    def test_utf8_bom_is_stripped(self):
        path = self.dir / "bom.csv"
        path.write_bytes("\ufeff名称,数量\n春茶,10\n".encode("utf-8"))
        content, _, meta = files.read_file(path)
        self.assertFalse(content.startswith("\ufeff"))
        self.assertIn("春茶", content)
        self.assertEqual(meta["encoding"], "utf-8-sig")

    def test_gbk_csv_is_readable(self):
        # 中文用户导出的 CSV 十有八九是 GBK
        path = self.dir / "gbk.csv"
        path.write_bytes("名称,数量\n春茶,10\n".encode("gb18030"))
        content, _, meta = files.read_file(path)
        self.assertIn("春茶", content)
        self.assertIn(meta["encoding"], ("gb18030", "gbk"))

    def test_undecodable_bytes_fall_back_to_latin1(self):
        path = self.dir / "weird.txt"
        path.write_bytes(b"\xff\xfe\x00abc")
        content, _, _ = files.read_file(path)
        self.assertIsInstance(content, str)


class CsvTests(TempDirCase):
    def test_csv_row_and_column_counts(self):
        path = self.dir / "orders.csv"
        path.write_text("sku,qty\nA,1\nB,2\n", encoding="utf-8")
        content, media, meta = files.read_file(path)
        self.assertEqual(media, "text/csv")
        self.assertEqual(meta["rows"], 2)
        self.assertEqual(meta["columns"], 2)
        self.assertEqual(meta["header"], ["sku", "qty"])

    def test_tsv_uses_tab_delimiter(self):
        path = self.dir / "t.tsv"
        path.write_text("a\tb\n1\t2\n", encoding="utf-8")
        _, _, meta = files.read_file(path)
        self.assertEqual(meta["columns"], 2)

    def test_blank_lines_ignored(self):
        path = self.dir / "b.csv"
        path.write_text("a,b\n\n\n1,2\n\n", encoding="utf-8")
        _, _, meta = files.read_file(path)
        self.assertEqual(meta["rows"], 1)


class JsonTests(TempDirCase):
    def test_json_is_pretty_printed(self):
        path = self.dir / "d.json"
        path.write_text('{"a":1,"b":[2,3]}', encoding="utf-8")
        content, media, meta = files.read_file(path)
        self.assertIn("\n", content)
        self.assertEqual(media, "application/json")
        self.assertEqual(meta["keys"], ["a", "b"])

    def test_broken_json_reports_line(self):
        path = self.dir / "bad.json"
        path.write_text('{"a": }', encoding="utf-8")
        with self.assertRaises(SourceError) as ctx:
            files.read_file(path)
        self.assertIn("JSON 解析失败", str(ctx.exception))

    def test_jsonl_records(self):
        path = self.dir / "d.jsonl"
        path.write_text('{"a":1}\n{"a":2}\n', encoding="utf-8")
        _, _, meta = files.read_file(path)
        self.assertEqual(meta["records"], 2)

    def test_jsonl_bad_line_reports_number(self):
        path = self.dir / "bad.jsonl"
        path.write_text('{"a":1}\nnot json\n', encoding="utf-8")
        with self.assertRaises(SourceError) as ctx:
            files.read_file(path)
        self.assertIn("第 2 行", str(ctx.exception))


class XlsxTests(TempDirCase):
    def test_reads_header_and_values(self):
        path = make_xlsx(self.dir / "s.xlsx", [["sku", "qty"], ["A", 1], ["B", 2]])
        content, _, meta = files.read_file(path)
        self.assertIn("sku\tqty", content)
        self.assertIn("A\t1", content)
        self.assertEqual(meta["rows"], 2)
        self.assertEqual(meta["columns"], 2)

    def test_works_without_workbook_xml(self):
        # 走 sheet1.xml 回退分支
        path = make_xlsx(self.dir / "min.xlsx", [["x"], ["y"]], with_workbook=False)
        content, _, _ = files.read_file(path)
        self.assertIn("x", content)
        self.assertIn("y", content)

    def test_renamed_xls_is_reported_clearly(self):
        path = self.dir / "fake.xlsx"
        path.write_bytes(b"this is not a zip")
        with self.assertRaises(SourceError) as ctx:
            files.read_file(path)
        self.assertIn("不是有效的 xlsx", str(ctx.exception))

    def test_empty_cells_are_padded(self):
        path = self.dir / "gap.xlsx"
        make_xlsx(path, [["a", "", "c"]])
        content, _, _ = files.read_file(path)
        self.assertEqual(content.split("\t"), ["a", "", "c"])


class UnsupportedTests(TempDirCase):
    def test_unknown_extension_is_rejected(self):
        path = self.dir / "x.pdf"
        path.write_bytes(b"%PDF")
        with self.assertRaises(SourceError) as ctx:
            files.read_file(path)
        self.assertIn("不支持的文件类型", str(ctx.exception))

    def test_missing_file(self):
        with self.assertRaises(SourceError):
            files.read_file(self.dir / "nope.csv")


# ---------------------------------------------------------------- 文档库

class DocumentStoreTests(TempDirCase):
    def setUp(self):
        super().setUp()
        self.store = DocumentStore(self.dir)

    def test_add_assigns_id_and_hash(self):
        document = self.store.add("origin", "内容", "text/plain")
        self.assertEqual(document.doc_id, "DOC-001")
        self.assertEqual(document.sha256, sha256_of("内容"))

    def test_ids_increment(self):
        self.assertEqual(self.store.add("o", "a").doc_id, "DOC-001")
        self.assertEqual(self.store.add("o", "b").doc_id, "DOC-002")

    def test_get_roundtrip_and_verify(self):
        self.store.add("o", "材料")
        self.assertTrue(self.store.verify("DOC-001"))
        self.assertEqual(self.store.get("DOC-001").content, "材料")

    def test_verify_detects_tampering(self):
        self.store.add("o", "原始")
        path = self.store.documents_dir / "DOC-001.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["content"] = "被改过"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        self.assertFalse(self.store.verify("DOC-001"))

    def test_index_excludes_content(self):
        self.store.add("o", "abcdef")
        entry = self.store.list()[0]
        self.assertNotIn("content", entry)
        self.assertEqual(entry["origin"], "o")

    def test_missing_document_raises(self):
        with self.assertRaises(SourceError):
            self.store.get("DOC-999")

    def test_oversized_content_truncated_and_marked(self):
        self.store.add("o", "x" * (MAX_CONTENT_CHARS + 500))
        document = self.store.get("DOC-001")
        self.assertTrue(document.meta["truncated"])
        self.assertEqual(document.meta["kept_chars"], MAX_CONTENT_CHARS)
        self.assertEqual(len(document.content), MAX_CONTENT_CHARS)

    def test_add_file_end_to_end(self):
        path = self.dir / "orders.csv"
        path.write_text("sku,qty\nA,1\n", encoding="utf-8")
        document = files.add_file(self.store, path)
        self.assertEqual(document.meta["kind"], "file")
        self.assertEqual(document.meta["rows"], 1)


# ---------------------------------------------------------------- HTTP 源

class FakeResponse:
    def __init__(self, body, status=200, content_type="application/json"):
        self._body = body if isinstance(body, bytes) else body.encode("utf-8")
        self.status = status
        self.headers = {"Content-Type": content_type}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class ExtractRecordsTests(unittest.TestCase):
    def test_empty_path_returns_payload(self):
        self.assertEqual(http_api.extract_records({"a": 1}, ""), [{"a": 1}])

    def test_dotted_path(self):
        payload = {"data": {"items": [1, 2]}}
        self.assertEqual(http_api.extract_records(payload, "data.items"), [1, 2])

    def test_list_index_path(self):
        payload = {"data": [{"x": 1}, {"x": 2}]}
        self.assertEqual(http_api.extract_records(payload, "data.1"), [{"x": 2}])

    def test_missing_key_lists_available(self):
        with self.assertRaises(SourceError) as ctx:
            http_api.extract_records({"data": {}}, "data.items")
        self.assertIn("可用字段", str(ctx.exception))

    def test_scalar_branch_errors(self):
        with self.assertRaises(SourceError):
            http_api.extract_records({"a": 1}, "a.b")


class RedactTests(unittest.TestCase):
    def test_strips_userinfo(self):
        self.assertNotIn("secret", http_api._redact("https://user:secret@example.com/x"))

    def test_masks_sensitive_query_params(self):
        redacted = http_api._redact("https://e.com/x?token=abc123&page=2")
        self.assertNotIn("abc123", redacted)
        self.assertIn("page=2", redacted)


class SpecSafetyTests(unittest.TestCase):
    def test_literal_credential_header_warns(self):
        spec = http_api.HttpSourceSpec(
            name="s", url="https://e.com",
            headers={"Authorization": "Bearer abc"},
        )
        self.assertTrue(any("header_env" in w for w in spec.warnings()))

    def test_secret_looking_value_warns(self):
        spec = http_api.HttpSourceSpec(
            name="s", url="https://e.com",
            headers={"X-Custom": "abcdefghijklmnopqrstuvwxyz123456"},
        )
        self.assertTrue(any("像是密钥" in w for w in spec.warnings()))

    def test_unset_env_var_warns(self):
        spec = http_api.HttpSourceSpec(
            name="s", url="https://e.com",
            header_env={"Authorization": "DEFINITELY_NOT_SET_ENV_XYZ"},
        )
        self.assertTrue(any("未设置" in w for w in spec.warnings()))

    def test_env_var_is_resolved_at_runtime(self):
        spec = http_api.HttpSourceSpec(
            name="s", url="https://e.com",
            header_env={"Authorization": "MY_TEST_TOKEN"},
        )
        with mock.patch.dict(os.environ, {"MY_TEST_TOKEN": "resolved"}, clear=False):
            self.assertEqual(spec.resolved_headers()["Authorization"], "resolved")

    def test_unknown_spec_field_rejected(self):
        with self.assertRaises(SourceError) as ctx:
            http_api.HttpSourceSpec.from_dict(
                {"name": "s", "url": "https://e.com", "typo_field": 1}
            )
        self.assertIn("未知字段", str(ctx.exception))

    def test_spec_missing_url_rejected(self):
        with self.assertRaises(SourceError):
            http_api.HttpSourceSpec.from_dict({"name": "s"})


class FetchTests(TempDirCase):
    def _spec(self, **overrides):
        base = {"name": "s", "url": "https://api.example.com/orders"}
        base.update(overrides)
        return http_api.HttpSourceSpec(**base)

    def test_fetch_json_records(self):
        payload = json.dumps({"data": {"items": [{"id": 1}, {"id": 2}]}})
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse(payload)):
            records, meta = http_api.fetch(self._spec(records_path="data.items"))
        self.assertEqual(len(records), 2)
        self.assertEqual(meta["status"], 200)

    def test_http_error_explains_and_redacts(self):
        error = urllib.error.HTTPError(
            "https://api.example.com/orders?token=SECRET", 401, "Unauthorized", {}, None
        )
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(SourceError) as ctx:
                http_api.fetch(self._spec())
        message = str(ctx.exception)
        self.assertIn("401", message)
        self.assertNotIn("SECRET", message)

    def test_connection_error_is_reported(self):
        with mock.patch("urllib.request.urlopen",
                        side_effect=urllib.error.URLError("dns failure")):
            with self.assertRaises(SourceError) as ctx:
                http_api.fetch(self._spec())
        self.assertIn("无法连接", str(ctx.exception))

    def test_non_json_body_becomes_single_document(self):
        with mock.patch("urllib.request.urlopen",
                        return_value=FakeResponse("hello", content_type="text/plain")):
            records, _ = http_api.fetch(self._spec())
        self.assertEqual(records, ["hello"])

    def test_record_cap_applied(self):
        payload = json.dumps({"items": list(range(http_api.MAX_RECORDS + 20))})
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse(payload)):
            records, meta = http_api.fetch(self._spec(records_path="items"))
        self.assertEqual(len(records), http_api.MAX_RECORDS)
        self.assertTrue(meta["truncated_records"])

    def test_add_http_stores_documents(self):
        store = DocumentStore(self.dir)
        payload = json.dumps({"items": [{"id": 1}, {"id": 2}]})
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse(payload)):
            documents = http_api.add_http(store, self._spec(records_path="items"))
        self.assertEqual([d.doc_id for d in documents], ["DOC-001", "DOC-002"])
        self.assertTrue(store.verify("DOC-001"))

    def test_get_method_sends_no_body(self):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["data"] = request.data
            captured["method"] = request.get_method()
            return FakeResponse("{}")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            http_api.fetch(self._spec())
        self.assertIsNone(captured["data"])
        self.assertEqual(captured["method"], "GET")

    def test_post_method_sends_json_body(self):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["data"] = request.data
            captured["method"] = request.get_method()
            return FakeResponse("{}")

        spec = self._spec(method="POST", body={"from": "2026-01-01"})
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            http_api.fetch(spec)
        self.assertEqual(captured["method"], "POST")
        self.assertIn(b"2026-01-01", captured["data"])


class SpecStorageTests(TempDirCase):
    def test_save_and_load_roundtrip(self):
        spec = http_api.HttpSourceSpec(
            name="orders", url="https://e.com/o",
            header_env={"Authorization": "TOK"}, records_path="data",
        )
        path = http_api.save_spec(self.dir, spec)
        self.assertTrue(path.exists())
        loaded = http_api.load_specs(self.dir)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].records_path, "data")

    def test_saved_spec_contains_no_secret_value(self):
        spec = http_api.HttpSourceSpec(
            name="orders", url="https://e.com/o",
            header_env={"Authorization": "MY_TOKEN_ENV"},
        )
        with mock.patch.dict(os.environ, {"MY_TOKEN_ENV": "super-secret-value"}):
            path = http_api.save_spec(self.dir, spec)
        self.assertNotIn("super-secret-value", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
