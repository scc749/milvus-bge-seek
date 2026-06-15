"""PostgreSQL schema and migration helpers for the RAG backend."""

from __future__ import annotations

from agent.config import get_settings


class PostgresSchemaManager:
    """Ensure required PostgreSQL schema objects exist."""

    def ensure_schema(self, conn) -> None:
        """Create required schema, tables, and indexes if they do not exist."""

        from psycopg import sql

        settings = get_settings()
        schema = sql.Identifier(settings.postgres_schema)
        with conn.cursor() as cur:
            cur.execute(sql.SQL("create schema if not exists {}").format(schema))
            cur.execute(sql.SQL("set search_path to {}").format(schema))
            cur.execute(
                """
                create table if not exists assistant_thread (
                    thread_id text primary key,
                    title text not null default '新对话',
                    status text not null default 'regular',
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now()
                )
                """
            )
            cur.execute(
                """
                create table if not exists assistant_message (
                    message_id text primary key,
                    thread_id text not null references assistant_thread(thread_id) on delete cascade,
                    sequence_number integer not null,
                    role text,
                    type text not null,
                    content_text text,
                    content_json jsonb not null default '[]'::jsonb,
                    additional_kwargs_json jsonb not null default '{}'::jsonb,
                    response_metadata_json jsonb not null default '{}'::jsonb,
                    created_at timestamptz not null default now(),
                    unique (thread_id, sequence_number)
                )
                """
            )
            cur.execute(
                """
                create table if not exists ingest_job (
                    ingest_job_id text primary key,
                    source_uri text,
                    status text not null,
                    document_count integer not null default 0,
                    chunk_count integer not null default 0,
                    upserted_count integer not null default 0,
                    error text,
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now()
                )
                """
            )
            cur.execute(
                """
                create table if not exists document (
                    document_id text primary key,
                    ingest_job_id text references ingest_job(ingest_job_id) on delete set null,
                    source_uri text not null,
                    source_type text not null,
                    title text,
                    content_hash text not null,
                    status text not null,
                    current_version_id text,
                    current_version_number integer not null default 0,
                    current_chunk_count integer not null default 0,
                    metadata jsonb not null default '{}'::jsonb,
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now()
                )
                """
            )
            cur.execute(
                """
                alter table document add column if not exists current_version_id text
                """
            )
            cur.execute(
                """
                alter table document add column if not exists current_version_number integer not null default 0
                """
            )
            cur.execute(
                """
                alter table document add column if not exists current_chunk_count integer not null default 0
                """
            )
            cur.execute(
                """
                create table if not exists document_version (
                    version_id text primary key,
                    document_id text not null references document(document_id) on delete cascade,
                    ingest_job_id text references ingest_job(ingest_job_id) on delete set null,
                    version_number integer not null,
                    source_uri text not null,
                    source_type text not null,
                    title text,
                    content_hash text not null,
                    content_length integer not null default 0,
                    chunk_count integer not null default 0,
                    status text not null,
                    metadata jsonb not null default '{}'::jsonb,
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now(),
                    unique (document_id, version_number)
                )
                """
            )
            cur.execute(
                """
                create table if not exists document_source_storage (
                    source_storage_id text primary key,
                    document_id text not null references document(document_id) on delete cascade,
                    version_id text not null references document_version(version_id) on delete cascade,
                    ingest_job_id text references ingest_job(ingest_job_id) on delete set null,
                    original_source_uri text not null,
                    replay_source_uri text not null,
                    source_name text,
                    source_mime_type text,
                    input_mode text not null,
                    configured_backend text not null default 'local',
                    effective_backend text not null default 'local',
                    storage_uri text,
                    local_path text,
                    bucket text,
                    object_key text,
                    sync_status text,
                    sync_error text,
                    synced_file_count integer not null default 0,
                    path_mapping jsonb not null default '{}'::jsonb,
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now(),
                    unique (version_id)
                )
                """
            )
            cur.execute(
                """
                create table if not exists delete_job (
                    delete_job_id text primary key,
                    document_id text references document(document_id) on delete set null,
                    status text not null,
                    reason text,
                    chunk_count integer not null default 0,
                    error text,
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now()
                )
                """
            )
            cur.execute(
                """
                create table if not exists chunk_manifest (
                    manifest_id text primary key,
                    version_id text not null references document_version(version_id) on delete cascade,
                    document_id text not null references document(document_id) on delete cascade,
                    ingest_job_id text references ingest_job(ingest_job_id) on delete set null,
                    delete_job_id text references delete_job(delete_job_id) on delete set null,
                    chunk_id text not null,
                    chunk_index integer not null,
                    version_number integer not null default 1,
                    content_hash text not null,
                    content_length integer not null default 0,
                    lifecycle_status text not null default 'active',
                    archived_at timestamptz,
                    metadata jsonb not null default '{}'::jsonb,
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now(),
                    unique (version_id, chunk_index)
                )
                """
            )
            cur.execute(
                """
                alter table chunk_manifest add column if not exists delete_job_id text
                references delete_job(delete_job_id) on delete set null
                """
            )
            cur.execute(
                """
                alter table chunk_manifest add column if not exists lifecycle_status text not null default 'active'
                """
            )
            cur.execute(
                """
                alter table chunk_manifest add column if not exists archived_at timestamptz
                """
            )
            cur.execute(
                """
                create index if not exists idx_assistant_thread_updated_at
                on assistant_thread (updated_at desc)
                """
            )
            cur.execute(
                """
                create index if not exists idx_assistant_message_thread_id
                on assistant_message (thread_id, sequence_number)
                """
            )
            cur.execute(
                """
                create index if not exists idx_delete_job_document_id
                on delete_job (document_id)
                """
            )
            cur.execute(
                """
                create index if not exists idx_document_ingest_job_id
                on document (ingest_job_id)
                """
            )
            cur.execute(
                """
                create index if not exists idx_document_version_document_id
                on document_version (document_id)
                """
            )
            cur.execute(
                """
                create index if not exists idx_document_version_ingest_job_id
                on document_version (ingest_job_id)
                """
            )
            cur.execute(
                """
                create index if not exists idx_document_source_storage_document_id
                on document_source_storage (document_id)
                """
            )
            cur.execute(
                """
                create index if not exists idx_document_source_storage_version_id
                on document_source_storage (version_id)
                """
            )
            cur.execute(
                """
                create index if not exists idx_document_source_storage_ingest_job_id
                on document_source_storage (ingest_job_id)
                """
            )
            cur.execute(
                """
                create index if not exists idx_chunk_manifest_document_id
                on chunk_manifest (document_id)
                """
            )
            cur.execute(
                """
                create index if not exists idx_chunk_manifest_version_id
                on chunk_manifest (version_id)
                """
            )
            cur.execute(
                """
                create index if not exists idx_chunk_manifest_chunk_id
                on chunk_manifest (chunk_id)
                """
            )
            cur.execute(
                """
                create index if not exists idx_chunk_manifest_lifecycle_status
                on chunk_manifest (lifecycle_status)
                """
            )
