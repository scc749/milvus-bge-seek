"""Write-oriented PostgreSQL repository for document lifecycle state."""

from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any
from uuid import uuid4

from agent.repositories.postgres_base import PostgresRepositoryBase


class PostgresRegistryRepository(PostgresRepositoryBase):
    """Persist ingest, version, manifest, and deletion state."""

    def create_ingest_job(self, source_uri: str | None) -> str | None:
        ingest_job_id = f"ing_{uuid4().hex}"
        try:
            with self._transaction() as conn:
                if conn is None:
                    return None
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        insert into ingest_job (
                            ingest_job_id, source_uri, status, created_at, updated_at
                        )
                        values (%s, %s, %s, now(), now())
                        """,
                        (ingest_job_id, source_uri, "created"),
                    )
        except Exception:
            return None
        return ingest_job_id

    def mark_ingest_job_processing(
        self,
        ingest_job_id: str | None,
        *,
        source_uri: str | None = None,
    ) -> None:
        if not ingest_job_id:
            return
        try:
            with self._transaction() as conn:
                if conn is None:
                    return
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        update ingest_job
                        set source_uri = coalesce(%s, source_uri),
                            status = %s,
                            updated_at = now()
                        where ingest_job_id = %s
                        """,
                        (source_uri, "processing", ingest_job_id),
                    )
        except Exception:
            return

    def register_documents(
        self,
        normalized_documents: list[dict[str, Any]],
        ingest_job_id: str | None = None,
    ) -> list[dict[str, Any]]:
        registered_records: list[dict[str, Any]] = []
        try:
            with self._transaction() as conn:
                if conn is None:
                    return []
                with conn.cursor() as cur:
                    for doc in normalized_documents:
                        document_id = doc["document_id"]
                        content = doc.get("content", "")
                        content_hash = self._hash_content(content)
                        content_length = len(content)
                        raw_metadata = dict(doc.get("metadata", {}))
                        metadata_json = self._to_json(self._document_metadata(raw_metadata))
                        cur.execute(
                            """
                            select current_version_id, current_version_number
                            from document
                            where document_id = %s
                            """,
                            (document_id,),
                        )
                        existing = cur.fetchone()
                        previous_version_id = existing[0] if existing and existing[0] else None
                        current_version_number = (
                            int(existing[1]) if existing and existing[1] is not None else 0
                        )
                        version_number = current_version_number + 1
                        version_id = f"ver_{uuid4().hex}"
                        cur.execute(
                            """
                            insert into document (
                                document_id,
                                ingest_job_id,
                                source_uri,
                                source_type,
                                title,
                                content_hash,
                                status,
                                current_version_id,
                                current_version_number,
                                current_chunk_count,
                                metadata,
                                created_at,
                                updated_at
                            )
                            values (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, now(), now()
                            )
                            on conflict (document_id) do update
                            set ingest_job_id = excluded.ingest_job_id,
                                source_uri = excluded.source_uri,
                                source_type = excluded.source_type,
                                title = excluded.title,
                                content_hash = excluded.content_hash,
                                status = excluded.status,
                                current_version_id = excluded.current_version_id,
                                current_version_number = excluded.current_version_number,
                                metadata = excluded.metadata,
                                updated_at = now()
                            """,
                            (
                                document_id,
                                ingest_job_id,
                                doc.get("source_uri", ""),
                                doc.get("source_type", "text"),
                                doc.get("title"),
                                content_hash,
                                "processing",
                                version_id,
                                version_number,
                                0,
                                metadata_json,
                            ),
                        )
                        cur.execute(
                            """
                            insert into document_version (
                                version_id,
                                document_id,
                                ingest_job_id,
                                version_number,
                                source_uri,
                                source_type,
                                title,
                                content_hash,
                                content_length,
                                chunk_count,
                                status,
                                metadata,
                                created_at,
                                updated_at
                            )
                            values (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, now(), now()
                            )
                            """,
                            (
                                version_id,
                                document_id,
                                ingest_job_id,
                                version_number,
                                doc.get("source_uri", ""),
                                doc.get("source_type", "text"),
                                doc.get("title"),
                                content_hash,
                                content_length,
                                0,
                                "processing",
                                metadata_json,
                            ),
                        )
                        source_storage_record = self._source_storage_record(
                            document_id=document_id,
                            version_id=version_id,
                            ingest_job_id=ingest_job_id,
                            source_uri=doc.get("source_uri", ""),
                            source_name=doc.get("title"),
                            metadata=raw_metadata,
                        )
                        if source_storage_record is not None:
                            cur.execute(
                                """
                                insert into document_source_storage (
                                    source_storage_id,
                                    document_id,
                                    version_id,
                                    ingest_job_id,
                                    original_source_uri,
                                    replay_source_uri,
                                    source_name,
                                    source_mime_type,
                                    input_mode,
                                    configured_backend,
                                    effective_backend,
                                    storage_uri,
                                    local_path,
                                    bucket,
                                    object_key,
                                    sync_status,
                                    sync_error,
                                    synced_file_count,
                                    path_mapping,
                                    created_at,
                                    updated_at
                                )
                                values (
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, now(), now()
                                )
                                on conflict (version_id) do update
                                set original_source_uri = excluded.original_source_uri,
                                    replay_source_uri = excluded.replay_source_uri,
                                    source_name = excluded.source_name,
                                    source_mime_type = excluded.source_mime_type,
                                    input_mode = excluded.input_mode,
                                    configured_backend = excluded.configured_backend,
                                    effective_backend = excluded.effective_backend,
                                    storage_uri = excluded.storage_uri,
                                    local_path = excluded.local_path,
                                    bucket = excluded.bucket,
                                    object_key = excluded.object_key,
                                    sync_status = excluded.sync_status,
                                    sync_error = excluded.sync_error,
                                    synced_file_count = excluded.synced_file_count,
                                    path_mapping = excluded.path_mapping,
                                    updated_at = now()
                                """,
                                (
                                    source_storage_record["source_storage_id"],
                                    source_storage_record["document_id"],
                                    source_storage_record["version_id"],
                                    source_storage_record["ingest_job_id"],
                                    source_storage_record["original_source_uri"],
                                    source_storage_record["replay_source_uri"],
                                    source_storage_record["source_name"],
                                    source_storage_record["source_mime_type"],
                                    source_storage_record["input_mode"],
                                    source_storage_record["configured_backend"],
                                    source_storage_record["effective_backend"],
                                    source_storage_record["storage_uri"],
                                    source_storage_record["local_path"],
                                    source_storage_record["bucket"],
                                    source_storage_record["object_key"],
                                    source_storage_record["sync_status"],
                                    source_storage_record["sync_error"],
                                    source_storage_record["synced_file_count"],
                                    self._to_json(source_storage_record["path_mapping"]),
                                ),
                            )
                        registered_records.append(
                            {
                                "document_id": document_id,
                                "version_id": version_id,
                                "version_number": version_number,
                                "previous_version_id": previous_version_id,
                                "content_hash": content_hash,
                            }
                        )
                    if ingest_job_id:
                        cur.execute(
                            """
                            update ingest_job
                            set status = %s,
                                document_count = %s,
                                updated_at = now()
                            where ingest_job_id = %s
                            """,
                            ("processing", len(normalized_documents), ingest_job_id),
                        )
        except Exception:
            return []
        return registered_records

    def finalize_ingest_job(
        self,
        ingest_job_id: str | None,
        chunks: list[dict[str, Any]],
        upserted_count: int,
        status: str = "completed",
        error: str | None = None,
        replaced_version_ids: list[str] | None = None,
    ) -> None:
        try:
            chunk_count_by_document = Counter(
                chunk["document_id"] for chunk in chunks if chunk.get("document_id")
            )
            chunk_count_by_version = Counter(
                chunk["version_id"] for chunk in chunks if chunk.get("version_id")
            )
            with self._transaction() as conn:
                if conn is None:
                    return
                with conn.cursor() as cur:
                    if ingest_job_id:
                        cur.execute(
                            """
                            update ingest_job
                            set status = %s,
                                chunk_count = %s,
                                upserted_count = %s,
                                error = %s,
                                updated_at = now()
                            where ingest_job_id = %s
                            """,
                            (status, len(chunks), upserted_count, error, ingest_job_id),
                        )
                        cur.execute(
                            """
                            update document
                            set status = %s,
                                current_chunk_count = 0,
                                updated_at = now()
                            where ingest_job_id = %s
                            """,
                            (status, ingest_job_id),
                        )
                        cur.execute(
                            """
                            update document_version
                            set status = %s,
                                chunk_count = 0,
                                updated_at = now()
                            where ingest_job_id = %s
                            """,
                            (status, ingest_job_id),
                        )

                    if status == "completed" and chunks:
                        for chunk in chunks:
                            version_id = chunk.get("version_id")
                            if not version_id:
                                continue
                            metadata_json = self._to_json(chunk.get("metadata", {}))
                            content = chunk.get("content", "")
                            cur.execute(
                                """
                                insert into chunk_manifest (
                                    manifest_id,
                                    version_id,
                                    document_id,
                                    ingest_job_id,
                                    chunk_id,
                                    chunk_index,
                                    version_number,
                                    content_hash,
                                    content_length,
                                    metadata,
                                    created_at,
                                    updated_at
                                )
                                values (
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, now(), now()
                                )
                                on conflict (manifest_id) do update
                                set ingest_job_id = excluded.ingest_job_id,
                                    chunk_id = excluded.chunk_id,
                                    chunk_index = excluded.chunk_index,
                                    version_number = excluded.version_number,
                                    content_hash = excluded.content_hash,
                                    content_length = excluded.content_length,
                                    metadata = excluded.metadata,
                                    lifecycle_status = 'active',
                                    archived_at = null,
                                    updated_at = now()
                                """,
                                (
                                    self._manifest_id(version_id, int(chunk.get("chunk_index", 0))),
                                    version_id,
                                    chunk["document_id"],
                                    ingest_job_id,
                                    chunk["chunk_id"],
                                    int(chunk.get("chunk_index", 0)),
                                    int(chunk.get("version_number", 1)),
                                    self._hash_content(content),
                                    len(content),
                                    metadata_json,
                                ),
                            )

                    for document_id, chunk_count in chunk_count_by_document.items():
                        cur.execute(
                            """
                            update document
                            set status = %s,
                                current_chunk_count = %s,
                                updated_at = now()
                            where document_id = %s
                            """,
                            (status, chunk_count, document_id),
                        )

                    for version_id, chunk_count in chunk_count_by_version.items():
                        cur.execute(
                            """
                            update document_version
                            set status = %s,
                                chunk_count = %s,
                                updated_at = now()
                            where version_id = %s
                            """,
                            (status, chunk_count, version_id),
                        )

                    if status == "completed":
                        for version_id in replaced_version_ids or []:
                            cur.execute(
                                """
                                update document_version
                                set status = %s,
                                    updated_at = now()
                                where version_id = %s
                                """,
                                ("superseded", version_id),
                            )
                            cur.execute(
                                """
                                update chunk_manifest
                                set lifecycle_status = %s,
                                    archived_at = now(),
                                    updated_at = now()
                                where version_id = %s
                                """,
                                ("superseded", version_id),
                            )
        except Exception:
            return

    def create_delete_job(self, document_id: str, reason: str | None = None) -> str | None:
        delete_job_id = f"del_{uuid4().hex}"
        try:
            with self._transaction() as conn:
                if conn is None:
                    return None
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        insert into delete_job (
                            delete_job_id, document_id, status, reason, created_at, updated_at
                        )
                        values (%s, %s, %s, %s, now(), now())
                        """,
                        (delete_job_id, document_id, "created", reason),
                    )
        except Exception:
            return None
        return delete_job_id

    def get_chunk_ids_by_version_ids(self, version_ids: list[str]) -> list[str]:
        if not version_ids:
            return []
        conn = self._connect()
        if conn is None:
            return []
        try:
            with conn.cursor() as cur:
                chunk_ids: list[str] = []
                for version_id in version_ids:
                    cur.execute(
                        """
                        select chunk_id
                        from chunk_manifest
                        where version_id = %s
                        order by chunk_index asc
                        """,
                        (version_id,),
                    )
                    chunk_ids.extend(row[0] for row in cur.fetchall())
                return sorted(set(chunk_ids))
        except Exception:
            return []
        finally:
            conn.close()

    def get_document_chunk_ids(self, document_id: str) -> list[str]:
        conn = self._connect()
        if conn is None:
            return []
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select distinct chunk_id
                    from chunk_manifest
                    where document_id = %s
                    order by chunk_id asc
                    """,
                    (document_id,),
                )
                return [row[0] for row in cur.fetchall()]
        except Exception:
            return []
        finally:
            conn.close()

    def get_document_record(self, document_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        if conn is None:
            return None
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select
                        document_id,
                        source_uri,
                        source_type,
                        title,
                        status,
                        current_version_id,
                        current_version_number,
                        current_chunk_count,
                        metadata
                    from document
                    where document_id = %s
                    """,
                    (document_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                cur.execute(
                    """
                    select
                        original_source_uri,
                        replay_source_uri,
                        source_name,
                        source_mime_type,
                        input_mode,
                        configured_backend,
                        effective_backend,
                        storage_uri,
                        local_path,
                        bucket,
                        object_key,
                        sync_status,
                        sync_error,
                        synced_file_count,
                        path_mapping
                    from document_source_storage
                    where version_id = %s
                    """,
                    (row[5],),
                )
                storage_row = cur.fetchone()
                return {
                    "document_id": row[0],
                    "source_uri": row[1],
                    "source_type": row[2],
                    "title": row[3],
                    "status": row[4],
                    "current_version_id": row[5],
                    "current_version_number": row[6],
                    "current_chunk_count": row[7],
                    "metadata": row[8] or {},
                    "source_storage": self._row_to_source_storage(storage_row),
                }
        except Exception:
            return None
        finally:
            conn.close()

    def finalize_delete_job(
        self,
        delete_job_id: str | None,
        document_id: str,
        deleted_chunk_count: int,
        status: str = "completed",
        error: str | None = None,
    ) -> None:
        try:
            with self._transaction() as conn:
                if conn is None:
                    return
                with conn.cursor() as cur:
                    if delete_job_id:
                        cur.execute(
                            """
                            update delete_job
                            set status = %s,
                                chunk_count = %s,
                                error = %s,
                                updated_at = now()
                            where delete_job_id = %s
                            """,
                            (status, deleted_chunk_count, error, delete_job_id),
                        )
                    cur.execute(
                        """
                        update document
                        set status = %s,
                            current_version_id = null,
                            current_chunk_count = 0,
                            updated_at = now()
                        where document_id = %s
                        """,
                        ("deleted", document_id),
                    )
                    cur.execute(
                        """
                        update document_version
                        set status = %s,
                            updated_at = now()
                        where document_id = %s
                        """,
                        ("deleted", document_id),
                    )
                    cur.execute(
                        """
                        update chunk_manifest
                        set lifecycle_status = %s,
                            archived_at = now(),
                            delete_job_id = %s,
                            updated_at = now()
                        where document_id = %s
                        """,
                        ("deleted", delete_job_id, document_id),
                    )
        except Exception:
            return

    def _manifest_id(self, version_id: str, chunk_index: int) -> str:
        return f"{version_id}::chunk::{chunk_index}"

    def _source_storage_record(
        self,
        *,
        document_id: str,
        version_id: str,
        ingest_job_id: str | None,
        source_uri: str,
        source_name: str | None,
        metadata: dict[str, Any],
    ) -> dict[str, Any] | None:
        replay_source_uri = metadata.get("replay_source_uri")
        input_mode = metadata.get("source_input_mode")
        source_storage = metadata.get("source_storage")
        path_mapping = metadata.get("source_path_mapping")
        if not replay_source_uri and not input_mode and not source_storage:
            return None
        source_storage_payload = source_storage if isinstance(source_storage, dict) else {}
        path_mapping_payload = path_mapping if isinstance(path_mapping, dict) else {}
        effective_backend = source_storage_payload.get("effective_backend")
        configured_backend = source_storage_payload.get("configured_backend")
        if not configured_backend:
            configured_backend = "external" if input_mode == "url" else "local"
        if not effective_backend:
            effective_backend = "external" if input_mode == "url" else "local"
        return {
            "source_storage_id": f"src_{uuid4().hex}",
            "document_id": document_id,
            "version_id": version_id,
            "ingest_job_id": ingest_job_id,
            "original_source_uri": source_uri,
            "replay_source_uri": str(replay_source_uri or source_uri),
            "source_name": metadata.get("source_name") or source_name,
            "source_mime_type": metadata.get("source_mime_type"),
            "input_mode": str(input_mode or "file"),
            "configured_backend": str(configured_backend),
            "effective_backend": str(effective_backend),
            "storage_uri": source_storage_payload.get("storage_uri"),
            "local_path": source_storage_payload.get("local_path"),
            "bucket": source_storage_payload.get("bucket"),
            "object_key": source_storage_payload.get("object_key"),
            "sync_status": source_storage_payload.get("sync_status"),
            "sync_error": source_storage_payload.get("sync_error"),
            "synced_file_count": int(source_storage_payload.get("synced_file_count") or 0),
            "path_mapping": path_mapping_payload,
        }

    def _document_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        cleaned = dict(metadata)
        cleaned.pop("source_storage", None)
        cleaned.pop("replay_source_uri", None)
        cleaned.pop("source_path_mapping", None)
        return cleaned

    def _row_to_source_storage(self, row: Any) -> dict[str, Any]:
        if row is None:
            return {}
        return {
            "original_source_uri": row[0],
            "replay_source_uri": row[1],
            "source_name": row[2],
            "source_mime_type": row[3],
            "input_mode": row[4],
            "configured_backend": row[5],
            "effective_backend": row[6],
            "storage_uri": row[7],
            "local_path": row[8],
            "bucket": row[9],
            "object_key": row[10],
            "sync_status": row[11],
            "sync_error": row[12],
            "synced_file_count": row[13],
            "path_mapping": row[14] or {},
        }

    def _hash_content(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _to_json(self, value: dict[str, Any]) -> str:
        import json

        return json.dumps(value, ensure_ascii=False)
