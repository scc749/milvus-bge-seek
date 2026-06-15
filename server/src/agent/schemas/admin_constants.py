"""Shared admin constants for backend contracts and future frontend reuse."""

from __future__ import annotations

ADMIN_OPERATIONS = [
    "list_documents",
    "get_document_detail",
    "list_document_versions",
    "list_ingest_jobs",
    "get_ingest_job_detail",
    "list_delete_jobs",
    "get_delete_job_detail",
    "get_page_contract",
]

ADMIN_PAGE_NAMES = [
    "document_list",
    "document_detail",
    "ingest_job",
    "delete_job",
]

DOCUMENT_STATUSES = ["processing", "completed", "deleted"]
VERSION_STATUSES = ["processing", "completed", "superseded", "deleted"]
JOB_STATUSES = ["created", "processing", "completed", "failed"]
SOURCE_TYPES = ["url", "file", "directory", "memory", "text"]

DOCUMENT_SORT_FIELDS = [
    "updated_at",
    "title",
    "source_type",
    "status",
    "current_version_number",
]

VERSION_SORT_FIELDS = [
    "version_number",
    "updated_at",
    "created_at",
    "status",
    "chunk_count",
]

JOB_SORT_FIELDS = [
    "updated_at",
    "created_at",
    "status",
    "chunk_count",
]
