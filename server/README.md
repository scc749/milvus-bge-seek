# LangGraph RAG Backend

这个目录包含一个基于 `LangGraph + LangChain` 的 RAG 后端原型，目标技术栈为：

架构规范请优先参考：

- `后端架构规范文档.md`

- `DeepSeek`
- `BGE-M3`
- `BGE-Reranker-v2-M3`
- `Milvus`
- `LangGraph Server`

当前代码已经从初始模板扩展为多图结构：

- `assistant_graph`
  - `assistant-ui` 兼容消息态入口
- `rag_query_graph`
  - 查询分析
  - 查询改写
  - 检索
  - 重排
  - 回答生成
- `rag_ingest_graph`
  - 文档加载
  - 文档规范化
  - 分块
  - 入库

## 目录说明

- `src/agent/graph.py`
  - LangGraph 图定义
- `src/agent/nodes/`
  - 图节点
- `src/agent/services/`
  - 应用服务、领域能力服务
  - 其中 `document_parser_service.py` 负责按文件类型选择解析策略
- `src/agent/repositories/`
  - PostgreSQL 写模型、读模型、schema/migration
  - 其中写模型已使用显式事务收口，避免多表写入半成功
- `src/agent/schemas/`
  - 后台查询返回 DTO / 契约 / 共享常量
- `src/agent/components/factories.py`
  - DeepSeek / HuggingFace / Milvus 工厂
- `RAG_项目架构设计文档.md`
  - 架构设计与后续需求说明
- `docker-compose.yml`
  - 本地开发依赖，包含 `PostgreSQL + Milvus + etcd + minio`

## 本地开发准备

### 1. 安装依赖

当前项目的本地联调推荐直接使用现有 Python 3.10 Conda 环境，例如：

```bash
conda run -n mbs python -m pip install -e .
```

如果只需要先跑通前后端兼容联调，也至少需要保证以下依赖已经安装：

```bash
conda run -n mbs python -m pip install fastapi uvicorn pymilvus langchain-milvus
```

说明：

- 由于官方 `langgraph dev` / `langgraph-api` 在当前工程实践里受 Python 版本约束影响较大，本项目前后端联调默认改走 `FastAPI compat API`。
- 如果后续你已经升级到兼容的 Python 3.11+ 环境，仍然可以再切回官方 LangGraph Server 方案。

### 2. 准备环境变量

复制示例配置：

```bash
cp .env.example .env
```

最少需要关注这些变量：

- `DEEPSEEK_API_KEY`
- `MILVUS_URI`
- `MILVUS_COLLECTION`
 - `MILVUS_PRIMARY_FIELD`
 - `MILVUS_TEXT_FIELD`
 - `MILVUS_VECTOR_FIELD`
- `EMBEDDING_MODEL_NAME`
- `RERANKER_MODEL_NAME`

如果你希望源文件也进入受控存储，而不是只依赖原始本地路径，还需要关注：

- `SOURCE_STORAGE_BACKEND`
- `SOURCE_STORAGE_ROOT`
- `SOURCE_STORAGE_BUCKET`
- `SOURCE_STORAGE_PREFIX`
- `SOURCE_STORAGE_MINIO_ENDPOINT`
- `SOURCE_STORAGE_MINIO_ACCESS_KEY`
- `SOURCE_STORAGE_MINIO_SECRET_KEY`

如果你处于国内网络环境，可以直接使用：

```text
HF_ENDPOINT=https://hf-mirror.com
```

### 3. 启动本地基础设施

当前推荐使用 Docker Compose 启动本地开发依赖：

```bash
docker compose up -d
```

默认会启动：

- `postgres`
- `etcd`
- `minio`
- `milvus`

默认端口：

- `PostgreSQL`: `5432`
- `Milvus`: `19530`
- `MinIO API`: `9090`
- `MinIO Console`: `9091`

### 4. 启动兼容 API

当前推荐启动方式：

```bash
conda run -n mbs python -m uvicorn agent.compat_api:app --app-dir src --host 127.0.0.1 --port 2024
```

健康检查：

```bash
curl http://127.0.0.1:2024/health
```

兼容 API 会桥接以下本地图能力：

- `/compat/assistant/threads`
- `/compat/assistant/chat`
- `/compat/assistant/chat/stream`
- `/compat/admin/page-contract`
- `/compat/admin/query`
- `/compat/ingest`
- `/compat/delete`
- `/compat/reindex`

