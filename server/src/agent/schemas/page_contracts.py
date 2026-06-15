"""Page-level backend contracts for future document/task center UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FilterContract:
    """Describes a filter accepted by a page contract."""

    key: str
    label: str
    value_type: str
    options: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "key": self.key,
            "label": self.label,
            "value_type": self.value_type,
        }
        if self.options:
            payload["options"] = self.options
        return payload


@dataclass(frozen=True)
class ParamContract:
    """Describes a query parameter accepted by a backend operation."""

    key: str
    label: str
    required: bool
    value_type: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "required": self.required,
            "value_type": self.value_type,
        }


@dataclass(frozen=True)
class SortContract:
    """Describes a supported sort field for a page contract."""

    field: str
    label: str
    default_direction: str = "desc"

    def to_dict(self) -> dict[str, str]:
        return {
            "field": self.field,
            "label": self.label,
            "default_direction": self.default_direction,
        }


@dataclass(frozen=True)
class FieldContract:
    """Describes a concrete field rendered on cards, lists, or detail blocks."""

    key: str
    label: str
    source_path: str
    value_type: str = "text"
    emphasized: bool = False
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "key": self.key,
            "label": self.label,
            "source_path": self.source_path,
            "value_type": self.value_type,
            "emphasized": self.emphasized,
        }
        if self.description:
            payload["description"] = self.description
        return payload


@dataclass(frozen=True)
class StatCardContract:
    """Describes a summary stat card expected by the frontend."""

    key: str
    label: str
    source_path: str
    tone: str = "default"

    def to_dict(self) -> dict[str, str]:
        return {
            "key": self.key,
            "label": self.label,
            "source_path": self.source_path,
            "tone": self.tone,
        }


@dataclass(frozen=True)
class TableContract:
    """Describes a table block to render on a page."""

    key: str
    label: str
    source_operation: str
    columns: list[FieldContract] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "source_operation": self.source_operation,
            "columns": [item.to_dict() for item in self.columns],
        }


@dataclass(frozen=True)
class SectionContract:
    """Describes a logical section expected by a detail page."""

    key: str
    label: str
    kind: str = "panel"
    fields: list[FieldContract] = field(default_factory=list)
    stat_cards: list[StatCardContract] = field(default_factory=list)
    tables: list[TableContract] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "kind": self.kind,
            "fields": [item.to_dict() for item in self.fields],
            "stat_cards": [item.to_dict() for item in self.stat_cards],
            "tables": [item.to_dict() for item in self.tables],
        }


@dataclass(frozen=True)
class TabContract:
    """Describes a detail-page tab and the section keys it should render."""

    key: str
    label: str
    section_keys: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "section_keys": self.section_keys,
        }


@dataclass(frozen=True)
class QueryContract:
    """Describes how the frontend should call a backend operation."""

    name: str
    operation: str
    params: list[ParamContract] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "name": self.name,
            "operation": self.operation,
            "params": [item.to_dict() for item in self.params],
        }
        if self.description:
            payload["description"] = self.description
        return payload


@dataclass(frozen=True)
class ExampleContract:
    """Example input payload for a page-level operation."""

    label: str
    request: dict[str, Any]
    response_preview: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "label": self.label,
            "request": self.request,
        }
        if self.response_preview:
            payload["response_preview"] = self.response_preview
        return payload


@dataclass(frozen=True)
class PageContract:
    """Stable contract exported to frontend page implementations."""

    page_name: str
    title: str
    primary_operation: str
    secondary_operations: list[str] = field(default_factory=list)
    primary_query: QueryContract | None = None
    secondary_queries: list[QueryContract] = field(default_factory=list)
    filters: list[FilterContract] = field(default_factory=list)
    sorts: list[SortContract] = field(default_factory=list)
    list_item_fields: list[FieldContract] = field(default_factory=list)
    stat_cards: list[StatCardContract] = field(default_factory=list)
    tables: list[TableContract] = field(default_factory=list)
    sections: list[SectionContract] = field(default_factory=list)
    tabs: list[TabContract] = field(default_factory=list)
    examples: list[ExampleContract] = field(default_factory=list)
    default_page_size: int = 20

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "page_name": self.page_name,
            "title": self.title,
            "primary_operation": self.primary_operation,
            "secondary_operations": self.secondary_operations,
            "default_page_size": self.default_page_size,
            "filters": [item.to_dict() for item in self.filters],
            "sorts": [item.to_dict() for item in self.sorts],
            "list_item_fields": [item.to_dict() for item in self.list_item_fields],
            "stat_cards": [item.to_dict() for item in self.stat_cards],
            "tables": [item.to_dict() for item in self.tables],
            "sections": [item.to_dict() for item in self.sections],
            "tabs": [item.to_dict() for item in self.tabs],
            "examples": [item.to_dict() for item in self.examples],
        }
        if self.primary_query is not None:
            payload["primary_query"] = self.primary_query.to_dict()
        if self.secondary_queries:
            payload["secondary_queries"] = [item.to_dict() for item in self.secondary_queries]
        return payload
