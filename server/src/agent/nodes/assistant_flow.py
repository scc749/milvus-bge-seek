"""Adapter nodes for assistant-ui / LangGraph message-based conversations."""

from __future__ import annotations

from typing import Any

from langgraph.runtime import Runtime

from agent.context import RagContext
from agent.dependencies import get_container
from agent.state import AssistantState


async def capture_latest_user_query(
    state: AssistantState,
    runtime: Runtime[RagContext],
) -> dict[str, Any]:
    """Extract the latest human message into the internal query field."""

    del runtime
    container = get_container()
    user_query = container.conversation_service.extract_latest_user_query(
        state.get("messages", [])
    )
    return {"user_query": user_query}


async def append_assistant_message(
    state: AssistantState,
    runtime: Runtime[RagContext],
) -> dict[str, Any]:
    """Append the generated answer to the message list for assistant-ui clients."""

    del runtime
    container = get_container()
    messages = container.conversation_service.append_assistant_message(
        messages=state.get("messages", []),
        answer=state.get("answer", ""),
        citations=state.get("citations", []),
        debug=state.get("debug", {}),
    )
    return {"messages": messages}