`langgraph.json` 中当前注册了以下图：

- `agent`
- `assistant`
- `rag_query`
- `rag_ingest`
- `rag_delete`
- `rag_reindex`
- `rag_admin`

其中：

- `agent`
- `assistant`

都指向兼容 `assistant-ui` 的消息态图入口。

当前聊天 compat 层补充能力：

- 线程元数据与消息历史已持久化到 PostgreSQL
- 可通过 `/compat/assistant/threads` 获取会话列表
- `/compat/assistant/chat/stream` 会流式返回：
  - 分析阶段事件
  - 检索阶段事件
  - 生成阶段事件
  - 增量答案 chunk
- 每轮最终助手消息会持久化：
  - `citations`
  - `retrieval_hits`
  - `turn_trace`
  这样前端在历史回放时，仍能恢复“问题分析 -> 知识检索 -> 答案生成”的同轮轨迹展示
- 为兼容 `assistant-ui` 的 `useLangGraphRuntime`，流式 `messages` 事件按 LangGraph tuple 结构返回 `[message_chunk, metadata]`，并且同一轮回答的所有 `AIMessageChunk` 必须复用同一个稳定消息 `id`

当前管理台任务型动作补充约束：

- `/compat/ingest`
  - 语义为“提交入库任务”
  - 接口先创建 `ingest_job` 并立即返回 `ingest_job_id`
  - 实际 `load -> normalize -> split -> upsert -> finalize` 流程在后端后台继续执行
- 因此前端点击 URL/文件入库后，应提示“任务已提交”，并引导用户去 `/jobs/ingest` 查看后续状态，而不是把 HTTP 成功误判为“入库已完成”

### 5. 官方 LangGraph Server 说明

如果你的运行环境已经满足官方 CLI / API 的版本要求，也可以继续使用：

```bash
langgraph dev
```

但在当前这套本地联调方案中，`client` 默认通过 Next.js 代理把 `/api/compat/*` 转发到 `http://127.0.0.1:2024`，并不依赖官方 LangGraph Server。

## 当前实现说明

### 查询图

查询图会优先尝试真实 provider：

- 使用 `ChatDeepSeek` 做查询分析与回答生成
- 使用 `HuggingFaceEmbeddings` 加载 `BGE-M3`
- 使用 `langchain-milvus` 检索
- 使用 `HuggingFaceCrossEncoder` 尝试加载 `BGE-Reranker-v2-M3`

如果这些依赖尚未准备好，会自动回退到可离线运行的 fallback 逻辑，方便先调试图编排和状态流。

当前查询侧实际上拆成两层：

- `assistant_graph`
  - 面向 `assistant-ui` / `langgraph-sdk`
  - 输入输出使用 `messages`
- `rag_query_graph`
  - 面向后端内部编排与调试
  - 使用更直接的 `user_query / answer / citations` 状态

这种设计可以同时兼顾：

- 前端线程流式对话协议
- 后端内部 RAG 编排可读性

### 入库图

入库图目前支持：

- URL 文档加载
- 本地文件加载
- 本地目录加载
- URL 递归抓取
  - 站内子页面可递归抓取
  - 每个命中的页面按独立文档入库
  - 额外保留根 URL 与页面路由信息

当前已经按文件类型拆分了解析能力，优先参考 `WeKnora` 的 simple/builtin 思路，落成了适合当前 Python 架构的一版解析服务：

- 简单文本格式
  - `md`
  - `markdown`
  - `txt`
  - `csv`
  - `json`
  - `html`
  - `htm`
- 办公文档格式
  - `pdf`
  - `docx`
  - `pptx`
  - `xlsx`
- 兼容回退格式
  - `doc`
  - `ppt`
  - `xls`
  - 这类旧格式会优先尝试 `UnstructuredFileLoader`，失败时退化为占位文本而不是让整条入库链报错
- 多媒体占位接入
  - 图片：`jpg` `jpeg` `png` `gif` `bmp` `tiff` `webp`
  - 音频：`mp3` `wav` `m4a` `flac` `ogg`
  - 视频：`mp4` `mov` `avi` `mkv` `webm` `wmv` `flv`
  - 当前会保留文件元数据并生成占位文本，为后续 OCR / ASR / VLM 扩展留接口

