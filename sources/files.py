#!/usr/bin/env python3
"""本地文件数据源。

支持：CSV / TSV / JSON / JSONL / TXT / MD / XLSX。

两处刻意为之的设计：

1. **中文编码兜底。** 中文用户导出的 CSV 十有八九是 GBK 或带 BOM 的 UTF-8。
   直接按 UTF-8 打开会整片乱码，而乱码喂进模型比没有数据更糟——
   模型会照着乱码编。因此按 utf-8-sig → utf-8 → gb18030 → latin-1 依次尝试。

2. **XLSX 用标准库解析。** xlsx 本质是 zip + XML，用 zipfile 与
   xml.etree 足以读出首个工作表的值。这样就不必为了读一个 Excel
   而给整个项目引入 pandas / openpyxl 依赖。
"""
from __future__ import annotations

import csv
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .base import Document, SourceError

#: 依次尝试的编码。gb18030 覆盖 GBK/GB2312，放在 utf-8 之后。
ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "big5", "latin-1")

TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".log"}
JSON_SUFFIXES = {".json"}
JSONL_SUFFIXES = {".jsonl", ".ndjson"}
CSV_SUFFIXES = {".csv", ".tsv"}
XLSX_SUFFIXES = {".xlsx", ".xlsm"}

SUPPORTED_SUFFIXES = (
    TEXT_SUFFIXES | JSON_SUFFIXES | JSONL_SUFFIXES | CSV_SUFFIXES | XLSX_SUFFIXES
)

#: JSON 美化输出的行数上限，超过就不美化（避免小文件变大文件）。
PRETTY_JSON_MAX_CHARS = 50_000


def decode_bytes(raw: bytes) -> tuple[str, str]:
    """按候选编码解码，返回 (文本, 采用的编码)。"""
    for encoding in ENCODINGS:
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise SourceError("无法用任何候选编码解码该文件（已尝试 utf-8 / gb18030 / big5 / latin-1）")


