"""FastAPI router for the local compat layer."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from agent.api.compat_models import (
    AdminQueryRequest,
    AssistantChatRequest,
    AssistantThreadUpdateRequest,
    DocumentActionRequest,
    IngestRequest,
    PageContractRequest,
)
from agent.dependencies import get_container

router = APIRouter(tags=["compat"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Return a minimal health response for local development."""

    return {"status": "ok"}


@router.post("/compat/assistant/threads")
async def create_thread() -> dict[str, str]:
    """Create a persisted chat thread."""

    return get_container().compat_application_service.create_thread()


@router.get("/compat/assistant/threads")
async def list_threads() -> dict[str, object]:
    """List persisted assistant threads."""

    return get_container().compat_application_service.list_threads()


@router.get("/compat/assistant/threads/{thread_id}")
async def get_thread(thread_id: str) -> dict[str, object]:
    """Return the stored message history for a thread."""

    result = get_container().compat_application_service.get_thread(thread_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return result


@router.patch("/compat/assistant/threads/{thread_id}")
async def update_thread(
    thread_id: str, payload: AssistantThreadUpdateRequest
) -> dict[str, object]:
    """Update thread metadata such as title or archive status."""

    result = get_container().compat_application_service.update_thread(
        thread_id=thread_id,
        title=payload.title,
        status=payload.status,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return result


@router.delete("/compat/assistant/threads/{thread_id}")
async def delete_thread(thread_id: str) -> dict[str, str]:
    """Delete a persisted thread."""

    get_container().compat_application_service.delete_thread(thread_id)
    return {"status": "ok"}


@router.post("/compat/assistant/chat")
async def assistant_chat(payload: AssistantChatRequest) -> dict[str, object]:
    """Run a single assistant turn using the message-based assistant graph."""

    return await get_container().compat_application_service.assistant_chat(
        thread_id=payload.thread_id,
        message=payload.message,
    )


@router.post("/compat/assistant/chat/stream")
async def assistant_chat_stream(payload: AssistantChatRequest) -> StreamingResponse:
    """Stream assistant turn progress and incremental answer chunks."""

    async def generate():
        async for event in get_container().compat_application_service.assistant_chat_stream(
            thread_id=payload.thread_id,
            message=payload.message,
        ):
            yield json.dumps(event, ensure_ascii=False) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@router.post("/compat/admin/page-contract")
async def admin_page_contract(payload: PageContractRequest) -> dict[str, object]:
    """Return a page contract through the admin graph."""

    return await get_container().compat_application_service.admin_page_contract(
        payload.page_name
    )


@router.post("/compat/admin/query")
async def admin_query(payload: AdminQueryRequest) -> dict[str, object]:
    """Run an admin read-model query through the admin graph."""

    return await get_container().compat_application_service.admin_query(
        payload.operation,
        payload.payload,
    )


@router.post("/compat/ingest")
async def ingest_document(payload: IngestRequest) -> dict[str, object]:
    """Run the local ingest graph."""

    return await get_container().compat_application_service.ingest_document(
        payload.model_dump()
    )


@router.post("/compat/delete")
async def delete_document(payload: DocumentActionRequest) -> dict[str, object]:
    """Run the local delete graph."""

    return await get_container().compat_application_service.delete_document(
        payload.model_dump()
    )


@router.post("/compat/reindex")
async def reindex_document(payload: DocumentActionRequest) -> dict[str, object]:
    """Run the local reindex graph."""

    return await get_container().compat_application_service.reindex_document(
        payload.model_dump()
    )