当前解析策略：

- `simple`
  - 本地直接转文本或 Markdown
  - 适合 `md/txt/csv/json/html`
- `builtin`
  - 走 Python 侧专用解析依赖
  - 适合 `pdf/docx/pptx/xlsx`
- `multimodal_placeholder`
  - 先允许图片/音频/视频进入入库主链
  - 当前不做富多模态提取，只做占位与元数据保留

当前源文件管理策略：

- `source_uri`
  - 保留用户侧可理解的原始来源地址
  - URL 场景下就是原链接
  - 本地文件场景下就是用户提交的原路径
  - 直接上传场景下会生成 `upload://filename` 形式的逻辑来源地址
- `replay_source_uri`
  - 保留系统内部可重放的解析地址
  - 如果启用了源文件备份，本地文件会先复制到 `SOURCE_STORAGE_ROOT`
  - 后续重建索引优先走这个地址，而不是依赖用户原机器路径
- `source_storage`
  - 记录受控存储信息
  - 默认后端是 `local`
  - 如果配置 `SOURCE_STORAGE_BACKEND=minio`，会在保留本地副本的同时把源文件同步到 MinIO
  - 同步成功后会记录 `storage_uri/bucket/object_key`
  - 当前这部分已经从 `document.metadata` 升级为独立主数据表 `document_source_storage`
  - 后台查询、重建索引、删除追踪都优先读取这张表
  - `URL` 来源当前不做网页快照备份，重建时默认重新抓取页面
  - 若启用递归抓取，`ingest_job.source_uri` 保留根 URL；每个页面文档的 `source_uri` 保留真实页面 URL，并在元数据中补充：
    - `crawl_root_uri`
    - `page_url`
    - `page_route`
    - `crawl_mode`
    - `recursive_max_depth`

当前主数据分工：

- `document`
  - 保留文档主记录、原始来源 `source_uri`、状态与当前版本指针
- `document_version`
  - 保留每次入库的版本信息
- `document_source_storage`
  - 保留每个版本对应的源文件受控存储记录
  - 包括：
    - `original_source_uri`
    - `replay_source_uri`
    - `storage_uri`
    - `bucket/object_key`
    - `sync_status`
    - `path_mapping`

并会将切分后的 chunk 尝试写入 `Milvus`。如果 `Milvus` 未连接成功，则保持流程可运行，但不会真正完成向量落库。

如果后续前端要做“上传文件”按钮，当前推荐的接法是两段式：

1. 前端先把文件上传到后端可访问目录或对象存储。
2. 再把落盘后的路径作为 `source_uri` 触发 `rag_ingest`。

这样可以保证上传层与 LangGraph 入库编排层解耦，后续不管换本地存储、MinIO 还是云对象存储，`rag_ingest` 的解析和入库主链都不用重写。

当前 `rag_ingest` 推荐输入：

```json
{
  "source_uri": "E:\\docs\\manual.pdf",
  "backup_source": true
}
```

URL 递归抓取示例：

```json
{
  "source_uri": "https://example.com/docs/",
  "backup_source": true,
  "recursive_url": true,
  "recursive_max_depth": 2,
  "recursive_prevent_outside": true
}
```

如果前端已经拿到了文件二进制，也可以直接传：

```json
{
  "source_name": "manual.pdf",
  "source_mime_type": "application/pdf",
  "source_content_b64": "<base64>",
  "backup_source": true
}
```

默认行为是：

1. 先把源文件转成受控来源记录。
2. 本地文件先复制到受控目录。
3. 如果启用了 MinIO，同步上传到对象存储。
4. 解析时使用可重放地址。
5. PostgreSQL 中保留原始来源地址、可重放地址和存储元数据。

当前入库/删除语义已经收紧为“严格成功”：

- 如果源地址无法加载出任何文档，任务直接标记为 `failed`
- 如果旧 chunk 删除不完整，重建/重入库直接标记为 `failed`
- 如果新 chunk 没有真正写入 `Milvus`，入库任务不会再被标记为 `completed`
- 也就是说，`upserted_count == len(chunks)` 才表示这次向量写入真的成功

当前入库流程还会在首次写入前尝试准备 `Milvus collection`：

