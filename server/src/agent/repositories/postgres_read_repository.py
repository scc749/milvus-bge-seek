"""Read-oriented PostgreSQL repository for admin/document-center queries."""

from __future__ import annotations

from typing import Any

from agent.repositories.postgres_base import PostgresRepositoryBase
from agent.schemas.admin_constants import (
    ADMIN_OPERATIONS,
    DOCUMENT_SORT_FIELDS,
    DOCUMENT_STATUSES,
    JOB_SORT_FIELDS,
    JOB_STATUSES,
    SOURCE_TYPES,
    VERSION_SORT_FIELDS,
    VERSION_STATUSES,
)
from agent.schemas.admin_contracts import AdminQueryMeta, AdminQueryResult, PageInfo, SortInfo


class PostgresReadRepository(PostgresRepositoryBase):
    """Run document-center and job-center queries with pagination, sorting, and details."""
    DOCUMENT_SORT_FIELDS_MAP = {field: field for field in DOCUMENT_SORT_FIELDS}
    VERSION_SORT_FIELDS_MAP = {field: field for field in VERSION_SORT_FIELDS}
    JOB_SORT_FIELDS_MAP = {field: field for field in JOB_SORT_FIELDS}

    def list_documents(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        source_type: str | None = None,
        query: str | None = None,
        sort_by: str = "updated_at",
        sort_direction: str = "desc",
    ) -> dict[str, Any]:
        conn = self._connect()
        if conn is None:
            return self._empty_page(
                operation="list_documents",
                page=page,
                page_size=page_size,
                filters={
                    "status": status,
                    "source_type": source_type,
                    "query": query,
                },
                sort_by=sort_by,
                sort_direction=sort_direction,
                sortable_fields=DOCUMENT_SORT_FIELDS,
                statuses=DOCUMENT_STATUSES,
                source_types=SOURCE_TYPES,
            )
        try:
            from psycopg import sql

            where_sql, params = self._document_filters(
                status=status,
                source_type=source_type,
                query=query,
            )
            order_clause, resolved_sort_by, resolved_direction = self._order_clause(
                sort_by=sort_by,
                sort_direction=sort_direction,
                allowed_fields=self.DOCUMENT_SORT_FIELDS_MAP,
            )
            offset = max(page - 1, 0) * page_size
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("select count(*) from document {where_sql}").format(
                        where_sql=where_sql
                    ),
                    params,
                )
                total = int(cur.fetchone()[0])
                cur.execute(
                    sql.SQL(
                        """
                        select
                            d.document_id,
                            d.source_uri,
                            d.source_type,
                            d.title,
                            d.status,
                            d.current_version_id,
                            d.current_version_number,
                            d.current_chunk_count,
                            d.updated_at,
                            dss.replay_source_uri,
                            dss.storage_uri,
                            dss.effective_backend,
                            dss.bucket,
                            dss.object_key,
                            dss.sync_status
                        from document d
                        left join document_source_storage dss
                            on dss.version_id = d.current_version_id
                        {where_sql}
                        order by {order_clause}
                        limit %s offset %s
                        """
                    ).format(
                        where_sql=where_sql,
                        order_clause=order_clause,
                    ),
                    (*params, page_size, offset),
                )
                records = [
                    {
                        "document_id": row[0],
                        "source_uri": row[1],
                        "source_type": row[2],
                        "title": row[3],
                        "status": row[4],
                        "current_version_id": row[5],
                        "current_version_number": row[6],
                        "current_chunk_count": row[7],
                        "updated_at": row[8].isoformat() if row[8] else None,
                        "replay_source_uri": row[9],
                        "source_storage": self._source_storage_payload(
                            replay_source_uri=row[9],
                            storage_uri=row[10],
                            effective_backend=row[11],
                            bucket=row[12],
                            object_key=row[13],
                            sync_status=row[14],
                        ),
                    }
                    for row in cur.fetchall()
                ]
            return AdminQueryResult(
                operation="list_documents",
                records=records,
                page_info=PageInfo(page=page, page_size=page_size, total=total),
                sort_info=SortInfo(field=resolved_sort_by, direction=resolved_direction),
                filters={
                    "status": status,
                    "source_type": source_type,
                    "query": query,
                },
                meta=self._meta(
                    sortable_fields=DOCUMENT_SORT_FIELDS,
                    statuses=DOCUMENT_STATUSES,
                    source_types=SOURCE_TYPES,
                ),
            ).to_dict()
        except Exception:
            return self._empty_page(
                operation="list_documents",
                page=page,
                page_size=page_size,
                filters={
                    "status": status,
                    "source_type": source_type,
                    "query": query,
                },
                sort_by=sort_by,
                sort_direction=sort_direction,
                sortable_fields=DOCUMENT_SORT_FIELDS,
                statuses=DOCUMENT_STATUSES,
                source_types=SOURCE_TYPES,
            )
        finally:
            conn.close()

    def get_document_detail(self, document_id: str) -> dict[str, Any]:
        conn = self._connect()
        if conn is None or not document_id:
            return self._empty_detail(
                operation="get_document_detail",
                document_id=document_id or None,
                sortable_fields=VERSION_SORT_FIELDS,
                statuses=VERSION_STATUSES,
                source_types=SOURCE_TYPES,
            )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select
                        d.document_id,
                        d.source_uri,
                        d.source_type,
                        d.title,
                        d.status,
                        d.current_version_id,
                        d.current_version_number,
                        d.current_chunk_count,
                        d.updated_at,
                        d.metadata,
                        dss.replay_source_uri,
                        dss.storage_uri,
                        dss.effective_backend,
                        dss.bucket,
                        dss.object_key,
                        dss.sync_status
                    from document d
                    left join document_source_storage dss
                        on dss.version_id = d.current_version_id
                    where d.document_id = %s
                    """,
                    (document_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return self._empty_detail(
                        operation="get_document_detail",
                        document_id=document_id,
                        sortable_fields=VERSION_SORT_FIELDS,
                        statuses=VERSION_STATUSES,
                        source_types=SOURCE_TYPES,
                    )
                cur.execute(
                    """
                    select
                        count(*) as version_total,
                        count(*) filter (where status = 'completed') as completed_versions,
                        count(*) filter (where status = 'superseded') as superseded_versions
                    from document_version
                    where document_id = %s
                    """,
                    (document_id,),
                )
                version_stats = cur.fetchone()
                cur.execute(
                    """
                    select
                        count(*) filter (where lifecycle_status = 'active') as active_chunk_total,
                        count(*) filter (where lifecycle_status = 'superseded') as superseded_chunk_total,
                        count(*) filter (where lifecycle_status = 'deleted') as deleted_chunk_total
                    from chunk_manifest
                    where document_id = %s
                    """,
                    (document_id,),
                )
                chunk_stats = cur.fetchone()
                cur.execute(
                    """
                    select
                        version_id,
                        version_number,
                        status,
                        chunk_count,
                        updated_at
                    from document_version
                    where document_id = %s
                    order by version_number desc
                    limit 5
                    """,
                    (document_id,),
                )
                recent_versions = [
                    {
                        "version_id": item[0],
                        "version_number": item[1],
                        "status": item[2],
                        "chunk_count": item[3],
                        "updated_at": item[4].isoformat() if item[4] else None,
                    }
                    for item in cur.fetchall()
                ]
                detail = {
                    "document_id": row[0],
                    "source_uri": row[1],
                    "source_type": row[2],
                    "title": row[3],
                    "status": row[4],
                    "current_version_id": row[5],
                    "current_version_number": row[6],
                    "current_chunk_count": row[7],
                    "updated_at": row[8].isoformat() if row[8] else None,
                    "metadata": row[9] or {},
                    "replay_source_uri": row[10],
                    "source_storage": self._source_storage_payload(
                        replay_source_uri=row[10],
                        storage_uri=row[11],
                        effective_backend=row[12],
                        bucket=row[13],
                        object_key=row[14],
                        sync_status=row[15],
                    ),
                    "stats": {
                        "version_total": int(version_stats[0] or 0),
                        "completed_versions": int(version_stats[1] or 0),
                        "superseded_versions": int(version_stats[2] or 0),
                        "active_chunk_total": int(chunk_stats[0] or 0),
                        "superseded_chunk_total": int(chunk_stats[1] or 0),
                        "deleted_chunk_total": int(chunk_stats[2] or 0),
                    },
                    "recent_versions": recent_versions,
                }
                return AdminQueryResult(
                    operation="get_document_detail",
                    document_id=document_id,
                    records=[detail],
                    meta=self._meta(
                        sortable_fields=VERSION_SORT_FIELDS,
                        statuses=VERSION_STATUSES,
                        source_types=SOURCE_TYPES,
                    ),
                ).to_dict()
        except Exception:
            return self._empty_detail(
                operation="get_document_detail",
                document_id=document_id,
                sortable_fields=VERSION_SORT_FIELDS,
                statuses=VERSION_STATUSES,
                source_types=SOURCE_TYPES,
            )
        finally:
            conn.close()

    def list_document_versions(
        self,
        document_id: str,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        sort_by: str = "version_number",
        sort_direction: str = "desc",
    ) -> dict[str, Any]:
        if not document_id:
            return self._empty_page(
                operation="list_document_versions",
                page=page,
                page_size=page_size,
                filters={"status": status},
                document_id=document_id or None,
                sort_by=sort_by,
                sort_direction=sort_direction,
                sortable_fields=VERSION_SORT_FIELDS,
                statuses=VERSION_STATUSES,
            )
        conn = self._connect()
        if conn is None:
            return self._empty_page(
                operation="list_document_versions",
                page=page,
                page_size=page_size,
                filters={"status": status},
                document_id=document_id,
                sort_by=sort_by,
                sort_direction=sort_direction,
                sortable_fields=VERSION_SORT_FIELDS,
                statuses=VERSION_STATUSES,
            )
        try:
            from psycopg import sql

            params: list[Any] = [document_id]
            where_sql = sql.SQL("where document_id = %s")
            if status:
                where_sql = sql.SQL("where document_id = %s and status = %s")
                params.append(status)
            order_clause, resolved_sort_by, resolved_direction = self._order_clause(
                sort_by=sort_by,
                sort_direction=sort_direction,
                allowed_fields=self.VERSION_SORT_FIELDS_MAP,
            )
            offset = max(page - 1, 0) * page_size
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("select count(*) from document_version {where_sql}").format(
                        where_sql=where_sql
                    ),
                    tuple(params),
                )
                total = int(cur.fetchone()[0])
                cur.execute(
                    sql.SQL(
                        """
                        select
                            version_id,
                            version_number,
                            status,
                            content_hash,
                            chunk_count,
                            created_at,
                            updated_at
                        from document_version
                        {where_sql}
                        order by {order_clause}
                        limit %s offset %s
                        """
                    ).format(
                        where_sql=where_sql,
                        order_clause=order_clause,
                    ),
                    (*params, page_size, offset),
                )
                records = [
                    {
                        "version_id": row[0],
                        "version_number": row[1],
                        "status": row[2],
                        "content_hash": row[3],
                        "chunk_count": row[4],
                        "created_at": row[5].isoformat() if row[5] else None,
                        "updated_at": row[6].isoformat() if row[6] else None,
                    }
                    for row in cur.fetchall()
                ]
            return AdminQueryResult(
                operation="list_document_versions",
                document_id=document_id,
                records=records,
                page_info=PageInfo(page=page, page_size=page_size, total=total),
                sort_info=SortInfo(field=resolved_sort_by, direction=resolved_direction),
                filters={"status": status},
                meta=self._meta(
                    sortable_fields=VERSION_SORT_FIELDS,
                    statuses=VERSION_STATUSES,
                ),
            ).to_dict()
        except Exception:
            return self._empty_page(
                operation="list_document_versions",
                page=page,
                page_size=page_size,
                filters={"status": status},
                document_id=document_id,
                sort_by=sort_by,
                sort_direction=sort_direction,
                sortable_fields=VERSION_SORT_FIELDS,
                statuses=VERSION_STATUSES,
            )
        finally:
            conn.close()

    def list_ingest_jobs(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        sort_by: str = "updated_at",
        sort_direction: str = "desc",
    ) -> dict[str, Any]:
        return self._list_jobs(
            table_name="ingest_job",
            operation="list_ingest_jobs",
            page=page,
            page_size=page_size,
            status=status,
            target_column="source_uri",
            id_column="ingest_job_id",
            sort_by=sort_by,
            sort_direction=sort_direction,
        )

    def list_delete_jobs(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        sort_by: str = "updated_at",
        sort_direction: str = "desc",
    ) -> dict[str, Any]:
        return self._list_jobs(
            table_name="delete_job",
            operation="list_delete_jobs",
            page=page,
            page_size=page_size,
            status=status,
            target_column="document_id",
            id_column="delete_job_id",
            sort_by=sort_by,
            sort_direction=sort_direction,
        )

    def get_ingest_job_detail(self, job_id: str) -> dict[str, Any]:
        conn = self._connect()
        if conn is None or not job_id:
            return self._empty_detail(
                operation="get_ingest_job_detail",
                job_id=job_id or None,
                sortable_fields=JOB_SORT_FIELDS,
                statuses=JOB_STATUSES,
            )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select
                        ingest_job_id,
                        source_uri,
                        status,
                        document_count,
                        chunk_count,
                        upserted_count,
                        error,
                        created_at,
                        updated_at
                    from ingest_job
                    where ingest_job_id = %s
                    """,
                    (job_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return self._empty_detail(
                        operation="get_ingest_job_detail",
                        job_id=job_id,
                        sortable_fields=JOB_SORT_FIELDS,
                        statuses=JOB_STATUSES,
                    )
                cur.execute(
                    """
                    select
                        d.document_id,
                        d.title,
                        d.status,
                        d.current_version_number,
                        d.current_chunk_count,
                        dss.replay_source_uri,
                        dss.storage_uri,
                        dss.effective_backend,
                        dss.bucket,
                        dss.object_key,
                        dss.sync_status
                    from document d
                    left join document_source_storage dss
                        on dss.version_id = d.current_version_id
                    where d.ingest_job_id = %s
                    order by d.updated_at desc
                    limit 10
                    """,
                    (job_id,),
                )
                documents = [
                    {
                        "document_id": item[0],
                        "title": item[1],
                        "status": item[2],
                        "current_version_number": item[3],
                        "current_chunk_count": item[4],
                        "replay_source_uri": item[5],
                        "source_storage": self._source_storage_payload(
                            replay_source_uri=item[5],
                            storage_uri=item[6],
                            effective_backend=item[7],
                            bucket=item[8],
                            object_key=item[9],
                            sync_status=item[10],
                        ),
                    }
                    for item in cur.fetchall()
                ]
                cur.execute(
                    """
                    select
                        count(*) as version_total,
                        count(*) filter (where status = 'completed') as completed_versions,
                        count(*) filter (where status = 'superseded') as superseded_versions,
                        count(*) filter (where status = 'deleted') as deleted_versions
                    from document_version
                    where ingest_job_id = %s
                    """,
                    (job_id,),
                )
                version_stats = cur.fetchone()
                cur.execute(
                    """
                    select
                        count(*) filter (where lifecycle_status = 'active') as active_chunk_total,
                        count(*) filter (where lifecycle_status = 'superseded') as superseded_chunk_total,
                        count(*) filter (where lifecycle_status = 'deleted') as deleted_chunk_total
                    from chunk_manifest
                    where ingest_job_id = %s
                    """,
                    (job_id,),
                )
                chunk_stats = cur.fetchone()
                detail = {
                    "job_id": row[0],
                    "source_uri": row[1],
                    "status": row[2],
                    "document_count": row[3],
                    "chunk_count": row[4],
                    "upserted_count": row[5],
                    "error": row[6],
                    "created_at": row[7].isoformat() if row[7] else None,
                    "updated_at": row[8].isoformat() if row[8] else None,
                    "stats": {
                        "document_total": int(row[3] or 0),
                        "chunk_total": int(row[4] or 0),
                        "upserted_total": int(row[5] or 0),
                        "version_total": int(version_stats[0] or 0),
                        "completed_versions": int(version_stats[1] or 0),
                        "superseded_versions": int(version_stats[2] or 0),
                        "deleted_versions": int(version_stats[3] or 0),
                        "active_chunk_total": int(chunk_stats[0] or 0),
                        "superseded_chunk_total": int(chunk_stats[1] or 0),
                        "deleted_chunk_total": int(chunk_stats[2] or 0),
                    },
                    "documents": documents,
                }
                return AdminQueryResult(
                    operation="get_ingest_job_detail",
                    job_id=job_id,
                    records=[detail],
                    meta=self._meta(
                        sortable_fields=JOB_SORT_FIELDS,
                        statuses=JOB_STATUSES,
                    ),
                ).to_dict()
        except Exception:
            return self._empty_detail(
                operation="get_ingest_job_detail",
                job_id=job_id,
                sortable_fields=JOB_SORT_FIELDS,
                statuses=JOB_STATUSES,
            )
        finally:
            conn.close()

    def get_delete_job_detail(self, job_id: str) -> dict[str, Any]:
        conn = self._connect()
        if conn is None or not job_id:
            return self._empty_detail(
                operation="get_delete_job_detail",
                job_id=job_id or None,
                sortable_fields=JOB_SORT_FIELDS,
                statuses=JOB_STATUSES,
            )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select
                        delete_job_id,
                        document_id,
                        status,
                        reason,
                        chunk_count,
                        error,
                        created_at,
                        updated_at
                    from delete_job
                    where delete_job_id = %s
                    """,
                    (job_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return self._empty_detail(
                        operation="get_delete_job_detail",
                        job_id=job_id,
                        sortable_fields=JOB_SORT_FIELDS,
                        statuses=JOB_STATUSES,
                    )
                cur.execute(
                    """
                    select count(*)
                    from chunk_manifest
                    where delete_job_id = %s
                    """,
                    (job_id,),
                )
                manifest_total = int(cur.fetchone()[0] or 0)
                cur.execute(
                    """
                    select
                        d.title,
                        d.source_uri,
                        d.source_type,
                        d.status,
                        ss.replay_source_uri,
                        ss.storage_uri,
                        ss.effective_backend,
                        ss.bucket,
                        ss.object_key,
                        ss.sync_status,
                        count(*) filter (where dv.status = 'deleted') as deleted_versions
                    from document d
                    left join document_version dv on dv.document_id = d.document_id
                    left join lateral (
                        select
                            replay_source_uri,
                            storage_uri,
                            effective_backend,
                            bucket,
                            object_key,
                            sync_status
                        from document_source_storage
                        where document_id = d.document_id
                        order by updated_at desc
                        limit 1
                    ) ss on true
                    where d.document_id = %s
                    group by d.document_id, d.title, d.source_uri, d.source_type, d.status, ss.replay_source_uri, ss.storage_uri, ss.effective_backend, ss.bucket, ss.object_key, ss.sync_status
                    """,
                    (row[1],),
                )
                document_row = cur.fetchone()
                cur.execute(
                    """
                    select
                        count(*) filter (where lifecycle_status = 'active') as active_chunk_total,
                        count(*) filter (where lifecycle_status = 'superseded') as superseded_chunk_total,
                        count(*) filter (where lifecycle_status = 'deleted') as deleted_chunk_total
                    from chunk_manifest
                    where delete_job_id = %s
                    """,
                    (job_id,),
                )
                chunk_stats = cur.fetchone()
                detail = {
                    "job_id": row[0],
                    "document_id": row[1],
                    "status": row[2],
                    "reason": row[3],
                    "chunk_count": row[4],
                    "error": row[5],
                    "created_at": row[6].isoformat() if row[6] else None,
                    "updated_at": row[7].isoformat() if row[7] else None,
                    "archived_manifest_total": manifest_total,
                    "stats": {
                        "archived_manifest_total": manifest_total,
                        "active_chunk_total": int(chunk_stats[0] or 0),
                        "superseded_chunk_total": int(chunk_stats[1] or 0),
                        "deleted_chunk_total": int(chunk_stats[2] or 0),
                        "deleted_versions": int(document_row[10] or 0) if document_row else 0,
                    },
                    "document": (
                        {
                            "title": document_row[0],
                            "source_uri": document_row[1],
                            "source_type": document_row[2],
                            "status": document_row[3],
                            "replay_source_uri": document_row[4],
                            "source_storage": self._source_storage_payload(
                                replay_source_uri=document_row[4],
                                storage_uri=document_row[5],
                                effective_backend=document_row[6],
                                bucket=document_row[7],
                                object_key=document_row[8],
                                sync_status=document_row[9],
                            ),
                        }
                        if document_row
                        else {}
                    ),
                }
                return AdminQueryResult(
                    operation="get_delete_job_detail",
                    job_id=job_id,
                    records=[detail],
                    meta=self._meta(
                        sortable_fields=JOB_SORT_FIELDS,
                        statuses=JOB_STATUSES,
                    ),
                ).to_dict()
        except Exception:
            return self._empty_detail(
                operation="get_delete_job_detail",
                job_id=job_id,
                sortable_fields=JOB_SORT_FIELDS,
                statuses=JOB_STATUSES,
            )
        finally:
            conn.close()

    def _list_jobs(
        self,
        table_name: str,
        operation: str,
        page: int,
        page_size: int,
        status: str | None,
        target_column: str,
        id_column: str,
        sort_by: str,
        sort_direction: str,
    ) -> dict[str, Any]:
        conn = self._connect()
        if conn is None:
            return self._empty_page(
                operation=operation,
                page=page,
                page_size=page_size,
                filters={"status": status},
                sort_by=sort_by,
                sort_direction=sort_direction,
                sortable_fields=JOB_SORT_FIELDS,
                statuses=JOB_STATUSES,
            )
        try:
            from psycopg import sql

            where_sql = sql.SQL("")
            params: tuple[Any, ...] = ()
            if status:
                where_sql = sql.SQL("where status = %s")
                params = (status,)
            order_clause, resolved_sort_by, resolved_direction = self._order_clause(
                sort_by=sort_by,
                sort_direction=sort_direction,
                allowed_fields=self.JOB_SORT_FIELDS_MAP,
            )
            offset = max(page - 1, 0) * page_size
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("select count(*) from {table_name} {where_sql}").format(
                        table_name=sql.Identifier(table_name),
                        where_sql=where_sql,
                    ),
                    params,
                )
                total = int(cur.fetchone()[0])
                cur.execute(
                    sql.SQL(
                        """
                        select
                            {id_column},
                            status,
                            {target_column},
                            chunk_count,
                            error,
                            updated_at
                        from {table_name}
                        {where_sql}
                        order by {order_clause}
                        limit %s offset %s
                        """
                    ).format(
                        id_column=sql.Identifier(id_column),
                        target_column=sql.Identifier(target_column),
                        table_name=sql.Identifier(table_name),
                        where_sql=where_sql,
                        order_clause=order_clause,
                    ),
                    (*params, page_size, offset),
                )
                records = [
                    {
                        "job_id": row[0],
                        "status": row[1],
                        "target": row[2],
                        "chunk_count": row[3],
                        "error": row[4],
                        "updated_at": row[5].isoformat() if row[5] else None,
                    }
                    for row in cur.fetchall()
                ]
            return AdminQueryResult(
                operation=operation,
                records=records,
                page_info=PageInfo(page=page, page_size=page_size, total=total),
                sort_info=SortInfo(field=resolved_sort_by, direction=resolved_direction),
                filters={"status": status},
                meta=self._meta(
                    sortable_fields=JOB_SORT_FIELDS,
                    statuses=JOB_STATUSES,
                ),
            ).to_dict()
        except Exception:
            return self._empty_page(
                operation=operation,
                page=page,
                page_size=page_size,
                filters={"status": status},
                sort_by=sort_by,
                sort_direction=sort_direction,
                sortable_fields=JOB_SORT_FIELDS,
                statuses=JOB_STATUSES,
            )
        finally:
            conn.close()

    def _empty_page(
        self,
        operation: str,
        page: int,
        page_size: int,
        filters: dict[str, Any] | None = None,
        document_id: str | None = None,
        job_id: str | None = None,
        sort_by: str | None = None,
        sort_direction: str | None = None,
        sortable_fields: list[str] | None = None,
        statuses: list[str] | None = None,
        source_types: list[str] | None = None,
    ) -> dict[str, Any]:
        return AdminQueryResult(
            operation=operation,
            records=[],
            page_info=PageInfo(page=page, page_size=page_size, total=0),
            sort_info=(
                SortInfo(field=sort_by or "updated_at", direction=(sort_direction or "desc").lower())
                if sort_by is not None or sort_direction is not None
                else None
            ),
            document_id=document_id,
            job_id=job_id,
            filters=filters,
            meta=self._meta(
                sortable_fields=sortable_fields,
                statuses=statuses,
                source_types=source_types,
            ),
        ).to_dict()

    def _empty_detail(
        self,
        operation: str,
        document_id: str | None = None,
        job_id: str | None = None,
        sortable_fields: list[str] | None = None,
        statuses: list[str] | None = None,
        source_types: list[str] | None = None,
    ) -> dict[str, Any]:
        return AdminQueryResult(
            operation=operation,
            records=[],
            document_id=document_id,
            job_id=job_id,
            meta=self._meta(
                sortable_fields=sortable_fields,
                statuses=statuses,
                source_types=source_types,
            ),
        ).to_dict()

    def _meta(
        self,
        sortable_fields: list[str] | None = None,
        statuses: list[str] | None = None,
        source_types: list[str] | None = None,
    ) -> AdminQueryMeta:
        return AdminQueryMeta(
            available_operations=ADMIN_OPERATIONS,
            available_statuses=statuses,
            available_source_types=source_types,
            sortable_fields=sortable_fields,
        )

    def _document_filters(
        self,
        status: str | None = None,
        source_type: str | None = None,
        query: str | None = None,
    ):
        from psycopg import sql

        filters: list[str] = []
        params: list[Any] = []
        if status:
            filters.append("status = %s")
            params.append(status)
        if source_type:
            filters.append("source_type = %s")
            params.append(source_type)
        if query:
            filters.append("(title ilike %s or source_uri ilike %s or document_id ilike %s)")
            like = f"%{query}%"
            params.extend([like, like, like])
        if not filters:
            return sql.SQL(""), ()
        return sql.SQL("where " + " and ".join(filters)), tuple(params)

    def _order_clause(
        self,
        sort_by: str,
        sort_direction: str,
        allowed_fields: dict[str, str],
    ):
        from psycopg import sql

        normalized_sort_by = sort_by if sort_by in allowed_fields else next(iter(allowed_fields))
        normalized_direction = "asc" if str(sort_direction).lower() == "asc" else "desc"
        return (
            sql.SQL("{} {}").format(
                sql.Identifier(allowed_fields[normalized_sort_by]),
                sql.SQL(normalized_direction.upper()),
            ),
            normalized_sort_by,
            normalized_direction,
        )

    def _source_storage_payload(
        self,
        *,
        replay_source_uri: Any = None,
        storage_uri: Any = None,
        effective_backend: Any = None,
        bucket: Any = None,
        object_key: Any = None,
        sync_status: Any = None,
    ) -> dict[str, Any]:
        if (
            replay_source_uri is None
            and storage_uri is None
            and effective_backend is None
            and bucket is None
            and object_key is None
            and sync_status is None
        ):
            return {}
        return {
            "replay_source_uri": replay_source_uri,
            "storage_uri": storage_uri,
            "effective_backend": effective_backend,
            "bucket": bucket,
            "object_key": object_key,
            "sync_status": sync_status,
        }
