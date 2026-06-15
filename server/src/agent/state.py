"""Shared graph state definitions."""

from __future__ import annotations

from typing import Any, Literal

from typing_extensions import TypedDict


class QueryAnalysis(TypedDict, total=False):
    """Result of query analysis before retrieval."""

    intent: Literal["faq", "knowledge_qa", "comparison", "multi_hop"]
    need_rewrite: bool
    need_rerank: bool
    need_metadata_filter: bool
    top_k: int


class RetrievedChunk(TypedDict, total=False):
    """Single retrieval candidate flowing through the graph."""

    chunk_id: str
    document_id: str
    content: str
    score: float
    metadata: dict[str, Any]


class CitationRecord(TypedDict, total=False):
    """Reference returned to the caller."""

    document_id: str
    chunk_id: str
    title: str
    source_uri: str


class RagState(TypedDict, total=False):
    """Mutable state used by the query graph."""

    user_query: str
    rewritten_query: str
    analysis: QueryAnalysis
    filters: dict[str, Any]
    candidate_chunks: list[RetrievedChunk]
    reranked_chunks: list[RetrievedChunk]
    answer: str
    citations: list[CitationRecord]
    debug: dict[str, Any]
    error: str


class AssistantState(RagState, total=False):
    """Mutable state used by the assistant-ui compatible query graph."""

    messages: list[dict[str, Any]]


class IngestState(TypedDict, total=False):
    """Mutable state used by the ingestion graph."""

    document_id: str
    source_uri: str
    source_name: str
    source_content_b64: str
    source_mime_type: str
    backup_source: bool
    recursive_url: bool
    recursive_max_depth: int
    recursive_prevent_outside: bool
    ingest_job_id: str
    prepared_source: dict[str, Any]
    registered_document_ids: list[str]
    registered_version_ids: list[str]
    registered_versions: list[dict[str, Any]]
    document_record: dict[str, Any]
    raw_documents: list[dict[str, Any]]
    normalized_documents: list[dict[str, Any]]
    chunks: list[dict[str, Any]]
    upserted_count: int
    ingest_status: str
    delete_status: str
    error: str
    cleaned_chunk_count: int
    result: dict[str, Any]
    error: str


class DeleteState(TypedDict, total=False):
    """Mutable state used by the deletion graph."""

    document_id: str
    delete_job_id: str
    chunk_ids: list[str]
    deleted_chunk_count: int
    result: dict[str, Any]
    error: str


class AdminState(TypedDict, total=False):
    """Mutable state used by the admin query graph."""

    operation: Literal[
        "list_documents",
        "get_document_detail",
        "list_document_versions",
        "list_ingest_jobs",
        "list_delete_jobs",
        "get_ingest_job_detail",
        "get_delete_job_detail",
        "get_page_contract",
    ]
    page_name: Literal["document_list", "document_detail", "ingest_job", "delete_job"]
    document_id: str
    job_id: str
    page: int
    page_size: int
    limit: int
    status_filter: str
    source_type_filter: str
    query: str
    sort_by: str
    sort_direction: Literal["asc", "desc"]
    response: dict[str, Any]
    result: dict[str, Any]
    error: str
