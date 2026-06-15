"""Nodes for the ingestion flow."""

from __future__ import annotations

from typing import Any

from langgraph.runtime import Runtime

from agent.context import RagContext
from agent.dependencies import get_container
from agent.state import IngestState


async def load_documents(state: IngestState, runtime: Runtime[RagContext]) -> dict[str, Any]:
    """Load source documents into the ingestion flow."""

    del runtime
    container = get_container()
    return container.ingest_application_service.load_source(
        source_uri=state.get("source_uri"),
        source_name=state.get("source_name"),
        source_content_b64=state.get("source_content_b64"),
        source_mime_type=state.get("source_mime_type"),
        backup_source=state.get("backup_source", True),
        ingest_job_id=state.get("ingest_job_id"),
        recursive_url=state.get("recursive_url"),
        recursive_max_depth=state.get("recursive_max_depth"),
        recursive_prevent_outside=state.get("recursive_prevent_outside", True),
    )


async def normalize_documents(state: IngestState, runtime: Runtime[RagContext]) -> dict[str, Any]:
    """Normalize loaded documents."""

    del runtime
    container = get_container()
    return container.ingest_application_service.register_loaded_documents(
        ingest_job_id=state.get("ingest_job_id"),
        raw_documents=state.get("raw_documents", []),
        ingest_status=state.get("ingest_status"),
        error=state.get("error"),
    )


async def split_documents(state: IngestState, runtime: Runtime[RagContext]) -> dict[str, Any]:
    """Split normalized documents into chunks."""

    del runtime
    container = get_container()
    return container.ingest_application_service.split_registered_documents(
        state.get("normalized_documents", []),
        ingest_status=state.get("ingest_status"),
        error=state.get("error"),
    )


async def upsert_documents(state: IngestState, runtime: Runtime[RagContext]) -> dict[str, Any]:
    """Upsert chunks into the vector store."""

    del runtime
    container = get_container()
    return container.ingest_application_service.persist_chunks(
        chunks=state.get("chunks", []),
        ingest_job_id=state.get("ingest_job_id"),
        registered_versions=state.get("registered_versions", []),
        ingest_status=state.get("ingest_status"),
        error=state.get("error"),
    )


async def finalize_ingestion(state: IngestState, runtime: Runtime[RagContext]) -> dict[str, Any]:
    """Finalize ingestion response."""

    del runtime
    container = get_container()
    return container.ingest_application_service.build_ingest_result(state)
