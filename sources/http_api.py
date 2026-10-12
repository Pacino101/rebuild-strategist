#!/usr/bin/env python3
"""HTTP data source: connect to the user's own endpoints.

Positioning
-----------
This module **ships no connector for any specific platform** (it presets no
URLs or field mappings for PostHog / Mautic / ad platforms). The user supplies
the URL, the authentication method and the value path.

Security conventions
--------------------
- **Keys are never written into the spec file.** The spec only records "which
  request header corresponds to which environment variable" (`header_env`); the
  real values are read from the environment at runtime and never touch disk.
- If a literal in `headers` looks like a secret, a warning is emitted — a key
  written into a file ends up in git sooner or later.
- No request header value is ever logged or echoed.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .base import Document, SourceError

SPECS_DIRNAME = "specs"

#: Maximum number of documents one fetch may produce, so that an endpoint
#: returning a hundred thousand records cannot blow up the project.
MAX_RECORDS = 500

#: Literals that look like secrets: long random strings with no spaces.
_SECRET_LIKE = re.compile(r"^[A-Za-z0-9_\-\.]{20,}$")

#: These header names can be taken as credentials with near certainty.
_SENSITIVE_HEADERS = {
    "authorization", "x-api-key", "api-key", "apikey", "x-auth-token",
    "cookie", "x-token", "token", "private-token",
}


@dataclass
class HttpSourceSpec:
    """One HTTP fetch spec."""

    name: str
    url: str
    method: str = "GET"
    headers: dict = field(default_factory=dict)
    header_env: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    body: dict | None = None
    records_path: str = ""
    timeout: int = 30

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data) -> "HttpSourceSpec":
        known = set(cls.__dataclass_fields__)
        unknown = set(data) - known
        if unknown:
            raise SourceError(
                f"unknown field in spec: {sorted(unknown)}. "
                f"Available fields: {sorted(known)}"
            )
        if not data.get("name"):
            raise SourceError("spec is missing name")
        if not data.get("url"):
            raise SourceError("spec is missing url")
        return cls(**data)

    @classmethod
    def from_file(cls, path) -> "HttpSourceSpec":
        path = Path(path)
        if not path.exists():
            raise SourceError(f"spec file not found: {path}")
        try:
            return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            raise SourceError(f"{path} is not valid JSON: {exc}") from exc

    # ------------------------------------------------------- security checks
    def warnings(self) -> list[str]:
        problems = []
        for header, value in self.headers.items():
            if header.lower() in _SENSITIVE_HEADERS:
                problems.append(
                    f"header '{header}' is a credential-type field but is written "
                    f"directly into the spec. Use header_env instead "
                    f"(for example \"{header}\": \"MY_TOKEN_ENV\") so the key does "
                    f"not enter git history."
                )
            elif _SECRET_LIKE.match(str(value)):
                problems.append(
                    f"the value of header '{header}' looks like a secret. "
                    f"If it is one, use header_env instead."
                )
        missing = [
            env for env in self.header_env.values()
            if not os.environ.get(env)
        ]
        if missing:
            problems.append(
                f"these environment variables are not set: {', '.join(sorted(missing))}. "
                f"The corresponding request headers will be empty when fetching."
            )
        if self.method.upper() not in ("GET", "POST"):
            problems.append(f"method is {self.method}; this module only implements GET and POST")
        return problems

    def resolved_headers(self) -> dict:
        """Merge literal headers with headers taken from environment variables.
        Values are never logged or echoed."""
        headers = {k: str(v) for k, v in self.headers.items()}
        for header, env_name in self.header_env.items():
            value = os.environ.get(env_name, "")
            if value:
                headers[header] = value
        return headers


# ---------------------------------------------------------------------------
# Value path
# ---------------------------------------------------------------------------

def extract_records(payload, records_path: str):
    """Pull a set of records out of the response along a dot-separated path.

    An empty path returns [payload] (the whole response as one document).
    """
    if not records_path:
        return [payload]
    node = payload
    for part in records_path.split("."):
        if isinstance(node, dict):
            if part not in node:
                raise SourceError(
                    f"'{part}' in records_path does not exist. "
                    f"Available fields at this level: {sorted(node)[:10]}"
                )
            node = node[part]
        elif isinstance(node, list):
            try:
                node = node[int(part)]
            except (ValueError, IndexError):
                raise SourceError(
                    f"'{part}' in records_path cannot be used as a list index "
                    f"(the current level is a list of length {len(node)})"
                ) from None
        else:
            raise SourceError(
                f"records_path reached a scalar at '{part}' and cannot descend further"
            )
    return node if isinstance(node, list) else [node]


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def fetch(spec: HttpSourceSpec):
    """Perform one fetch. Returns (records, meta). Network or HTTP errors raise
    SourceError."""
    url = spec.url
    headers = spec.resolved_headers()
    headers.setdefault("Accept", "application/json, text/plain;q=0.9, */*;q=0.5")
    data = None

    if spec.params:
        joiner = "&" if urllib.parse.urlparse(url).query else "?"
        url = url + joiner + urllib.parse.urlencode(spec.params)

    if spec.method.upper() == "POST":
        data = json.dumps(spec.body or {}).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")

    request = urllib.request.Request(url, data=data, headers=headers,
                                     method=spec.method.upper())
    try:
        with urllib.request.urlopen(request, timeout=spec.timeout) as response:
            raw = response.read()
            status = response.status
            content_type = response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        snippet = ""
        try:
            snippet = exc.read().decode("utf-8", errors="replace")[:200]
        except Exception:  # noqa: BLE001 - must not mask the original error
            pass
        raise SourceError(
            f"HTTP {exc.code}: {exc.reason}\n"
            f"URL: {_redact(url)}\n"
            + (f"Response snippet: {snippet}\n" if snippet else "")
            + "Check the URL, the authentication headers and the permission scope."
        ) from exc
    except urllib.error.URLError as exc:
        raise SourceError(
            f"cannot connect: {_redact(url)}\nReason: {exc.reason}"
        ) from exc
    except TimeoutError as exc:
        raise SourceError(f"request timed out ({spec.timeout}s): {_redact(url)}") from exc

    text = raw.decode("utf-8", errors="replace")
    meta = {
        "kind": "http",
        "spec": spec.name,
        "url": _redact(url),
        "status": status,
        "content_type": content_type,
        "bytes": len(raw),
    }

    parsed = None
    if "json" in content_type.lower() or text.lstrip()[:1] in "[{":
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None

    if parsed is None:
        return [text], meta

    records = extract_records(parsed, spec.records_path)
    if len(records) > MAX_RECORDS:
        meta["truncated_records"] = True
        meta["original_records"] = len(records)
        records = records[:MAX_RECORDS]
    return records, meta


def _redact(url: str) -> str:
    """Strip userinfo and sensitive query parameters from a URL so it can be
    printed safely."""
    parts = urllib.parse.urlsplit(url)
    netloc = parts.netloc
    if "@" in netloc:
        netloc = netloc.rsplit("@", 1)[1]
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    safe = [
        (k, "***" if k.lower() in {"token", "key", "api_key", "apikey",
                                   "access_token", "secret", "password"} else v)
        for k, v in query
    ]
    return urllib.parse.urlunsplit((
        parts.scheme, netloc, parts.path,
        urllib.parse.urlencode(safe), parts.fragment,
    ))


def render(record) -> str:
    """Render one record as document content."""
    if isinstance(record, str):
        return record
    return json.dumps(record, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# spec storage
# ---------------------------------------------------------------------------

def specs_dir(project_dir) -> Path:
    return Path(project_dir) / "sources" / SPECS_DIRNAME


def save_spec(project_dir, spec: HttpSourceSpec) -> Path:
    directory = specs_dir(project_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{spec.name}.json"
    path.write_text(
        json.dumps(spec.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def load_specs(project_dir) -> list[HttpSourceSpec]:
    directory = specs_dir(project_dir)
    if not directory.exists():
        return []
    return [HttpSourceSpec.from_file(p) for p in sorted(directory.glob("*.json"))]


def add_http(store, spec: HttpSourceSpec) -> list[Document]:
    """Perform the fetch and store the results in the material library."""
    records, meta = fetch(spec)
    documents = []
    for index, record in enumerate(records, 1):
        record_meta = dict(meta)
        record_meta["record_index"] = index
        record_meta["record_total"] = len(records)
        origin = meta["url"] if len(records) == 1 else f"{meta['url']}#{index}"
        documents.append(store.add(
            origin=origin,
            content=render(record),
            media_type="application/json",
            meta=record_meta,
        ))
    return documents
