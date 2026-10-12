#!/usr/bin/env python3
"""Local file data source.

Supports: CSV / TSV / JSON / JSONL / TXT / MD / XLSX.

Two deliberate design decisions:

1. **Chinese encoding fallback.** A CSV exported by a Chinese user is nine times
   out of ten GBK, or UTF-8 with a BOM. Opening it as plain UTF-8 turns the
   whole file into mojibake, and mojibake fed to a model is worse than no data
   at all — the model will fabricate along the mojibake. So encodings are tried
   in order: utf-8-sig → utf-8 → gb18030 → latin-1.

2. **XLSX is parsed with the standard library.** An xlsx is essentially zip +
   XML, and zipfile plus xml.etree are enough to read the values of the first
   worksheet. That avoids pulling pandas / openpyxl into the whole project just
   to read a single Excel file.
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

#: Encodings tried in order. gb18030 covers GBK/GB2312 and comes after utf-8.
ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "big5", "latin-1")

TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".log"}
JSON_SUFFIXES = {".json"}
JSONL_SUFFIXES = {".jsonl", ".ndjson"}
CSV_SUFFIXES = {".csv", ".tsv"}
XLSX_SUFFIXES = {".xlsx", ".xlsm"}

SUPPORTED_SUFFIXES = (
    TEXT_SUFFIXES | JSON_SUFFIXES | JSONL_SUFFIXES | CSV_SUFFIXES | XLSX_SUFFIXES
)

#: Line-count ceiling for pretty-printed JSON output; beyond it the output is
#: left unformatted (so a small file does not turn into a big one).
PRETTY_JSON_MAX_CHARS = 50_000


def decode_bytes(raw: bytes) -> tuple[str, str]:
    """Decode using the candidate encodings; returns (text, encoding used)."""
    for encoding in ENCODINGS:
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise SourceError("cannot decode this file with any candidate encoding (tried utf-8 / gb18030 / big5 / latin-1)")


def read_file(path) -> tuple[str, str, dict]:
    """Read one file; returns (content, media_type, meta)."""
    path = Path(path)
    if not path.exists():
        raise SourceError(f"file does not exist: {path}")
    if not path.is_file():
        raise SourceError(f"not a file: {path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
        raise SourceError(
            f"unsupported file type {suffix or '(no extension)'}. Supported: {supported}\n"
            f"If this is plain text, rename it to .txt."
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
        raise SourceError(f"CSV parse failed: {exc}") from exc

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
        raise SourceError(f"JSON parse failed (line {exc.lineno}): {exc.msg}") from exc

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
            raise SourceError(f"JSONL line {index} is not valid JSON: {exc.msg}") from exc
    meta["records"] = len(lines)
    return text, "application/x-ndjson", meta


# ---------------------------------------------------------------------------
# XLSX (standard-library implementation)
# ---------------------------------------------------------------------------

_NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _read_xlsx(path: Path) -> tuple[str, str, dict]:
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            shared = _xlsx_shared_strings(archive, names)
            sheet_name = _xlsx_first_sheet(archive, names)
            if sheet_name is None:
                raise SourceError(f"no worksheet found in {path.name}")
            rows = _xlsx_rows(archive.read(sheet_name), shared)
    except zipfile.BadZipFile as exc:
        raise SourceError(
            f"{path.name} is not a valid xlsx (it may be the old .xls format or a renamed file). "
            f"Please use Excel to save it as .xlsx or .csv."
        ) from exc
    except ET.ParseError as exc:
        raise SourceError(f"the XML structure of {path.name} cannot be parsed: {exc}") from exc

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
        # A single <si> may be made of several <t> fragments (rich text)
        strings.append("".join(t.text or "" for t in si.iter(
            "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"
        )))
    return strings


def _xlsx_first_sheet(archive, names):
    """Return the XML path of the first worksheet in the workbook."""
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
    """A1 -> 0, B1 -> 1, AA1 -> 26. Used to pad skipped empty cells."""
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
# Convenience entry points
# ---------------------------------------------------------------------------

def add_file(store, path) -> Document:
    """Read one local file and store it in the project's material library."""
    path = Path(path)
    content, media_type, meta = read_file(path)
    meta["kind"] = "file"
    return store.add(origin=str(path), content=content, media_type=media_type, meta=meta)
