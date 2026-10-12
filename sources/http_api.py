#!/usr/bin/env python3
"""HTTP 数据源：接使用者自己的端点。

定位
----
本模块**不内置任何具体平台的连接器**（不预置 PostHog / Mautic / 广告平台
的 URL 或字段映射）。使用者自己给出 URL、鉴权方式和取值路径。

安全约定
--------
- **密钥不写进 spec 文件。** spec 里只记录「哪个请求头对应哪个环境变量」
  （`header_env`），真实值在运行时从环境变量读取，不落盘。
- 若检测到 `headers` 里像是密钥的字面量，会给出警告——写在文件里的密钥
  迟早会进 git。
- 不记录、不回显任何请求头的值。
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

#: 一次抓取最多产生多少条文档，防止一个接口返回十万条把项目撑爆。
MAX_RECORDS = 500

#: 看起来像密钥的字面量：长且无空格的随机串。
_SECRET_LIKE = re.compile(r"^[A-Za-z0-9_\-\.]{20,}$")

#: 这些请求头名基本可以断定是凭据。
_SENSITIVE_HEADERS = {
    "authorization", "x-api-key", "api-key", "apikey", "x-auth-token",
    "cookie", "x-token", "token", "private-token",
}


@dataclass
class HttpSourceSpec:
    """一个 HTTP 取数配置。"""

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
                f"spec 中出现未知字段：{sorted(unknown)}。"
                f"可用字段：{sorted(known)}"
            )
        if not data.get("name"):
            raise SourceError("spec 缺少 name")
        if not data.get("url"):
            raise SourceError("spec 缺少 url")
        return cls(**data)

    @classmethod
    def from_file(cls, path) -> "HttpSourceSpec":
        path = Path(path)
        if not path.exists():
            raise SourceError(f"找不到 spec 文件：{path}")
        try:
            return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            raise SourceError(f"{path} 不是合法 JSON：{exc}") from exc

    # ------------------------------------------------------------- 安全检查
    def warnings(self) -> list[str]:
        problems = []
        for header, value in self.headers.items():
            if header.lower() in _SENSITIVE_HEADERS:
                problems.append(
                    f"请求头 '{header}' 是凭据类字段，但直接写在了 spec 里。"
                    f"请改用 header_env（例如 \"{header}\": \"MY_TOKEN_ENV\"），"
                    f"避免密钥进入 git 历史。"
                )
            elif _SECRET_LIKE.match(str(value)):
                problems.append(
                    f"请求头 '{header}' 的值像是密钥。若确实是，请改用 header_env。"
                )
        missing = [
            env for env in self.header_env.values()
            if not os.environ.get(env)
        ]
        if missing:
            problems.append(
                f"以下环境变量当前未设置：{', '.join(sorted(missing))}。"
                f"取数时对应请求头将为空。"
            )
        if self.method.upper() not in ("GET", "POST"):
            problems.append(f"method 为 {self.method}，本模块只实现了 GET 与 POST")
        return problems

    def resolved_headers(self) -> dict:
        """合并字面量与来自环境变量的请求头。不记录、不回显值。"""
        headers = {k: str(v) for k, v in self.headers.items()}
        for header, env_name in self.header_env.items():
            value = os.environ.get(env_name, "")
            if value:
                headers[header] = value
        return headers


# ---------------------------------------------------------------------------
# 取值路径
# ---------------------------------------------------------------------------

def extract_records(payload, records_path: str):
    """按点分路径从响应里取出一组记录。

    路径为空时返回 [payload]（整体作为一条文档）。
    """
    if not records_path:
        return [payload]
    node = payload
    for part in records_path.split("."):
        if isinstance(node, dict):
            if part not in node:
                raise SourceError(
                    f"records_path 中的 '{part}' 不存在。"
                    f"该层可用字段：{sorted(node)[:10]}"
                )
            node = node[part]
        elif isinstance(node, list):
            try:
                node = node[int(part)]
            except (ValueError, IndexError):
                raise SourceError(
                    f"records_path 中的 '{part}' 无法作为列表下标（当前层是列表，"
                    f"长度 {len(node)}）"
                ) from None
        else:
            raise SourceError(f"records_path 走到 '{part}' 时已是标量，无法继续下钻")
    return node if isinstance(node, list) else [node]


# ---------------------------------------------------------------------------
# 抓取
# ---------------------------------------------------------------------------

def fetch(spec: HttpSourceSpec):
    """执行一次抓取。返回 (records, meta)。网络或 HTTP 错误抛 SourceError。"""
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
        except Exception:  # noqa: BLE001 - 读错误响应体失败不应掩盖原始错误
            pass
        raise SourceError(
            f"HTTP {exc.code}：{exc.reason}\n"
            f"地址：{_redact(url)}\n"
            + (f"响应片段：{snippet}\n" if snippet else "")
            + "请检查 URL、鉴权头与权限范围。"
        ) from exc
    except urllib.error.URLError as exc:
        raise SourceError(
            f"无法连接：{_redact(url)}\n原因：{exc.reason}"
        ) from exc
    except TimeoutError as exc:
        raise SourceError(f"请求超时（{spec.timeout}s）：{_redact(url)}") from exc

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
    """去掉 URL 里的用户信息与敏感查询参数，便于安全打印。"""
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
    """把一条记录渲染成文档内容。"""
    if isinstance(record, str):
        return record
    return json.dumps(record, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# spec 存取
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
    """执行抓取并把结果存入材料库。"""
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
