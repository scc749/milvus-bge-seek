"""Pydantic request models for the local compat API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AssistantChatRequest(BaseModel):
    """Single-turn assistant chat request."""

    thread_id: str | None = None
    message: str = Field(min_length=1)


class AssistantThreadUpdateRequest(BaseModel):
    """Update persisted assistant thread metadata."""

    title: str | None = None
    status: str | None = None


class PageContractRequest(BaseModel):
    """Fetch a page-level admin contract."""

    page_name: str


class AdminQueryRequest(BaseModel):
    """Run an admin query operation."""

    operation: str
    payload: dict[str, object] = Field(default_factory=dict)


class IngestRequest(BaseModel):
    """Start an ingest flow."""

    source_uri: str | None = None
    source_name: str | None = None
    source_content_b64: str | None = None
    source_mime_type: str | None = None
    backup_source: bool = True
    recursive_url: bool | None = None
    recursive_max_depth: int | None = Field(default=None, ge=0, le=6)
    recursive_prevent_outside: bool = True


class DocumentActionRequest(BaseModel):
    """Run a document-scoped action."""

    document_id: str