- 如果 collection 不存在，则按当前配置自动创建 schema 和向量索引
- 如果 collection 已存在，则尝试 load 后再执行写入
- 当前默认字段名与 `.env` 保持一致：
  - `MILVUS_PRIMARY_FIELD=pk`
  - `MILVUS_TEXT_FIELD=text`
  - `MILVUS_VECTOR_FIELD=vector`
  - `MILVUS_METADATA_FIELD=metadata`
- 当前还显式兼容了 `langchain-milvus + pymilvus` 的连接差异：
  - `MilvusClient` 可直接工作，但 `langchain_milvus.Milvus` 内部仍会走 ORM `Collection`
  - 因此后端会先按同一配置预热 `MilvusClient`，再注册对应 ORM alias，避免出现 `should create connection first` 导致 `upserted_count = 0`

如果 `PostgreSQL` 可用，入库图还会同步写入业务主数据：

- 创建 `ingest_job` 记录
- 注册 `document` 主记录
- 为每次入库创建 `document_version`
- 在写入完成后登记 `chunk_manifest`
- 回写任务、文档、版本的状态和 chunk 数量

当前这部分已经不再只是“最小主数据骨架”，而是具备了第一版可追踪链路：

- `ingest_job`
- `document`
- `document_version`
- `chunk_manifest`

这样至少可以把一次入库过程中的：

- 文档状态管理
- 入库任务追踪
- 文档版本追踪
- 文档与 chunk 映射

串成一条完整主线。当前 `rag_ingest_graph` 的返回结果里也会带上 `registered_version_ids`，方便后续前端或后台继续做追踪与审计。

在文档重复更新场景下，当前入库图还会做一层“旧版本清理”：

- 先根据历史 `document_version` 查询旧版 `chunk_manifest`
- 在写入新 chunk 之前，尝试从 `Milvus` 删除旧版 chunk id
- 新版本写入完成后，把旧版本状态标记为 `superseded`

这样可以减少文档 chunk 数量变化时，`Milvus` 中残留历史 chunk 的问题。

### 删除图与后台读模型

当前还新增了两类后台能力：

- `rag_delete_graph`
  - 创建 `delete_job`
  - 查询文档历史 chunk
  - 从 `Milvus` 删除 chunk
  - 回写文档与删除任务状态
- `PostgresReadRepository`
  - 文档列表查询
  - 文档版本列表查询
  - 入库任务列表查询
  - 删除任务列表查询

这部分主要服务于后续的：

- 文档中心
- 后台管理页
- 运维排查
- 删除/重建任务追踪

当前 `PostgreSQL` 这一层也已经做了工程化拆分：

- `PostgresSchemaManager`
  - 负责 schema / migration
- `PostgresRegistryRepository`
  - 负责写模型与状态推进
  - 关键写入通过显式事务统一 commit / rollback
- `PostgresReadRepository`
  - 负责文档中心 / 任务中心查询
- `IngestApplicationService` / `DeleteApplicationService` / `ReindexApplicationService`
  - 作为上层 use case 编排入口，直接依赖 repository

这样可以减少“一个类同时负责建表、写入、查询、序列化”的耦合问题。

当前 PostgreSQL 层的连接策略也已经区分为：

- 读模型
  - 轻连接
  - 以查询为主
- 写模型
  - 显式事务连接
  - 适用于 `create_ingest_job / register_documents / finalize_ingest_job / create_delete_job / finalize_delete_job`

这样可以尽量保证一次入库/删除状态推进中的多表写入具备原子性。

同时，后台管理约束也开始统一沉淀为共享常量：

- 文档状态枚举
- 版本状态枚举
- 任务状态枚举
- 来源类型枚举
- 文档/版本/任务排序字段白名单

这些常量当前集中在 `src/agent/schemas/admin_constants.py`，后续前端接入时可以直接对齐同一套语义。

### 文档中心契约

当前 `rag_admin_graph` 已经开始面向前端文档中心和任务中心提供稳定返回结构。

支持的 `operation` 包括：

- `list_documents`
- `get_document_detail`
- `list_document_versions`
- `list_ingest_jobs`
- `get_ingest_job_detail`
- `list_delete_jobs`
- `get_delete_job_detail`
- `get_page_contract`

其中列表型查询支持这些输入字段：

- `page`
- `page_size`
- `status_filter`
- `source_type_filter`
- `query`
- `sort_by`
- `sort_direction`