def read_file(path) -> tuple[str, str, dict]:
    """读取一个文件，返回 (内容, media_type, meta)。"""
    path = Path(path)
    if not path.exists():
        raise SourceError(f"文件不存在：{path}")
    if not path.is_file():
        raise SourceError(f"不是文件：{path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
        raise SourceError(
            f"不支持的文件类型 {suffix or '(无扩展名)'}。支持：{supported}\n"
            f"如果这是纯文本，请改名为 .txt。"
        )

    if suffix in XLSX_SUFFIXES:
        return _read_xlsx(path)

    raw = path.read_bytes()
    text, encoding = decode_bytes(raw)
    meta = {"bytes": len(raw), "encoding": encoding, "filename": path.name}

    if suffix in CSV_SUFFIXES:
        return _read_csv(text, suffix, meta)
    if suffix in JSON_SUFFIXES:
        return _read_json(text, meta)
    if suffix in JSONL_SUFFIXES:
        return _read_jsonl(text, meta)

    meta["lines"] = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    return text, "text/markdown" if suffix in {".md", ".markdown"} else "text/plain", meta


def _read_csv(text: str, suffix: str, meta: dict) -> tuple[str, str, dict]:
    delimiter = "\t" if suffix == ".tsv" else ","
    try:
        rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    except csv.Error as exc:
        raise SourceError(f"CSV 解析失败：{exc}") from exc

    rows = [r for r in rows if any(cell.strip() for cell in r)]
    meta["rows"] = max(len(rows) - 1, 0)
    meta["columns"] = len(rows[0]) if rows else 0
    if rows:
        meta["header"] = rows[0][:40]
    return text, "text/csv", meta


def _read_json(text: str, meta: dict) -> tuple[str, str, dict]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SourceError(f"JSON 解析失败（第 {exc.lineno} 行）：{exc.msg}") from exc

    if isinstance(data, list):
        meta["records"] = len(data)
    elif isinstance(data, dict):
        meta["keys"] = list(data.keys())[:40]

    if len(text) <= PRETTY_JSON_MAX_CHARS:
        text = json.dumps(data, ensure_ascii=False, indent=2)
    return text, "application/json", meta


def _read_jsonl(text: str, meta: dict) -> tuple[str, str, dict]:
    lines = [line for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines, 1):
        try:
            json.loads(line)
        except json.JSONDecodeError as exc:
            raise SourceError(f"JSONL 第 {index} 行不是合法 JSON：{exc.msg}") from exc
    meta["records"] = len(lines)
    return text, "application/x-ndjson", meta


# ---------------------------------------------------------------------------
# XLSX（标准库实现）
# ---------------------------------------------------------------------------

_NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _read_xlsx(path: Path) -> tuple[str, str, dict]:
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            shared = _xlsx_shared_strings(archive, names)
            sheet_name = _xlsx_first_sheet(archive, names)
            if sheet_name is None:
                raise SourceError(f"{path.name} 中找不到工作表")
            rows = _xlsx_rows(archive.read(sheet_name), shared)
    except zipfile.BadZipFile as exc:
        raise SourceError(
            f"{path.name} 不是有效的 xlsx（可能是 .xls 旧格式或被改名）。"
            f"请用 Excel 另存为 .xlsx 或 .csv。"
        ) from exc
    except ET.ParseError as exc:
        raise SourceError(f"{path.name} 的 XML 结构无法解析：{exc}") from exc

    rows = [r for r in rows if any(cell.strip() for cell in r)]
    meta = {
        "filename": path.name,
        "sheet": sheet_name.rsplit("/", 1)[-1],
        "rows": max(len(rows) - 1, 0),
        "columns": len(rows[0]) if rows else 0,
    }
    if rows:
        meta["header"] = rows[0][:40]

    lines = ["\t".join(rows[0])] if rows else []
    lines += ["\t".join(r) for r in rows[1:]]
    return "\n".join(lines), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", meta


def _xlsx_shared_strings(archive, names) -> list[str]:
    if "xl/sharedStrings.xml" not in names:
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    strings = []
    for si in root.findall("main:si", _NS):
        # 一个 <si> 可能由多个 <t> 片段组成（富文本）
        strings.append("".join(t.text or "" for t in si.iter(
            "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"
        )))
    return strings


def _xlsx_first_sheet(archive, names):
    """取工作簿里第一个工作表的 XML 路径。"""
    if "xl/workbook.xml" in names:
        try:
            root = ET.fromstring(archive.read("xl/workbook.xml"))
            rel_ns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            sheet = root.find("main:sheets/main:sheet", _NS)
            if sheet is not None:
                rel_id = sheet.get(rel_ns)
                target = _xlsx_rel_target(archive, names, rel_id)
                if target:
                    return target
        except ET.ParseError:
            pass
    for fallback in ("xl/worksheets/sheet1.xml", "xl/worksheets/sheet.xml"):
        if fallback in names:
            return fallback
    candidates = sorted(n for n in names if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
    return candidates[0] if candidates else None


def _xlsx_rel_target(archive, names, rel_id):
    if not rel_id or "xl/_rels/workbook.xml.rels" not in names:
        return None
    root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    for rel in root:
        if rel.get("Id") == rel_id:
            target = rel.get("Target", "")
            if target.startswith("/"):
                return target.lstrip("/")
            return "xl/" + target.lstrip("./")
    return None


def _column_index(cell_ref: str) -> int:
    """A1 -> 0, B1 -> 1, AA1 -> 26。用于补齐被跳过的空单元格。"""
    letters = re.match(r"([A-Z]+)", cell_ref or "")
    if not letters:
        return 0
    index = 0
    for char in letters.group(1):
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index - 1


def _xlsx_rows(xml_bytes: bytes, shared: list[str]) -> list[list[str]]:
    root = ET.fromstring(xml_bytes)
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rows = []
    for row in root.iter(f"{ns}row"):
        cells = {}
        for position, cell in enumerate(row.findall(f"{ns}c")):
            ref = cell.get("r")
            index = _column_index(ref) if ref else position
            kind = cell.get("t")
            value = ""
            if kind == "inlineStr":
                node = cell.find(f"{ns}is")
                if node is not None:
                    value = "".join(t.text or "" for t in node.iter(f"{ns}t"))
            else:
                node = cell.find(f"{ns}v")
                if node is not None and node.text is not None:
                    value = node.text
                    if kind == "s":
                        try:
                            value = shared[int(value)]
                        except (ValueError, IndexError):
                            value = ""
            cells[index] = value
        width = max(cells) + 1 if cells else 0
        rows.append([cells.get(i, "") for i in range(width)])
    return rows


# ---------------------------------------------------------------------------
# 便捷入口
# ---------------------------------------------------------------------------

def add_file(store, path) -> Document:
    """读一个本地文件并存入项目的材料库。"""
    path = Path(path)
    content, media_type, meta = read_file(path)
    meta["kind"] = "file"
    return store.add(origin=str(path), content=content, media_type=media_type, meta=meta)
