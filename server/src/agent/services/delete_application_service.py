"""Application service for document deletion flows."""

from __future__ import annotations

from typing import Any

from agent.repositories.postgres_registry_repository import PostgresRegistryRepository
from agent.services.ingestion_service import IngestionService


class DeleteApplicationService:
    """Coordinate delete use cases across registry and vector layers."""

    def __init__(
        self,
        ingestion_service: IngestionService,
        registry_repository: PostgresRegistryRepository,
    ) -> None:
        self._ingestion_service = ingestion_service
        self._registry_repository = registry_repository

    def create_delete_job(self, document_id: str) -> dict[str, Any]:
        """Create a delete job for the requested document."""

        return {
            "delete_job_id": self._registry_repository.create_delete_job(document_id)
        }

    def collect_delete_targets(self, document_id: str) -> dict[str, Any]:
        """Collect all chunk ids known for a document."""

        return {
            "chunk_ids": self._registry_repository.get_document_chunk_ids(document_id)
        }

    def delete_document_chunks(
        self,
        document_id: str,
        delete_job_id: str | None,
        chunk_ids: list[str],
    ) -> dict[str, Any]:
        """Delete chunks from Milvus and finalize the deletion job."""

        deleted_chunk_count = self._ingestion_service.delete_chunks(chunk_ids)
        if chunk_ids and deleted_chunk_count != len(chunk_ids):
            error = (
                "Failed to delete all chunks from Milvus. "
                f"expected={len(chunk_ids)} actual={deleted_chunk_count}"
            )
            self._registry_repository.finalize_delete_job(
                delete_job_id=delete_job_id,
                document_id=document_id,
                deleted_chunk_count=deleted_chunk_count,
                status="failed",
                error=error,
            )
            return {
                "deleted_chunk_count": deleted_chunk_count,
                "delete_status": "failed",
                "error": error,
            }
        self._registry_repository.finalize_delete_job(
            delete_job_id=delete_job_id,
            document_id=document_id,
            deleted_chunk_count=deleted_chunk_count,
            status="completed",
        )
        return {"deleted_chunk_count": deleted_chunk_count, "delete_status": "completed"}

    def build_delete_result(self, state: dict[str, Any]) -> dict[str, Any]:
        """Build a frontend-friendly result payload for deletion graphs."""

        return {
            "result": {
                "document_id": state.get("document_id"),
                "delete_job_id": state.get("delete_job_id"),
                "chunk_count": len(state.get("chunk_ids", [])),
                "deleted_chunk_count": state.get("deleted_chunk_count", 0),
                "status": state.get("delete_status", "completed"),
                "error": state.get("error"),
            }
        }
