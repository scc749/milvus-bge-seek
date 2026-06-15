"""Nodes for the document deletion flow."""

from __future__ import annotations

from typing import Any

from langgraph.runtime import Runtime

from agent.context import RagContext
from agent.dependencies import get_container
from agent.state import DeleteState


async def create_delete_job(state: DeleteState, runtime: Runtime[RagContext]) -> dict[str, Any]:
    """Create a delete job for the requested document when PostgreSQL is available."""

    del runtime
    container = get_container()
    return container.delete_application_service.create_delete_job(state["document_id"])


async def collect_delete_targets(state: DeleteState, runtime: Runtime[RagContext]) -> dict[str, Any]:
    """Collect all known chunk ids for the document across versions."""

    del runtime
    container = get_container()
    return container.delete_application_service.collect_delete_targets(state["document_id"])


async def delete_document_chunks(state: DeleteState, runtime: Runtime[RagContext]) -> dict[str, Any]:
    """Delete collected chunk ids from Milvus."""

    del runtime
    container = get_container()
    return container.delete_application_service.delete_document_chunks(
        document_id=state["document_id"],
        delete_job_id=state.get("delete_job_id"),
        chunk_ids=state.get("chunk_ids", []),
    )


async def finalize_delete(state: DeleteState, runtime: Runtime[RagContext]) -> dict[str, Any]:
    """Finalize delete-job status and shape the graph response."""

    del runtime
    container = get_container()
    return container.delete_application_service.build_delete_result(state)
