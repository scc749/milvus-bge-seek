"""Application service for admin/read-model graph operations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from agent.repositories.postgres_read_repository import PostgresReadRepository
from agent.schemas.admin_constants import ADMIN_OPERATIONS
from agent.services.admin_page_contract_service import AdminPageContractService


@dataclass(frozen=True)
class AdminQueryContext:
    """Normalized query context shared by admin read-model handlers."""

    operation: str
    page: int
    page_size: int
    status_filter: str | None
    source_type_filter: str | None
    query: str | None
    sort_by: str
    sort_direction: str
    document_id: str
    job_id: str
    page_name: str


class AdminApplicationService:
    """Coordinate admin-facing read-model queries."""

    def __init__(
        self,
        read_repository: PostgresReadRepository,
        admin_page_contract_service: AdminPageContractService | None = None,
    ) -> None:
        self._read_repository = read_repository
        self._admin_page_contract_service = admin_page_contract_service or AdminPageContractService()
        self._operation_handlers: dict[str, Callable[[AdminQueryContext], dict[str, Any]]] = {
            "get_page_contract": self._handle_get_page_contract,
            "get_document_detail": self._handle_get_document_detail,
            "get_ingest_job_detail": self._handle_get_ingest_job_detail,
            "get_delete_job_detail": self._handle_get_delete_job_detail,
            "list_document_versions": self._handle_list_document_versions,
            "list_ingest_jobs": self._handle_list_ingest_jobs,
            "list_delete_jobs": self._handle_list_delete_jobs,
            "list_documents": self._handle_list_documents,
        }

    def fetch_records(self, state: dict[str, Any]) -> dict[str, Any]:
        """Route admin operations to the appropriate read-model query."""

        context = self._build_query_context(state)
        handler = self._operation_handlers.get(context.operation)
        if handler is None:
            return {
                "response": {
                    "operation": context.operation,
                    "records": [],
                    "error": f"Unsupported admin operation: {context.operation}",
                    "meta": {
                        "available_operations": ADMIN_OPERATIONS,
                    },
                }
            }
        response = handler(context)
        return {"response": response}

    def build_result(self, state: dict[str, Any]) -> dict[str, Any]:
        """Build a frontend-friendly admin response envelope."""

        return {"result": state.get("response", {})}

    def _build_query_context(self, state: dict[str, Any]) -> AdminQueryContext:
        return AdminQueryContext(
            operation=str(state.get("operation", "list_documents")),
            page=max(int(state.get("page", 1) or 1), 1),
            page_size=max(int(state.get("page_size", state.get("limit", 20)) or 20), 1),
            status_filter=state.get("status_filter"),
            source_type_filter=state.get("source_type_filter"),
            query=state.get("query"),
            sort_by=str(state.get("sort_by", "") or ""),
            sort_direction=str(state.get("sort_direction", "desc") or "desc"),
            document_id=str(state.get("document_id", "") or ""),
            job_id=str(state.get("job_id", "") or ""),
            page_name=str(state.get("page_name", "document_list") or "document_list"),
        )

    def _handle_get_page_contract(self, context: AdminQueryContext) -> dict[str, Any]:
        return self._admin_page_contract_service.get_page_contract(context.page_name)["result"]

    def _handle_get_document_detail(self, context: AdminQueryContext) -> dict[str, Any]:
        return self._read_repository.get_document_detail(context.document_id)

    def _handle_get_ingest_job_detail(self, context: AdminQueryContext) -> dict[str, Any]:
        return self._read_repository.get_ingest_job_detail(context.job_id)

    def _handle_get_delete_job_detail(self, context: AdminQueryContext) -> dict[str, Any]:
        return self._read_repository.get_delete_job_detail(context.job_id)

    def _handle_list_document_versions(self, context: AdminQueryContext) -> dict[str, Any]:
        return self._read_repository.list_document_versions(
            context.document_id,
            page=context.page,
            page_size=context.page_size,
            status=context.status_filter,
            sort_by=context.sort_by or "version_number",
            sort_direction=context.sort_direction,
        )

    def _handle_list_ingest_jobs(self, context: AdminQueryContext) -> dict[str, Any]:
        return self._read_repository.list_ingest_jobs(
            page=context.page,
            page_size=context.page_size,
            status=context.status_filter,
            sort_by=context.sort_by or "updated_at",
            sort_direction=context.sort_direction,
        )

    def _handle_list_delete_jobs(self, context: AdminQueryContext) -> dict[str, Any]:
        return self._read_repository.list_delete_jobs(
            page=context.page,
            page_size=context.page_size,
            status=context.status_filter,
            sort_by=context.sort_by or "updated_at",
            sort_direction=context.sort_direction,
        )

    def _handle_list_documents(self, context: AdminQueryContext) -> dict[str, Any]:
        return self._read_repository.list_documents(
            page=context.page,
            page_size=context.page_size,
            status=context.status_filter,
            source_type=context.source_type_filter,
            query=context.query,
            sort_by=context.sort_by or "updated_at",
            sort_direction=context.sort_direction,
        )
