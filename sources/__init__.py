#!/usr/bin/env python3
"""REBUILD 数据源层。

把外部材料取回来，变成**带哈希、可校验、可追溯**的文档，供证据账本引用。

边界（刻意为之，不是能力缺失）
------------------------------
- 只读，不写回任何外部系统。
- 不内置任何具体平台的连接器。URL、鉴权、字段路径都由使用者提供。
- 不解析营销语义、不做归因、不采集用户行为。

用法
----
    from sources import DocumentStore, files, http_api

    store = DocumentStore("projects/my-project")
    doc = files.add_file(store, "~/Downloads/orders.csv")

    spec = http_api.HttpSourceSpec(
        name="my-orders",
        url="https://api.example.com/orders",
        header_env={"Authorization": "MY_API_TOKEN"},
        records_path="data.items",
    )
    docs = http_api.add_http(store, spec)
"""
from .base import (
    Document,
    DocumentStore,
    SourceError,
    sha256_of,
    SOURCES_DIRNAME,
    MAX_CONTENT_CHARS,
)
from . import files, http_api

__all__ = [
    "Document",
    "DocumentStore",
    "SourceError",
    "sha256_of",
    "files",
    "http_api",
    "SOURCES_DIRNAME",
    "MAX_CONTENT_CHARS",
]
