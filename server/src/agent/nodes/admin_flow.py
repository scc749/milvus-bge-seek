"""Nodes for the admin/read-model flow."""

from __future__ import annotations

from typing import Any

from langgraph.runtime import Runtime

from agent.context import RagContext
from agent.dependencies import get_container
from agent.state import AdminState


async def fetch_admin_records(state: AdminState, runtime: Runtime[RagContext]) -> dict[str, Any]:
    """Fetch admin records from the PostgreSQL read model."""

    del runtime
    container = get_container()
    return container.admin_application_service.fetch_records(state)


async def finalize_admin_records(state: AdminState, runtime: Runtime[RagContext]) -> dict[str, Any]:
    """Return admin records in a frontend-friendly envelope."""

    del runtime
    container = get_container()
    return container.admin_application_service.build_result(state)