当前已经统一的排序字段白名单：

- 文档列表：
  - `updated_at`
  - `title`
  - `source_type`
  - `status`
  - `current_version_number`
- 文档版本：
  - `version_number`
  - `updated_at`
  - `created_at`
  - `status`
  - `chunk_count`
- 任务列表：
  - `updated_at`
  - `created_at`
  - `status`
  - `chunk_count`

当前返回结构统一为：

```json
{
  "operation": "list_documents",
  "count": 0,
  "records": [],
  "page": 1,
  "page_size": 20,
  "total": 0,
  "sort": {
    "field": "updated_at",
    "direction": "desc"
  },
  "filters": {
    "status": "completed",
    "source_type": "file",
    "query": "rag"
  },
  "meta": {
    "available_operations": [
      "list_documents",
      "get_document_detail",
      "list_document_versions",
      "list_ingest_jobs",
      "get_ingest_job_detail",
      "list_delete_jobs",
      "get_delete_job_detail"
    ],
    "available_statuses": ["processing", "completed", "deleted"],
    "available_source_types": ["url", "file", "directory", "memory", "text"],
    "sortable_fields": ["updated_at", "title", "source_type", "status", "current_version_number"]
  }
}
```

这意味着后续前端做：

- 文档列表
- 文档详情
- 版本历史
- 入库任务页
- 删除任务页

时，不需要再重新设计一套完全不同的返回协议。

详情型查询当前也做了聚合：

- `get_document_detail`
  - 返回文档主记录
  - 返回版本/chunk 状态统计
  - 返回最近版本摘要
- `get_ingest_job_detail`
  - 返回任务主记录
  - 返回关联文档摘要
- `get_delete_job_detail`
  - 返回删除任务主记录
  - 返回归档 chunk 数量摘要

### 页面级后端契约

当前还新增了“页面级 contract”能力，专门给未来 `client` 的管理页面使用。

支持的 `page_name` 包括：

- `document_list`
- `document_detail`
- `ingest_job`
- `delete_job`

通过 `rag_admin_graph` 调用：

```json
{
  "operation": "get_page_contract",
  "page_name": "document_list"
}
```

可返回该页面对应的：

- 主查询 operation
- 关联 secondary operations
- 过滤项定义
- 排序项定义
- 页面 sections 定义
- 默认分页大小

这样后续前端做页面时，可以明确知道：

- 文档列表页该调什么
- 文档详情页除了详情还要调什么
- 入库任务页和删除任务页有哪些结构区块

当前 admin 层也已经改成“显式契约失败”：

- 未知 `operation` 不再偷偷回退到 `list_documents`
- 未知 `page_name` 不再偷偷回退到 `document_list`
- 后端会返回显式 `error` 和 `available_operations/available_pages`

这样前后端联调时，如果参数写错，能第一时间暴露契约问题，而不是收到一个看似成功但其实是别的页面数据的响应。
- 哪些筛选和排序是官方支持的

### 前后端接口边界

当前前端模板 `client` 基于 `assistant-ui + langgraph-sdk`，核心依赖的是：

- `LANGGRAPH_API_URL`
- `assistant_id` / `graph_id`
- `threads` / `runs.stream(...)`

因此当前推荐的前后端接口边界是：

- 对话主入口使用：
  - `agent`
  - 或 `assistant`
- 文档入库、删除、重建使用独立图：
  - `rag_ingest`
  - `rag_delete`
  - `rag_reindex`
- 后台文档中心、任务中心使用 `rag_admin`

这样可以保证：

- 聊天线程接口不被后台管理逻辑污染
- 前端后续扩展文档中心时，不必强行复用聊天消息协议
- 后端仍保持 `LangGraph Server` 作为统一运行入口

## 当前阶段定位

这不是最终的生产实现，而是“第一阶段真实接入骨架”：

- 已具备完整图编排
- 已具备模型和向量库接入位
- 已具备本地基础设施方案
- 已开始具备关系型数据库主数据落点
- 尚未完成生产级的索引初始化、完整关系库建模、完整评测与后台能力

如需完整设计背景，请优先阅读 [RAG_项目架构设计文档.md](./RAG_%E9%A1%B9%E7%9B%AE%E6%9E%B6%E6%9E%84%E8%AE%BE%E8%AE%A1%E6%96%87%E6%A1%A3.md)。
