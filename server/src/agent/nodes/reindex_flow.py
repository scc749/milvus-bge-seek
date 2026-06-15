"""Nodes for the document reindex flow."""

from __future__ import annotations

from typing import Any

from langgraph.runtime import Runtime

from agent.context import RagContext
from agent.dependencies import get_container
from agent.state import IngestState


async def resolve_reindex_source(state: IngestState, runtime: Runtime[RagContext]) -> dict[str, Any]:
    """Resolve the existing document record before re-running ingestion."""

    del runtime
    container = get_container()
    return container.reindex_application_service.resolve_reindex_source(
        state.get("document_id")
    )


async def pin_document_identity(state: IngestState, runtime: Runtime[RagContext]) -> dict[str, Any]:
    """Keep the original document id when reindexing an existing source."""

    del runtime
    container = get_container()
    return container.reindex_application_service.pin_document_identity(
        raw_documents=state.get("raw_documents", []),
        document_id=state.get("document_id"),
        source_uri=state.get("source_uri"),
        document_record=state.get("document_record"),
    )
