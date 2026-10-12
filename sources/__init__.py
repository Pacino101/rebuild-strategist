#!/usr/bin/env python3
"""REBUILD data source layer.

Fetches external material and turns it into documents that are **hashed,
verifiable and traceable**, for the evidence ledger to reference.

Boundaries (deliberate, not a capability gap)
--------------------------------------------
- Read-only; never writes back to any external system.
- Ships no connector for any specific platform. URL, authentication and
  field paths are all supplied by the user.
- Does not parse marketing semantics, does not do attribution, does not
  collect user behaviour.

Usage
-----
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
