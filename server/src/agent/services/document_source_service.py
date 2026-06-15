"""Domain service for source metadata enrichment and reindex replay mapping."""

from __future__ import annotations

from typing import Any


class DocumentSourceService:
    """Handle source metadata shaping independent from ingest/delete use cases."""

    def enrich_raw_documents(
        self,
        raw_documents: list[dict[str, Any]],
        prepared_source_state: dict[str, object],
    ) -> list[dict[str, Any]]:
        """Attach source storage and replay metadata to raw loaded documents."""

        prepared_source = prepared_source_state.get("prepared_source")
        if not isinstance(prepared_source, dict):
            return raw_documents

        display_source_uri = str(prepared_source.get("display_source_uri") or "")
        path_mapping = prepared_source.get("path_mapping")
        source_mapping = path_mapping if isinstance(path_mapping, dict) else {}
        storage = prepared_source.get("storage")
        source_storage = storage if isinstance(storage, dict) else {}
        input_mode = str(prepared_source.get("input_mode") or "")
        load_options = prepared_source.get("load_options")
        load_options_payload = load_options if isinstance(load_options, dict) else {}
        source_name = prepared_source.get("source_name")
        source_mime_type = prepared_source.get("source_mime_type")

        enriched_documents: list[dict[str, Any]] = []
        for raw in raw_documents:
            replay_source_uri = str(raw.get("source_uri") or "")
            if input_mode == "url" and not source_mapping:
                original_source_uri = replay_source_uri or display_source_uri
            else:
                original_source_uri = str(
                    source_mapping.get(replay_source_uri) or display_source_uri or replay_source_uri
                )
            metadata = dict(raw.get("metadata", {}))
            metadata.update(
                {
                    "original_source_uri": original_source_uri,
                    "replay_source_uri": replay_source_uri,
                    "source_storage": source_storage,
                    "source_path_mapping": source_mapping,
                    "source_input_mode": input_mode,
                    "source_load_options": load_options_payload,
                    "source_name": source_name or raw.get("title"),
                    "source_mime_type": source_mime_type,
                }
            )
            enriched_documents.append(
                {
                    **raw,
                    "source_uri": original_source_uri,
                    "metadata": metadata,
                }
            )
        return enriched_documents

    def public_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Remove internal-only storage fields from metadata exposed to graph state."""

        cleaned = dict(metadata)
        cleaned.pop("source_storage", None)
        cleaned.pop("replay_source_uri", None)
        cleaned.pop("source_path_mapping", None)
        return cleaned

    def pin_document_identity(
        self,
        *,
        raw_documents: list[dict[str, Any]],
        document_id: str | None,
        source_uri: str | None = None,
        document_record: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Force reindex flow to reuse the existing document identifier."""

        if not document_id:
            return raw_documents

        pinned_documents: list[dict[str, Any]] = []
        source_storage = (document_record or {}).get("source_storage")
        source_storage_payload = source_storage if isinstance(source_storage, dict) else {}
        previous_path_mapping = source_storage_payload.get("path_mapping")
        previous_path_mapping_payload = (
            previous_path_mapping if isinstance(previous_path_mapping, dict) else {}
        )
        for raw in raw_documents:
            metadata = dict(raw.get("metadata", {}))
            metadata["document_id"] = document_id
            current_path_mapping = metadata.get("source_path_mapping")
            current_path_mapping_payload = (
                current_path_mapping if isinstance(current_path_mapping, dict) else {}
            )
            original_source_uri = str(
                previous_path_mapping_payload.get(raw.get("source_uri", ""))
                or (document_record or {}).get("source_uri")
                or source_uri
                or ""
            )
            composed_path_mapping = {
                replay_uri: str(previous_path_mapping_payload.get(mapped_uri) or mapped_uri)
                for replay_uri, mapped_uri in current_path_mapping_payload.items()
            }
            metadata["source_path_mapping"] = composed_path_mapping
            metadata["replay_source_uri"] = (
                metadata.get("replay_source_uri") or raw.get("source_uri", "")
            )
            pinned_documents.append(
                {
                    **raw,
                    "metadata": metadata,
                    "source_uri": original_source_uri,
                    "title": raw.get("title") or (document_record or {}).get("title"),
                }
            )
        return pinned_documents
