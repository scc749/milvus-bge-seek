"""Application service for ingest and re-ingest flows."""

from __future__ import annotations

from typing import Any

from agent.repositories.postgres_registry_repository import PostgresRegistryRepository
from agent.services.document_source_service import DocumentSourceService
from agent.services.document_source_store_service import DocumentSourceStoreService
from agent.services.ingestion_service import IngestionService


class IngestApplicationService:
    """Coordinate ingest use cases across source storage, registry, and vector layers."""

    def __init__(
        self,
        ingestion_service: IngestionService,
        registry_repository: PostgresRegistryRepository,
        document_source_store_service: DocumentSourceStoreService,
        document_source_service: DocumentSourceService,
    ) -> None:
        self._ingestion_service = ingestion_service
        self._registry_repository = registry_repository
        self._document_source_store_service = document_source_store_service
        self._document_source_service = document_source_service

    def load_source(
        self,
        source_uri: str | None = None,
        source_name: str | None = None,
        source_content_b64: str | None = None,
        source_mime_type: str | None = None,
        backup_source: bool = True,
        ingest_job_id: str | None = None,
        recursive_url: bool | None = None,
        recursive_max_depth: int | None = None,
        recursive_prevent_outside: bool = True,
    ) -> dict[str, Any]:
        """Create an ingest job and load raw source documents."""

        prepared_source = self._document_source_store_service.prepare_source(
            source_uri=source_uri,
            source_name=source_name,
            source_content_b64=source_content_b64,
            source_mime_type=source_mime_type,
            backup_source=backup_source,
            recursive_url=recursive_url,
            recursive_max_depth=recursive_max_depth,
            recursive_prevent_outside=recursive_prevent_outside,
        )
        effective_ingest_job_id = ingest_job_id or self._registry_repository.create_ingest_job(
            prepared_source.display_source_uri or prepared_source.load_source_uri
        )
        self._registry_repository.mark_ingest_job_processing(
            effective_ingest_job_id,
            source_uri=prepared_source.display_source_uri or source_uri or "",
        )
        raw_documents = self._ingestion_service.load_documents(
            prepared_source.load_source_uri,
            load_options=prepared_source.load_options,
        )
        if not raw_documents:
            error = "No documents could be loaded from the provided source."
            self._registry_repository.finalize_ingest_job(
                ingest_job_id=effective_ingest_job_id,
                chunks=[],
                upserted_count=0,
                status="failed",
                error=error,
            )
            return {
                "ingest_job_id": effective_ingest_job_id,
                "source_uri": prepared_source.display_source_uri or source_uri or "",
                "source_name": prepared_source.source_name,
                "source_mime_type": prepared_source.source_mime_type,
                **prepared_source.to_state(),
                "raw_documents": [],
                "ingest_status": "failed",
                "error": error,
            }
        enriched_documents = self._document_source_service.enrich_raw_documents(
            raw_documents,
            prepared_source.to_state(),
        )
        return {
            "ingest_job_id": effective_ingest_job_id,
            "source_uri": prepared_source.display_source_uri or source_uri or "",
            "source_name": prepared_source.source_name,
            "source_mime_type": prepared_source.source_mime_type,
            **prepared_source.to_state(),
            "raw_documents": enriched_documents,
        }

    def register_loaded_documents(
        self,
        raw_documents: list[dict[str, Any]],
        ingest_job_id: str | None = None,
        ingest_status: str | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Normalize raw documents and register new document versions."""

        if ingest_status == "failed":
            return {
                "normalized_documents": [],
                "registered_document_ids": [],
                "registered_version_ids": [],
                "registered_versions": [],
                "ingest_status": "failed",
                "error": error,
            }
        normalized = self._ingestion_service.normalize_documents(raw_documents)
        registered_versions = self._registry_repository.register_documents(
            normalized_documents=normalized,
            ingest_job_id=ingest_job_id,
        )
        version_lookup = {record["document_id"]: record for record in registered_versions}
        enriched_normalized: list[dict[str, Any]] = []
        for doc in normalized:
            record = version_lookup.get(doc["document_id"], {})
            enriched_normalized.append(
                {
                    **doc,
                    "metadata": self._document_source_service.public_metadata(
                        doc.get("metadata", {})
                    ),
                    "version_id": record.get("version_id"),
                    "version_number": record.get("version_number"),
                }
            )
        return {
            "normalized_documents": enriched_normalized,
            "registered_document_ids": [record["document_id"] for record in registered_versions],
            "registered_version_ids": [record["version_id"] for record in registered_versions],
            "registered_versions": registered_versions,
        }

    def split_registered_documents(
        self,
        normalized_documents: list[dict[str, Any]],
        ingest_status: str | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Split normalized documents into chunk records."""

        if ingest_status == "failed":
            return {"chunks": [], "ingest_status": "failed", "error": error}
        return {"chunks": self._ingestion_service.split_documents(normalized_documents)}

    def persist_chunks(
        self,
        chunks: list[dict[str, Any]],
        ingest_job_id: str | None = None,
        registered_versions: list[dict[str, Any]] | None = None,
        ingest_status: str | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Delete stale chunks, upsert current chunks, and finalize ingest state."""

        if ingest_status == "failed":
            return {
                "cleaned_chunk_count": 0,
                "upserted_count": 0,
                "ingest_status": "failed",
                "error": error,
            }
        replaced_version_ids = [
            record["previous_version_id"]
            for record in (registered_versions or [])
            if record.get("previous_version_id")
        ]
        stale_chunk_ids = self._registry_repository.get_chunk_ids_by_version_ids(
            replaced_version_ids
        )
        cleaned_chunk_count = self._ingestion_service.delete_chunks(stale_chunk_ids)

        if stale_chunk_ids and cleaned_chunk_count != len(stale_chunk_ids):
            error = (
                "Failed to delete all stale chunks before reindex. "
                f"expected={len(stale_chunk_ids)} actual={cleaned_chunk_count}"
            )
            self._registry_repository.finalize_ingest_job(
                ingest_job_id=ingest_job_id,
                chunks=[],
                upserted_count=0,
                status="failed",
                error=error,
            )
            return {
                "cleaned_chunk_count": cleaned_chunk_count,
                "upserted_count": 0,
                "ingest_status": "failed",
                "error": error,
            }

        upserted_count = self._ingestion_service.upsert_chunks(chunks)
        if chunks and upserted_count != len(chunks):
            error = (
                "Failed to upsert all chunks into Milvus. "
                f"expected={len(chunks)} actual={upserted_count}"
            )
            self._registry_repository.finalize_ingest_job(
                ingest_job_id=ingest_job_id,
                chunks=[],
                upserted_count=upserted_count,
                status="failed",
                error=error,
            )
            return {
                "cleaned_chunk_count": cleaned_chunk_count,
                "upserted_count": upserted_count,
                "ingest_status": "failed",
                "error": error,
            }

        self._registry_repository.finalize_ingest_job(
            ingest_job_id=ingest_job_id,
            chunks=chunks,
            upserted_count=upserted_count,
            status="completed",
            replaced_version_ids=replaced_version_ids,
        )
        return {
            "cleaned_chunk_count": cleaned_chunk_count,
            "upserted_count": upserted_count,
            "ingest_status": "completed",
        }

    def build_ingest_result(self, state: dict[str, Any]) -> dict[str, Any]:
        """Build a frontend-friendly result payload for ingestion graphs."""

        return {
            "result": {
                "source_uri": state.get("source_uri"),
                "source_name": state.get("source_name"),
                "ingest_job_id": state.get("ingest_job_id"),
                "registered_document_ids": state.get("registered_document_ids", []),
                "registered_version_ids": state.get("registered_version_ids", []),
                "chunk_count": len(state.get("chunks", [])),
                "cleaned_chunk_count": state.get("cleaned_chunk_count", 0),
                "upserted_count": state.get("upserted_count", 0),
                "status": state.get("ingest_status", "completed"),
                "error": state.get("error"),
                "source_storage": (state.get("prepared_source") or {}).get("storage", {}),
            }
        }
