"""DTOs for admin/document-center responses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PageInfo:
    """Pagination metadata for admin list responses."""

    page: int
    page_size: int
    total: int

    def to_dict(self) -> dict[str, int]:
        return {
            "page": self.page,
            "page_size": self.page_size,
            "total": self.total,
        }


@dataclass(frozen=True)
class SortInfo:
    """Sorting metadata for admin responses."""

    field: str
    direction: str

    def to_dict(self) -> dict[str, str]:
        return {
            "field": self.field,
            "direction": self.direction,
        }


@dataclass(frozen=True)
class AdminQueryMeta:
    """Capability metadata exposed to frontend document/task center pages."""

    available_operations: list[str] | None = None
    available_statuses: list[str] | None = None
    available_source_types: list[str] | None = None
    sortable_fields: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.available_operations is not None:
            payload["available_operations"] = self.available_operations
        if self.available_statuses is not None:
            payload["available_statuses"] = self.available_statuses
        if self.available_source_types is not None:
            payload["available_source_types"] = self.available_source_types
        if self.sortable_fields is not None:
            payload["sortable_fields"] = self.sortable_fields
        return payload


@dataclass(frozen=True)
class AdminQueryResult:
    """Stable envelope for admin graph operations."""

    operation: str
    records: list[dict[str, Any]]
    page_info: PageInfo | None = None
    sort_info: SortInfo | None = None
    document_id: str | None = None
    job_id: str | None = None
    filters: dict[str, Any] | None = None
    meta: AdminQueryMeta | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "operation": self.operation,
            "count": len(self.records),
            "records": self.records,
        }
        if self.document_id:
            payload["document_id"] = self.document_id
        if self.job_id:
            payload["job_id"] = self.job_id
        if self.page_info is not None:
            payload["page"] = self.page_info.page
            payload["page_size"] = self.page_info.page_size
            payload["total"] = self.page_info.total
        if self.sort_info is not None:
            payload["sort"] = self.sort_info.to_dict()
        if self.filters:
            payload["filters"] = self.filters
        if self.meta is not None:
            payload["meta"] = self.meta.to_dict()
        return payload
