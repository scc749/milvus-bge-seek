"""Page-level contracts for document center and task center UI."""

from __future__ import annotations

from agent.schemas.admin_constants import (
    ADMIN_PAGE_NAMES,
    DOCUMENT_SORT_FIELDS,
    DOCUMENT_STATUSES,
    JOB_SORT_FIELDS,
    JOB_STATUSES,
    SOURCE_TYPES,
    VERSION_SORT_FIELDS,
    VERSION_STATUSES,
)
from agent.schemas.page_contracts import (
    ExampleContract,
    FieldContract,
    FilterContract,
    PageContract,
    ParamContract,
    QueryContract,
    SectionContract,
    StatCardContract,
    SortContract,
    TabContract,
    TableContract,
)


class AdminPageContractService:
    """Provide stable backend contracts for future frontend pages."""

    def get_page_contract(self, page_name: str) -> dict:
        """Return a page-level contract definition."""

        contracts = {
            "document_list": self._document_list_contract(),
            "document_detail": self._document_detail_contract(),
            "ingest_job": self._ingest_job_contract(),
            "delete_job": self._delete_job_contract(),
        }
        if page_name not in contracts:
            return {
                "result": {
                    "operation": "get_page_contract",
                    "page_name": page_name,
                    "error": f"Unsupported page contract: {page_name}",
                    "available_pages": ADMIN_PAGE_NAMES,
                }
            }
        contract = contracts[page_name]
        return {
            "result": {
                "operation": "get_page_contract",
                "page_contract": contract.to_dict(),
            }
        }

    def _document_list_contract(self) -> PageContract:
        return PageContract(
            page_name="document_list",
            title="文档列表页",
            primary_operation="list_documents",
            secondary_operations=[],
            primary_query=QueryContract(
                name="document_list_query",
                operation="list_documents",
                description="获取文档列表页的卡片/表格数据",
                params=[
                    ParamContract("page", "页码", True, "int"),
                    ParamContract("page_size", "分页大小", True, "int"),
                    ParamContract("status_filter", "文档状态", False, "enum"),
                    ParamContract("source_type_filter", "来源类型", False, "enum"),
                    ParamContract("query", "关键词", False, "text"),
                    ParamContract("sort_by", "排序字段", False, "enum"),
                    ParamContract("sort_direction", "排序方向", False, "enum"),
                ],
            ),
            filters=[
                FilterContract("status_filter", "文档状态", "enum", DOCUMENT_STATUSES),
                FilterContract("source_type_filter", "来源类型", "enum", SOURCE_TYPES),
                FilterContract("query", "关键词", "text"),
            ],
            sorts=[SortContract(field, self._label_for_sort(field)) for field in DOCUMENT_SORT_FIELDS],
            list_item_fields=[
                FieldContract("title", "标题", "records[].title", emphasized=True),
                FieldContract("document_id", "文档 ID", "records[].document_id"),
                FieldContract("status", "状态", "records[].status", value_type="badge"),
                FieldContract("source_type", "来源类型", "records[].source_type", value_type="badge"),
                FieldContract("current_version_number", "当前版本", "records[].current_version_number"),
                FieldContract("current_chunk_count", "当前 Chunk 数", "records[].current_chunk_count"),
                FieldContract("updated_at", "更新时间", "records[].updated_at", value_type="datetime"),
            ],
            tables=[
                TableContract(
                    key="document_table",
                    label="文档表格",
                    source_operation="list_documents",
                    columns=[
                        FieldContract("document_id", "文档 ID", "records[].document_id"),
                        FieldContract("title", "标题", "records[].title"),
                        FieldContract("status", "状态", "records[].status", value_type="badge"),
                        FieldContract("source_type", "来源类型", "records[].source_type", value_type="badge"),
                        FieldContract("source_uri", "来源地址", "records[].source_uri"),
                        FieldContract(
                            "source_storage_uri",
                            "备份地址",
                            "records[].source_storage.storage_uri",
                        ),
                        FieldContract("current_version_number", "版本号", "records[].current_version_number"),
                        FieldContract("current_chunk_count", "Chunk 数", "records[].current_chunk_count"),
                        FieldContract("updated_at", "更新时间", "records[].updated_at", value_type="datetime"),
                    ],
                )
            ],
            sections=[
                SectionContract(key="list", label="文档列表", kind="table"),
            ],
            examples=[
                ExampleContract(
                    label="按文件来源和完成状态筛选文档",
                    request={
                        "operation": "list_documents",
                        "page": 1,
                        "page_size": 20,
                        "status_filter": "completed",
                        "source_type_filter": "file",
                        "sort_by": "updated_at",
                        "sort_direction": "desc",
                    },
                    response_preview={
                        "operation": "list_documents",
                        "records": [{"document_id": "doc-123", "title": "RAG 设计说明"}],
                        "page": 1,
                        "page_size": 20,
                        "total": 1,
                    },
                )
            ],
        )

    def _document_detail_contract(self) -> PageContract:
        return PageContract(
            page_name="document_detail",
            title="文档详情页",
            primary_operation="get_document_detail",
            secondary_operations=["list_document_versions"],
            primary_query=QueryContract(
                name="document_detail_query",
                operation="get_document_detail",
                description="获取文档详情页主记录、统计和最近版本摘要",
                params=[
                    ParamContract("document_id", "文档 ID", True, "text"),
                ],
            ),
            secondary_queries=[
                QueryContract(
                    name="document_versions_query",
                    operation="list_document_versions",
                    description="获取版本历史表格",
                    params=[
                        ParamContract("document_id", "文档 ID", True, "text"),
                        ParamContract("page", "页码", True, "int"),
                        ParamContract("page_size", "分页大小", True, "int"),
                        ParamContract("status_filter", "版本状态", False, "enum"),
                        ParamContract("sort_by", "排序字段", False, "enum"),
                        ParamContract("sort_direction", "排序方向", False, "enum"),
                    ],
                )
            ],
            filters=[
                FilterContract("status_filter", "版本状态", "enum", VERSION_STATUSES),
            ],
            sorts=[SortContract(field, self._label_for_sort(field)) for field in VERSION_SORT_FIELDS],
            stat_cards=[
                StatCardContract("version_total", "版本总数", "records[0].stats.version_total"),
                StatCardContract("active_chunk_total", "活跃 Chunk 数", "records[0].stats.active_chunk_total"),
                StatCardContract("superseded_chunk_total", "已替换 Chunk 数", "records[0].stats.superseded_chunk_total"),
                StatCardContract("deleted_chunk_total", "已删除 Chunk 数", "records[0].stats.deleted_chunk_total", tone="warning"),
            ],
            sections=[
                SectionContract(
                    "summary",
                    "文档摘要",
                    fields=[
                        FieldContract("title", "标题", "records[0].title", emphasized=True),
                        FieldContract("document_id", "文档 ID", "records[0].document_id"),
                        FieldContract("status", "状态", "records[0].status", value_type="badge"),
                        FieldContract("source_type", "来源类型", "records[0].source_type", value_type="badge"),
                        FieldContract("source_uri", "来源地址", "records[0].source_uri"),
                        FieldContract("replay_source_uri", "可重放地址", "records[0].replay_source_uri"),
                        FieldContract("source_storage_uri", "备份地址", "records[0].source_storage.storage_uri"),
                        FieldContract("updated_at", "更新时间", "records[0].updated_at", value_type="datetime"),
                    ],
                ),
                SectionContract("stats", "统计信息", kind="stats", stat_cards=[
                    StatCardContract("version_total", "版本总数", "records[0].stats.version_total"),
                    StatCardContract("completed_versions", "完成版本", "records[0].stats.completed_versions"),
                    StatCardContract("active_chunk_total", "活跃 Chunk", "records[0].stats.active_chunk_total"),
                    StatCardContract("superseded_versions", "已替换版本", "records[0].stats.superseded_versions", tone="muted"),
                ]),
                SectionContract(
                    "recent_versions",
                    "最近版本",
                    kind="table",
                    tables=[
                        TableContract(
                            key="recent_versions_table",
                            label="最近版本",
                            source_operation="get_document_detail",
                            columns=[
                                FieldContract("version_number", "版本号", "records[0].recent_versions[].version_number"),
                                FieldContract("status", "状态", "records[0].recent_versions[].status", value_type="badge"),
                                FieldContract("chunk_count", "Chunk 数", "records[0].recent_versions[].chunk_count"),
                                FieldContract("updated_at", "更新时间", "records[0].recent_versions[].updated_at", value_type="datetime"),
                            ],
                        )
                    ],
                ),
                SectionContract(
                    "versions_table",
                    "版本历史",
                    kind="table",
                    tables=[
                        TableContract(
                            key="document_versions_table",
                            label="版本历史表",
                            source_operation="list_document_versions",
                            columns=[
                                FieldContract("version_number", "版本号", "records[].version_number"),
                                FieldContract("status", "状态", "records[].status", value_type="badge"),
                                FieldContract("content_hash", "内容哈希", "records[].content_hash"),
                                FieldContract("chunk_count", "Chunk 数", "records[].chunk_count"),
                                FieldContract("updated_at", "更新时间", "records[].updated_at", value_type="datetime"),
                            ],
                        )
                    ],
                ),
            ],
            tabs=[
                TabContract("overview", "概览", ["summary", "stats"]),
                TabContract("versions", "版本历史", ["recent_versions", "versions_table"]),
            ],
            examples=[
                ExampleContract(
                    label="获取文档详情页主数据",
                    request={"operation": "get_document_detail", "document_id": "doc-123"},
                    response_preview={
                        "operation": "get_document_detail",
                        "records": [{"document_id": "doc-123", "stats": {"version_total": 3}}],
                    },
                ),
                ExampleContract(
                    label="获取文档版本历史",
                    request={
                        "operation": "list_document_versions",
                        "document_id": "doc-123",
                        "page": 1,
                        "page_size": 20,
                        "sort_by": "version_number",
                        "sort_direction": "desc",
                    },
                    response_preview={
                        "operation": "list_document_versions",
                        "records": [{"version_number": 3, "status": "completed"}],
                        "page": 1,
                        "page_size": 20,
                    },
                ),
            ],
        )

    def _ingest_job_contract(self) -> PageContract:
        return PageContract(
            page_name="ingest_job",
            title="入库任务页",
            primary_operation="list_ingest_jobs",
            secondary_operations=["get_ingest_job_detail"],
            primary_query=QueryContract(
                name="ingest_job_list_query",
                operation="list_ingest_jobs",
                description="获取入库任务列表",
                params=[
                    ParamContract("page", "页码", True, "int"),
                    ParamContract("page_size", "分页大小", True, "int"),
                    ParamContract("status_filter", "任务状态", False, "enum"),
                    ParamContract("sort_by", "排序字段", False, "enum"),
                    ParamContract("sort_direction", "排序方向", False, "enum"),
                ],
            ),
            secondary_queries=[
                QueryContract(
                    name="ingest_job_detail_query",
                    operation="get_ingest_job_detail",
                    description="获取入库任务详情与关联统计",
                    params=[
                        ParamContract("job_id", "任务 ID", True, "text"),
                    ],
                )
            ],
            filters=[
                FilterContract("status_filter", "任务状态", "enum", JOB_STATUSES),
            ],
            sorts=[SortContract(field, self._label_for_sort(field)) for field in JOB_SORT_FIELDS],
            stat_cards=[
                StatCardContract("document_total", "文档总数", "records[0].stats.document_total"),
                StatCardContract("chunk_total", "Chunk 总数", "records[0].stats.chunk_total"),
                StatCardContract("upserted_total", "实际入库 Chunk", "records[0].stats.upserted_total"),
                StatCardContract("version_total", "版本总数", "records[0].stats.version_total"),
            ],
            list_item_fields=[
                FieldContract("job_id", "任务 ID", "records[].job_id"),
                FieldContract("status", "状态", "records[].status", value_type="badge"),
                FieldContract("target", "目标", "records[].target"),
                FieldContract("chunk_count", "Chunk 数", "records[].chunk_count"),
                FieldContract("updated_at", "更新时间", "records[].updated_at", value_type="datetime"),
            ],
            tables=[
                TableContract(
                    key="ingest_job_table",
                    label="入库任务表格",
                    source_operation="list_ingest_jobs",
                    columns=[
                        FieldContract("job_id", "任务 ID", "records[].job_id"),
                        FieldContract("status", "状态", "records[].status", value_type="badge"),
                        FieldContract("target", "来源地址", "records[].target"),
                        FieldContract("chunk_count", "Chunk 数", "records[].chunk_count"),
                        FieldContract("updated_at", "更新时间", "records[].updated_at", value_type="datetime"),
                    ],
                )
            ],
            sections=[
                SectionContract(
                    "summary",
                    "任务摘要",
                    fields=[
                        FieldContract("job_id", "任务 ID", "records[0].job_id", emphasized=True),
                        FieldContract("status", "状态", "records[0].status", value_type="badge"),
                        FieldContract("source_uri", "来源地址", "records[0].source_uri"),
                        FieldContract("created_at", "创建时间", "records[0].created_at", value_type="datetime"),
                        FieldContract("updated_at", "更新时间", "records[0].updated_at", value_type="datetime"),
                        FieldContract("error", "错误信息", "records[0].error"),
                    ],
                ),
                SectionContract(
                    "stats",
                    "任务统计",
                    kind="stats",
                    stat_cards=[
                        StatCardContract("document_total", "文档总数", "records[0].stats.document_total"),
                        StatCardContract("chunk_total", "Chunk 总数", "records[0].stats.chunk_total"),
                        StatCardContract("upserted_total", "入库 Chunk", "records[0].stats.upserted_total"),
                        StatCardContract("active_chunk_total", "活跃 Chunk", "records[0].stats.active_chunk_total"),
                    ],
                ),
                SectionContract(
                    "documents",
                    "关联文档",
                    kind="table",
                    tables=[
                        TableContract(
                            key="ingest_job_documents_table",
                            label="关联文档",
                            source_operation="get_ingest_job_detail",
                            columns=[
                                FieldContract("document_id", "文档 ID", "records[0].documents[].document_id"),
                                FieldContract("title", "标题", "records[0].documents[].title"),
                                FieldContract("status", "状态", "records[0].documents[].status", value_type="badge"),
                                FieldContract("current_version_number", "版本号", "records[0].documents[].current_version_number"),
                                FieldContract("current_chunk_count", "Chunk 数", "records[0].documents[].current_chunk_count"),
                            ],
                        )
                    ],
                ),
                SectionContract(
                    "versions",
                    "版本统计",
                    kind="stats",
                    stat_cards=[
                        StatCardContract("version_total", "版本总数", "records[0].stats.version_total"),
                        StatCardContract("completed_versions", "完成版本", "records[0].stats.completed_versions"),
                        StatCardContract("superseded_versions", "已替换版本", "records[0].stats.superseded_versions", tone="muted"),
                        StatCardContract("deleted_versions", "已删除版本", "records[0].stats.deleted_versions", tone="warning"),
                    ],
                ),
            ],
            tabs=[
                TabContract("overview", "概览", ["summary", "stats"]),
                TabContract("documents", "关联文档", ["documents", "versions"]),
            ],
            examples=[
                ExampleContract(
                    label="获取入库任务列表",
                    request={
                        "operation": "list_ingest_jobs",
                        "page": 1,
                        "page_size": 20,
                        "status_filter": "completed",
                        "sort_by": "updated_at",
                        "sort_direction": "desc",
                    },
                    response_preview={
                        "operation": "list_ingest_jobs",
                        "records": [{"job_id": "ing_xxx", "status": "completed"}],
                        "page": 1,
                        "page_size": 20,
                    },
                ),
                ExampleContract(
                    label="获取入库任务详情",
                    request={"operation": "get_ingest_job_detail", "job_id": "ing_xxx"},
                    response_preview={
                        "operation": "get_ingest_job_detail",
                        "records": [{"job_id": "ing_xxx", "stats": {"document_total": 2}}],
                    },
                ),
            ],
        )

    def _delete_job_contract(self) -> PageContract:
        return PageContract(
            page_name="delete_job",
            title="删除任务页",
            primary_operation="list_delete_jobs",
            secondary_operations=["get_delete_job_detail"],
            primary_query=QueryContract(
                name="delete_job_list_query",
                operation="list_delete_jobs",
                description="获取删除任务列表",
                params=[
                    ParamContract("page", "页码", True, "int"),
                    ParamContract("page_size", "分页大小", True, "int"),
                    ParamContract("status_filter", "任务状态", False, "enum"),
                    ParamContract("sort_by", "排序字段", False, "enum"),
                    ParamContract("sort_direction", "排序方向", False, "enum"),
                ],
            ),
            secondary_queries=[
                QueryContract(
                    name="delete_job_detail_query",
                    operation="get_delete_job_detail",
                    description="获取删除任务详情与归档统计",
                    params=[
                        ParamContract("job_id", "任务 ID", True, "text"),
                    ],
                )
            ],
            filters=[
                FilterContract("status_filter", "任务状态", "enum", JOB_STATUSES),
            ],
            sorts=[SortContract(field, self._label_for_sort(field)) for field in JOB_SORT_FIELDS],
            stat_cards=[
                StatCardContract("archived_manifest_total", "归档 Manifest 数", "records[0].stats.archived_manifest_total"),
                StatCardContract("deleted_chunk_total", "已删除 Chunk", "records[0].stats.deleted_chunk_total", tone="warning"),
                StatCardContract("superseded_chunk_total", "已替换 Chunk", "records[0].stats.superseded_chunk_total", tone="muted"),
            ],
            list_item_fields=[
                FieldContract("job_id", "任务 ID", "records[].job_id"),
                FieldContract("status", "状态", "records[].status", value_type="badge"),
                FieldContract("target", "目标文档", "records[].target"),
                FieldContract("chunk_count", "Chunk 数", "records[].chunk_count"),
                FieldContract("updated_at", "更新时间", "records[].updated_at", value_type="datetime"),
            ],
            tables=[
                TableContract(
                    key="delete_job_table",
                    label="删除任务表格",
                    source_operation="list_delete_jobs",
                    columns=[
                        FieldContract("job_id", "任务 ID", "records[].job_id"),
                        FieldContract("status", "状态", "records[].status", value_type="badge"),
                        FieldContract("target", "目标文档", "records[].target"),
                        FieldContract("chunk_count", "Chunk 数", "records[].chunk_count"),
                        FieldContract("updated_at", "更新时间", "records[].updated_at", value_type="datetime"),
                    ],
                )
            ],
            sections=[
                SectionContract(
                    "summary",
                    "任务摘要",
                    fields=[
                        FieldContract("job_id", "任务 ID", "records[0].job_id", emphasized=True),
                        FieldContract("document_id", "文档 ID", "records[0].document_id"),
                        FieldContract("status", "状态", "records[0].status", value_type="badge"),
                        FieldContract("reason", "删除原因", "records[0].reason"),
                        FieldContract("created_at", "创建时间", "records[0].created_at", value_type="datetime"),
                        FieldContract("updated_at", "更新时间", "records[0].updated_at", value_type="datetime"),
                    ],
                ),
                SectionContract(
                    "stats",
                    "归档统计",
                    kind="stats",
                    stat_cards=[
                        StatCardContract("archived_manifest_total", "归档 Manifest", "records[0].stats.archived_manifest_total"),
                        StatCardContract("active_chunk_total", "活跃 Chunk", "records[0].stats.active_chunk_total"),
                        StatCardContract("superseded_chunk_total", "已替换 Chunk", "records[0].stats.superseded_chunk_total", tone="muted"),
                        StatCardContract("deleted_chunk_total", "已删除 Chunk", "records[0].stats.deleted_chunk_total", tone="warning"),
                    ],
                ),
                SectionContract(
                    "document",
                    "关联文档",
                    fields=[
                        FieldContract("title", "标题", "records[0].document.title", emphasized=True),
                        FieldContract("source_uri", "来源地址", "records[0].document.source_uri"),
                        FieldContract("replay_source_uri", "可重放地址", "records[0].document.replay_source_uri"),
                        FieldContract("source_storage_uri", "备份地址", "records[0].document.source_storage.storage_uri"),
                        FieldContract("source_type", "来源类型", "records[0].document.source_type", value_type="badge"),
                        FieldContract("status", "文档状态", "records[0].document.status", value_type="badge"),
                    ],
                ),
            ],
            tabs=[
                TabContract("overview", "概览", ["summary", "stats"]),
                TabContract("document", "关联文档", ["document"]),
            ],
            examples=[
                ExampleContract(
                    label="获取删除任务列表",
                    request={
                        "operation": "list_delete_jobs",
                        "page": 1,
                        "page_size": 20,
                        "status_filter": "completed",
                        "sort_by": "updated_at",
                        "sort_direction": "desc",
                    },
                    response_preview={
                        "operation": "list_delete_jobs",
                        "records": [{"job_id": "del_xxx", "status": "completed"}],
                        "page": 1,
                        "page_size": 20,
                    },
                ),
                ExampleContract(
                    label="获取删除任务详情",
                    request={"operation": "get_delete_job_detail", "job_id": "del_xxx"},
                    response_preview={
                        "operation": "get_delete_job_detail",
                        "records": [{"job_id": "del_xxx", "stats": {"deleted_chunk_total": 12}}],
                    },
                ),
            ],
        )

    def _label_for_sort(self, field: str) -> str:
        labels = {
            "updated_at": "更新时间",
            "created_at": "创建时间",
            "title": "标题",
            "source_type": "来源类型",
            "status": "状态",
            "current_version_number": "当前版本号",
            "version_number": "版本号",
            "chunk_count": "Chunk 数",
        }
        return labels.get(field, field)
