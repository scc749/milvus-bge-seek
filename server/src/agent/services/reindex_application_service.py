"""Application service for reindex-specific source resolution and pinning."""

from __future__ import annotations

from typing import Any

from agent.repositories.postgres_registry_repository import PostgresRegistryRepository
from agent.services.document_source_service import DocumentSourceService
from agent.services.document_source_store_service import DocumentSourceStoreService


class ReindexApplicationService:
    """Coordinate reindex-only steps before re-entering the ingest flow."""

    def __init__(
        self,
        registry_repository: PostgresRegistryRepository,
        document_source_store_service: DocumentSourceStoreService,
        document_source_service: DocumentSourceService,
    ) -> None:
        self._registry_repository = registry_repository
        self._document_source_store_service = document_source_store_service
        self._document_source_service = document_source_service

    def resolve_reindex_source(self, document_id: str | None) -> dict[str, Any]:
        """Load the current source record for an existing document."""

        if not document_id:
            return {"document_record": {}, "source_uri": ""}
        record = self._registry_repository.get_document_record(document_id) or {}
        replay_source_uri = self._document_source_store_service.materialize_replay_source(record)
        return {
            "document_record": record,
            "source_uri": replay_source_uri or record.get("source_uri", ""),
        }

    def pin_document_identity(
        self,
        raw_documents: list[dict[str, Any]],
        document_id: str | None,
        source_uri: str | None = None,
        document_record: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Keep the original document id when reindexing an existing source."""

        return {
            "raw_documents": self._document_source_service.pin_document_identity(
                raw_documents=raw_documents,
                document_id=document_id,
                source_uri=source_uri,
                document_record=document_record,
            )
        }
