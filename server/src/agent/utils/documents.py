"""Helpers for document and chunk identifiers."""

from __future__ import annotations

from typing import Any
from uuid import uuid4


def ensure_document_id(metadata: dict[str, Any]) -> str:
    """Return an existing document id or generate one."""

    document_id = metadata.get("document_id")
    if document_id:
        return str(document_id)
    return str(uuid4())


def ensure_chunk_id(document_id: str, chunk_index: int) -> str:
    """Build a deterministic chunk identifier."""

    return f"{document_id}::chunk::{chunk_index}"
