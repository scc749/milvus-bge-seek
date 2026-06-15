# 基于 LangGraph 的 RAG 项目架构设计文档

补充说明：

- 运行与分层落地规范请结合 `后端架构规范文档.md` 一起阅读。

## 1. 文档目标

本文档基于以下材料进行重新设计：

- 根目录中的 `README.md`
- `rag_from_scratch_1_to_4.ipynb`
- `rag_from_scratch_5_to_9.ipynb`
- `rag_from_scratch_10_and_11.ipynb`
- `rag_from_scratch_12_to_14.ipynb`
- `rag_from_scratch_15_to_18.ipynb`
- `RAG_FROM_SCRATCH_说明文档.md`
- 当前后端模板目录 `server`

目标不是照搬 notebook 中的旧版调用方式，而是：

1. 结合这些 notebook 提炼出的设计思想。
2. 基于当前 `LangGraph CLI + LangGraph Server` 模板。
3. 使用**当前 LangChain / LangGraph 生态中推荐的封装方式**重新规划一套可落地、可扩展、风格统一的 RAG 后端架构。
4. 技术栈统一为：
   - `LangGraph`
   - `LangChain`
   - `DeepSeek`
   - `BGE-M3`
   - `BGE-Reranker-v2-M3`
   - `Milvus`

当前阶段只设计后端，不改前端。前端 `assistant-ui` 仅作为未来对接对象，在本设计中只考虑接口兼容性，不展开实现。

---

## 2. 设计原则

### 2.1 全局统一使用 LangChain / LangGraph 风格

本项目必须遵循以下约束：

- 聊天模型统一通过 LangChain Chat Model 封装访问，不直接在业务代码中调用厂商原生 SDK。
- 向量模型统一通过 LangChain Embeddings 封装访问。
- 向量库统一通过 LangChain VectorStore / Retriever 封装访问。
- 工作流编排统一由 LangGraph 负责，不在业务层手写松散的 if/else 流程。
- Prompt、检索器、重排器、压缩器、结构化输出全部优先使用 LangChain 标准抽象。

也就是说，本项目的主风格不是“模型 SDK 驱动”，而是“LangChain 抽象驱动 + LangGraph 编排驱动”。

### 2.2 新项目不要沿用 notebook 里的旧写法

notebook 里的代码主要用于教学，存在几个问题：

- 很多示例使用的是较早期的 `langchain_community` 风格写法。
- 许多代码写在 notebook 单元里，不适合后端服务化组织。
- 一些调用是一次性实验写法，不适合工程抽象。
- 部分示例只验证概念，不适合直接进入生产代码。

因此本项目应遵循：

- 包拆分尽量使用独立 provider 包。
- LCEL 和 LangGraph 只在合适层次使用，不把所有逻辑塞进一个文件。
- 明确区分：
  - 图编排层
  - 领域服务层
  - 基础设施层
  - 配置层
  - 数据模型层

### 2.3 先稳定后增强

虽然 `BGE-M3` 支持更复杂的多功能能力，`Milvus` 也支持更高级的 hybrid retrieval，但为了保证项目第一版稳定，架构采用两阶段策略：

1. 第一阶段优先建设一条稳定、统一、可测试的 `Dense Retrieval + Re-rank + Generation` 主链路。
2. 第二阶段再逐步增强：
   - Multi-query
   - Decomposition
   - Metadata filter
   - Hybrid retrieval
   - Query routing
   - 自适应检索策略

---

## 3. 现有后端模板分析

当前 `server` 目录已经从标准的 LangGraph CLI 模板，推进到了“第一阶段可运行 RAG 骨架”状态，核心结构如下：

```text
server/
  .env.example
  docker-compose.yml
  RAG_项目架构设计文档.md
  README.md
  langgraph.json
  pyproject.toml
  src/agent/__init__.py
  src/agent/components/factories.py
  src/agent/context.py
  src/agent/config.py
  src/agent/dependencies.py
  src/agent/graph.py
  src/agent/nodes/assistant_flow.py
  src/agent/nodes/admin_flow.py
  src/agent/nodes/delete_flow.py
  src/agent/nodes/ingest_flow.py
  src/agent/nodes/query_flow.py
  src/agent/nodes/reindex_flow.py
  src/agent/prompts.py
  src/agent/repositories/postgres_base.py
  src/agent/repositories/postgres_schema_manager.py
  src/agent/repositories/postgres_registry_repository.py
  src/agent/repositories/postgres_read_repository.py
  src/agent/schemas/admin_contracts.py
  src/agent/services/admin_application_service.py
  src/agent/services/answer_service.py
  src/agent/services/conversation_service.py
  src/agent/services/delete_application_service.py
  src/agent/services/document_source_service.py
  src/agent/services/ingest_application_service.py
  src/agent/services/ingestion_service.py
  src/agent/services/postgres_read_model_service.py
  src/agent/services/retrieval_service.py
  src/agent/services/reindex_application_service.py
  src/agent/services/rerank_service.py
  src/agent/state.py
  src/agent/utils/documents.py
  tests/
```

现状特点：

- `langgraph.json` 中已注册 7 个入口：
  - `agent -> ./src/agent/graph.py:graph`
  - `assistant -> ./src/agent/graph.py:assistant_graph`
  - `rag_query -> ./src/agent/graph.py:rag_query_graph`
  - `rag_ingest -> ./src/agent/graph.py:rag_ingest_graph`
- `rag_delete -> ./src/agent/graph.py:rag_delete_graph`
- `rag_reindex -> ./src/agent/graph.py:rag_reindex_graph`
- `rag_admin -> ./src/agent/graph.py:rag_admin_graph`
- `graph.py` 已不再是单节点占位图，而是多图结构：
  - `assistant-ui` 兼容图 `assistant_graph`
  - 问答图 `rag_query_graph`
  - 入库图 `rag_ingest_graph`
  - 删除图 `rag_delete_graph`
  - 重建图 `rag_reindex_graph`
  - 后台查询图 `rag_admin_graph`
- `pyproject.toml` 已补入第一阶段所需的主要依赖方向：
  - `langchain`
  - `langchain-deepseek`
  - `langchain-huggingface`
  - `langchain-milvus`
  - `langchain-text-splitters`
  - `pymilvus`
  - `sentence-transformers`
- 已具备以下代码骨架能力：
  - `assistant-ui` 兼容消息态问答入口
  - 查询分析
  - 查询改写
  - 向量检索
  - 重排
  - 生成
  - 文档切分
  - 文档入库
  - 文档删除
  - 文档重建
  - 后台读模型查询
  - 环境变量配置
  - Prompt/LCEL 统一封装
  - 本地基础设施 docker compose
- 当前实现采用“真实 provider 优先，fallback 兜底”的策略：
  - 配置了真实依赖就走 `DeepSeek / BGE / Milvus`
  - 未配置时仍可离线运行最小链路
- 当前工程结构也开始从“图节点直接编排一切”收敛到“节点 + 应用服务 + 基础能力服务”分层：
  - `ConversationService`
  - `IngestApplicationService`
  - `DeleteApplicationService`
  - `ReindexApplicationService`
  - `DocumentSourceService`
  - `AdminApplicationService`
- `PostgreSQL` 相关能力也已经从“大一统 service”拆为：
  - `PostgresSchemaManager`
  - `PostgresRegistryRepository`
  - `PostgresReadRepository`
  - 应用服务直接依赖 repository，不再经过薄 service 透传
- `rag_admin_graph` 的输出也开始固定为前端可直接消费的 contract：
  - `records`
  - `page / page_size / total`
  - `sort`
  - `filters`
  - `meta`
- 后台约束也开始统一沉淀为共享常量：
  - 文档状态枚举
  - 版本状态枚举
  - 任务状态枚举
  - 来源类型枚举
  - 排序字段白名单

结论：当前后端已经完成了从模板到第一阶段骨架的升级，并开始进入“面向前后端协同的半工程化实现”阶段，但仍然距离完整生产级 RAG 服务有差距，主要还缺索引初始化、真实数据源接入、关系库主数据深化、评测和完整测试闭环。

补充聊天链路现状：

- `compat assistant` 已提供流式聊天端点 `/compat/assistant/chat/stream`
- 流式事件会显式输出：
  - 问题分析阶段
  - 知识检索阶段
  - 答案生成阶段
- 最终助手消息会附带：
  - reasoning 摘要
  - citations
  - retrieval_hits
  - turn_trace
- `turn_trace` 的定位不是页面顶部全局面板数据，而是“当前提问对应的单轮轨迹”，前端必须将其渲染在该轮消息内部，确保历史回放与实时流式体验一致
- 线程历史不再只保存在内存，已落到 PostgreSQL：
  - `assistant_thread`
  - `assistant_message`

---

## 4. 技术栈与库职责划分

本项目的关键不是“用了哪些库”，而是“这些库分别负责哪一层”。

## 4.1 LangGraph

职责：

- 定义工作流图。
- 管理状态流转。
- 实现条件分支、重试、人工介入和持久化扩展能力。
- 对外通过 LangGraph Server 暴露可调用图接口。

适用位置：

- 问答主图
- 文档入库图
- 未来的纠错图、评测图、后台维护图

不负责：

- 具体模型推理实现
- 向量库存储细节
- 文件加载器实现细节

## 4.2 LangChain

职责：

- 提供统一抽象：
  - `ChatModel`
  - `Embeddings`
  - `VectorStore`
  - `Retriever`
  - `DocumentCompressor`
  - `PromptTemplate`
  - `Structured Output`
- 提供与各 provider 的集成封装。

适用位置：

- DeepSeek 模型接入
- HuggingFace/BGE embedding 接入
- Milvus 接入
- Re-ranker 接入
- 文档 loader / splitter / retriever / compression

## 4.3 DeepSeek

职责：

- 生成回答
- 查询分析
- 结构化输出
- 查询改写
- 问题拆解
- 回答综合

接入方式：

- 使用 LangChain 的 `langchain-deepseek` 包。
- 统一通过 `ChatDeepSeek` 封装接入。

不建议：

- 在业务代码里直接混用 DeepSeek 官方 Python SDK。

## 4.4 BGE-M3

职责：

- 主 embedding 模型。
- 第一阶段作为**统一 dense embedding 模型**使用。

说明：

- `BGE-M3` 本身支持多功能检索能力，但在 LangChain 统一风格下，第一阶段优先使用其标准 embedding 能力。
- 对于更复杂的 sparse / hybrid 能力，建议作为第二阶段增强项处理，而不是在第一版就把底层逻辑打散。

接入方式：

- 统一通过 `langchain-huggingface` 提供的 embeddings 封装接入。
- 不在上层业务直接操作 `sentence-transformers` 原始对象。

## 4.5 BGE-Reranker-v2-M3

职责：

- 对初筛后的候选文档做重排。
- 提升最终送入 LLM 的上下文质量。

接入方式：

- 优先使用 LangChain 的 cross-encoder / reranker 抽象。
- 通过 `ContextualCompressionRetriever` 或独立 rerank service 封装。

设计原则：

- 上层只知道“这是一个 reranker”。
- 不让图层直接感知底层 HuggingFace 或其他模型调用细节。

## 4.6 Milvus

职责：

- 文档向量存储。
- 相似度检索。
- metadata 过滤。
- 后续 hybrid retrieval 扩展。

接入方式：

- 统一使用 `langchain-milvus` 的 `Milvus` 向量存储封装。
- 必要时在基础设施层少量引入 `pymilvus` 做运维或高级索引配置，但不让业务层依赖它。

设计原则：

- 业务代码调用 `Retriever`。
- 基础设施层管理 collection、index、search params。
- 不在节点函数里散落 Milvus 细节。

## 4.7 关系型数据库

职责：

- 存储业务主数据。
- 管理文档生命周期和状态流转。
- 记录入库任务、删除任务、重建任务。
- 管理知识库、租户、用户、权限、版本。

定位说明：

- 当前第一阶段代码可以在没有关系型数据库的情况下运行，依赖 `Milvus` 承载检索所需的 chunk 与基础 metadata。
- 但从长期架构看，关系型数据库仍然是推荐补充的一层，适合在第二阶段开始建设。

设计原则：

- `Milvus` 负责“检索面数据”。
- 关系型数据库负责“业务面数据”。
- 不把文档状态、权限、版本、批次任务等事务型数据长期压在 `Milvus` 上。

推荐方向：

- 关系型数据库建议优先选 `PostgreSQL`。
- 如果后续需要异步任务编排、后台运营系统、文档中心、权限体系，这一层基本是必选项。

---

## 5. 目标系统能力范围

本项目第一阶段要实现的不是“所有 RAG 论文技巧”，而是一套完善好用、可持续演进的后端。

第一阶段目标能力：

1. 文档接入与切分。
2. 文档 embedding 与 Milvus 入库。
3. 基础语义检索。
4. 查询改写。
5. 重排。
6. 基于上下文的回答生成。
7. 来源引用。
8. LangGraph Server 暴露统一图接口。
9. 配置化模型选择与参数控制。
10. 单元测试、集成测试、离线评测入口。

当前代码已落地情况：

- 已完成：
  - 多图注册与图编排
  - `assistant-ui` 兼容的消息态图入口
  - `DeepSeek` / `BGE-M3` / `Milvus` / `reranker` 的统一工厂入口
  - `PromptTemplate + LCEL` 风格的查询分析、查询改写、回答生成
  - `query analysis -> rewrite -> retrieve -> rerank -> generate -> finalize` 主链
  - `load -> normalize -> split -> upsert -> finalize_ingestion` 入库主链
  - `.env.example`
  - `docker-compose.yml`
  - `server/README.md` 的项目化说明
  - 最小运行验证
- 已部分完成：
  - `DeepSeek` 真实调用
  - `Milvus` 真实入库
  - `Milvus` 真实检索
  - `bge-reranker-v2-m3` 真实打分
  - `Milvus` 集合 create/load 准备逻辑
  - URL / 文件 / 目录三种入库源支持
  - 面向上传场景的多格式解析能力：
    - `md/markdown/txt/csv/json/html`
    - `pdf/docx/pptx/xlsx`
    - `doc/ppt/xls` 兼容回退
    - 图片 / 音频 / 视频占位接入
  - 源文件受控存储能力：
    - 支持 `source_uri` 本地文件先复制到受控目录
    - 支持 `source_content_b64 + source_name` 直接上传入库
    - 默认本地备份，可选同步到 `MinIO`
    - 独立表 `document_source_storage` 记录 `original_source_uri / replay_source_uri / storage_uri`
  - `PostgreSQL` 的 `ingest_job` / `document` / `document_version` / `chunk_manifest` 主数据链路
  - 旧版本 chunk 清理与版本替换状态推进
  - `rag_delete_graph` 与 `delete_job` 删除任务链路
  - `rag_reindex_graph` 重建索引链路
  - `chunk_manifest` 归档/软删除字段
  - 面向文档中心/后台管理的最小读模型查询
- 尚未完成：
  - 更完整的 collection/index 初始化与迁移策略
  - 更完善的 metadata 过滤
  - multi-query / decomposition / hybrid retrieval
  - 完整 pytest 回归
  - 更完整的关系型数据库设计与业务主数据落库
  - 删除后归档策略、版本回滚、索引重建编排与后台读模型扩展

第二阶段增强能力：

1. Multi-query retrieval。
2. Decomposition retrieval。
3. Metadata filter。
4. Query router。
5. Hybrid retrieval。
6. CRAG / Self-RAG 风格的自适应流程。
7. 多租户 / 多知识库。
8. 对接前端会话状态与用户权限。
9. 引入关系型数据库承载业务主数据。
10. 建立文档版本、任务状态、权限和审计能力。

---

## 6. 总体架构分层

建议采用 6 层结构。

```text
接入层
  -> 图编排层
    -> 应用服务层
      -> 领域能力层
        -> 基础设施层
          -> 外部依赖层
```

如果引入关系型数据库，整体依赖关系可进一步细化为：

```text
接入层
  -> 图编排层
    -> 应用服务层
      -> 领域能力层
        -> 基础设施层
          -> Milvus（检索面）
          -> PostgreSQL（业务面）
          -> 外部模型与观测系统
```

### 6.1 接入层

职责：

- 承接 LangGraph Server 对外暴露的运行接口。
- 未来对接前端 `assistant-ui`、后台任务系统、CLI 调试工具。

当前实现：

- 图编排核心仍然保持在 LangGraph。
- 前后端本地联调阶段额外引入 `FastAPI compat API` 作为桥接层。

原因：

- 官方 LangGraph Server 在不同 Python 版本下存在运行约束，本地开发环境未必稳定满足。
- 前端 `assistant-ui` 与管理控制台除了消息态线程协议，还需要稳定的管理型 HTTP 接口。
- 通过轻量兼容层桥接本地图对象，可以先把前后端链路打通，再决定是否切回官方 Server。

当前兼容层：

- 文件：
  - `src/agent/compat_api.py`
- 对外接口：
  - `/health`
  - `/compat/assistant/threads`
  - `/compat/assistant/chat`
  - `/compat/admin/page-contract`
  - `/compat/admin/query`
  - `/compat/ingest`
  - `/compat/delete`
  - `/compat/reindex`
- 内部调用：
  - `assistant_graph` / `rag_query_graph`
  - `rag_admin_graph`
  - `rag_ingest_graph`
  - `rag_delete_graph`
  - `rag_reindex_graph`

与前端模板的接口边界补充：

- `client` 当前基于 `assistant-ui`
- 管理页与动作接口默认通过 Next.js 代理访问 `/api/compat/*`
- 代理上游为本地 `FastAPI compat API`
- 对话线程主入口应绑定消息态图：
  - `agent`
  - 或 `assistant_graph`
- 文档中心/后台管理不建议强行塞进聊天消息协议
- 因此后端应额外暴露管理型图：
  - `rag_ingest`
  - `rag_delete`
  - `rag_reindex`
  - `rag_admin`

这样做的好处是：

- 聊天侧和后台侧接口边界清楚
- 当前前端可以直接走兼容 HTTP API
- 后续也仍然可以切回 LangGraph API，或在 Next.js BFF 层继续做二次封装
- 图编排仍然统一落在后端，不把管理流程散落到前端
- 对于 `rag_ingest / rag_reindex / rag_delete` 这类管理型动作，可以继续由图承载完整执行链，但对前端暴露的 compat HTTP 语义应优先设计为“提交任务并立即返回 job id”，由任务中心承担后续进度观察

### 6.2 图编排层

职责：

- 定义图状态。
- 定义节点之间的先后关系和分支关系。
- 只组织流程，不承担底层实现细节。

典型内容：

- `graph.py`
- `state.py`
- `routing.py`
- `edges.py`

当前实现补充：

- `assistant_graph` 负责把 `assistant-ui` 的 `messages` 状态适配为内部 `user_query`
- `rag_query_graph` 保持后端内部 RAG 主链清晰可调试
- 这种“双入口、同主链”的设计，符合前端协议适配与后端工程可维护性的平衡
- `rag_admin_graph` 开始承接面向文档中心/任务中心的稳定查询接口
- 当前已支持：
  - `list_documents`
  - `get_document_detail`
  - `list_document_versions`
  - `list_ingest_jobs`
  - `get_ingest_job_detail`
  - `list_delete_jobs`
  - `get_delete_job_detail`
  - `get_page_contract`
- 列表型查询已支持：
  - `page`
  - `page_size`
  - `status_filter`
  - `source_type_filter`
  - `query`
  - `sort_by`
  - `sort_direction`
- 页面级契约已支持：
  - `tables`
  - `sections.fields`
  - `sections.stat_cards`
  - `sections.tables`
- 页面级契约已支持：
  - `document_list`
  - `document_detail`
  - `ingest_job`
  - `delete_job`
- 当前约束补充：
  - 未知 `operation` 返回显式错误，不再默认回退到 `list_documents`
  - 未知 `page_name` 返回显式错误，不再默认回退到 `document_list`
  - 前端管理台必须按 contract 渲染列表/详情结构，禁止再次与后端维护两套列定义

### 6.3 应用服务层

职责：

- 把多个领域能力组合成“一个可被图节点调用的服务”。
- 保持节点函数轻量，避免节点里全是业务细节。

典型内容：

- `RagQueryService`
- `IngestionService`
- `RetrievalService`
- `AnswerService`

当前已落地的应用服务补充：

- `IngestApplicationService`
  - 负责入库主流程编排、旧 chunk 清理与任务收口
- `DeleteApplicationService`
  - 负责删除任务编排与严格失败语义
- `ReindexApplicationService`
  - 负责重建索引前的来源回放与 document identity 固定
- `AdminApplicationService`
  - 负责后台读模型查询的操作分发
  - 当前已收敛为显式 registry + `AdminQueryContext`，避免继续膨胀的字符串分支
- `ConversationService`
  - 负责消息态输入输出和 `assistant-ui` 适配
- `DocumentSourceService`
  - 负责来源元数据整形、公共 metadata 清洗与 replay/source mapping 逻辑

说明：

- 图节点现在更偏“状态衔接器”
- 复杂的流程协作尽量收敛到应用服务
- 这样可以减少图节点膨胀，符合 Python 项目中“编排与实现分离”的工程实践
- 后台查询的排序、详情聚合、筛选枚举统一在 repository/DTO 层固化，不让前端直接拼接数据库语义
- 页面级后端契约通过独立服务输出，不让前端自己猜 operation 组合关系
- `page contract` 当前已从“筛选/排序辅助信息”升级为页面主渲染契约：
  - 列表页消费 `tables`
  - 详情页消费 `sections.fields / sections.stat_cards / sections.tables`

### 6.4 领域能力层

职责：

- 封装与 RAG 直接相关的核心能力。

包括：

- 查询分析
- 查询改写
- 文档切分
- 检索
- 重排
- 引用整理
- 回答合成

### 6.5 基础设施层

职责：

- 管理具体 provider 和外部系统连接。
- 管理 repository、schema、migration 和稳定返回契约。

包括：

- `ChatDeepSeek` 实例工厂
- `HuggingFaceEmbeddings` 实例工厂
- `Milvus` 向量库连接
- `PostgresSchemaManager`
- `PostgresRegistryRepository`
- `PostgresReadRepository`
- Prompt 模板加载

其中当前 PostgreSQL repository 已进一步收敛为：

- 读模型 repository
  - 继续使用轻量查询连接
- 写模型 repository
  - 使用显式事务边界
  - 关键写入点包括：
    - `create_ingest_job`
    - `register_documents`
    - `finalize_ingest_job`
    - `create_delete_job`
    - `finalize_delete_job`

这样做的目的，是让一次入库或删除中的多表状态推进具备更稳定的 commit / rollback 语义，避免出现半成功状态。
- 本地缓存
- 运行配置读取
- DTO / schema
- 共享常量

实现补充：

- `PostgresReadRepository` 现在不只是“查列表”，还负责：
  - 排序字段白名单控制
  - 文档详情聚合
  - 入库任务详情聚合
  - 删除任务详情聚合
- 动态排序使用安全字段映射，而不是把前端传入字段直接拼到 SQL 中
- `schemas/admin_constants.py` 用来沉淀前后端共享的状态枚举和排序字段
- `services/admin_page_contract_service.py` 用来输出页面级 contract

### 6.6 外部依赖层

包括：

- DeepSeek API
- HuggingFace 模型权重 / 本地模型服务
- Milvus 服务
- LangSmith
- 对象存储或文档源
  - 当前默认受控源文件存储为本地目录
  - 可选同步到 `MinIO`

---

## 7. 推荐目录结构

原设计建议把 `src/agent` 目录扩展为更完整的分层结构。当前代码已落地的是一个精简但可运行的第一阶段版本。

```text
server/
  src/agent/
    __init__.py
    graph.py
    state.py
    context.py
    config.py
    dependencies.py
    prompts.py

    components/
      __init__.py
      factories.py

    nodes/
      __init__.py
      ingest_flow.py
      query_flow.py

    services/
      __init__.py
      answer_service.py
      ingestion_service.py
      retrieval_service.py
      rerank_service.py

    utils/
      documents.py

  tests/
    unit_tests/
    integration_tests/
```

说明：

- `graph.py` 只负责图定义，不再塞全部实现。
- 当前代码把图节点收敛成 `query_flow.py` 与 `ingest_flow.py` 两个文件，便于第一阶段快速演进。
- 当前代码把 provider 相关接入统一放进 `components/factories.py`，后续规模扩大后再拆成多个工厂文件。
- 当前代码新增 `prompts.py`，把查询分析、查询改写、回答生成的提示词和上下文格式化逻辑统一抽离出来，减少服务层中的硬编码 prompt。
- 原文档中的 `prompts/`、`schemas/`、`adapters/` 仍然是后续可以继续细化的目标目录，不是当前已完全落地状态。

---

## 8. 核心工作流设计

本项目建议拆成两张图，而不是所有事情都塞到一个图里。

## 8.1 图一：知识库入库图

图名建议：

- `rag_ingest`

职责：

- 接收文档源。
- 先把源文件转成系统可回放的来源对象。
- 根据文件类型选择解析器。
- 清洗、切分、打标签。
- 生成向量。
- 入库 Milvus。

节点建议：

1. `load_documents`
2. `normalize_documents`
3. `split_documents`
4. `upsert_documents`
5. `finalize_ingestion`

当前建议的入库输入契约：

- 传统来源模式
  - `source_uri`
  - `backup_source=true|false`
  - URL 场景还可附带：
    - `recursive_url=true|false`
    - `recursive_max_depth`
    - `recursive_prevent_outside=true|false`
- 直接上传模式
  - `source_name`
  - `source_mime_type`
  - `source_content_b64`
  - `backup_source=true|false`

其中：

- `source_uri`
  - 用于保留用户侧可理解的原始来源
- `replay_source_uri`
  - 用于系统内部重建索引和再次解析
- `source_storage`
  - 用于记录本地受控存储或 `MinIO` 对象位置
  - 当前权威落点是独立表 `document_source_storage`

因此当前真实入库主线已经从：

- `load -> normalize -> split -> upsert -> finalize`

进一步演进为：

- `prepare_source -> load -> normalize -> split -> upsert -> finalize`

其中 `prepare_source` 虽然被封装在 `load_documents` 节点前半段，但逻辑上已经独立成 `DocumentSourceStoreService`：

- 本地文件输入时：
  - 先复制到 `SOURCE_STORAGE_ROOT`
  - 再从受控副本解析
- 直接上传输入时：
  - 先按 `source_name` 落盘
  - 再进入解析链路
- `MinIO` 开启时：
  - 在保留本地副本的同时，把原文件同步到对象存储
- URL 输入时：
  - 支持单页抓取或站内递归抓取
  - 递归模式下，以根 URL 作为任务入口继续展开子页面
  - 每个命中的页面会作为独立文档进入主数据与向量库，而不是把整站内容拼成单文档
  - 每个页面文档会保留真实 `source_uri`
  - 元数据额外记录：
    - `crawl_root_uri`
    - `page_url`
    - `page_route`
    - `crawl_mode`
    - `recursive_max_depth`
  - 当前仍未做网页原始快照归档，后续重建索引默认按页面 URL 重新抓取

当前入库/删除链路也已经补上了更严格的成功语义：

- `load` 阶段如果没有解析出任何文档，任务直接标记为 `failed`
- `upsert` 阶段只有在 `Milvus` 真正写入成功时，`ingest_job/document/document_version` 才会收口为 `completed`
- 旧版 chunk 清理不完整时，重建任务直接失败，避免 PostgreSQL 与 Milvus 状态漂移
- 删除任务只有在 chunk 实际删除完成时，`delete_job` 才会收口为 `completed`

这意味着当前实现已经从“流程可运行优先”进一步收敛为“状态语义正确优先”。

当前推荐的主数据建模是：

- `document`
  - 文档主记录
  - 记录原始来源 `source_uri`
- `document_version`
  - 文档版本记录
- `document_source_storage`
  - 与 `document_version` 一对一
  - 保存：
    - `original_source_uri`
    - `replay_source_uri`
    - `source_name`
    - `source_mime_type`
    - `configured_backend / effective_backend`
    - `storage_uri / local_path / bucket / object_key`
    - `sync_status / sync_error`
    - `path_mapping`

这样做的原因是：

- 避免把源文件存储信息长期塞在 `document.metadata`
- 让重建索引直接依赖结构化主数据
- 让后台管理页可以稳定展示“原始来源”和“备份位置”

当前 `load_documents` 已经不是单纯读取文本文件，而是通过 `DocumentParserService` 做一层解析策略分发：

- `simple`
  - 适用于 `md/txt/csv/json/html`
  - 直接在 Python 服务内转成可切分文本
- `builtin`
  - 适用于 `pdf/docx/pptx/xlsx`
  - 优先走专用 Python 解析依赖
- `fallback`
  - `doc/ppt/xls` 优先尝试 `UnstructuredFileLoader`
  - 失败后退化成占位文本，避免整条入库任务失败
- `multimodal_placeholder`
  - 图片 / 音频 / 视频当前只保留元数据和占位文本
  - 未来可在这一层接 OCR / ASR / VLM 流程，而不破坏主图结构

适用触发方式：

- 后台任务
- 管理接口
- 批量构建知识库
- 前端上传文件后直接传 `source_content_b64`
- 前端上传文件后转路径触发 `rag_ingest`

## 8.2 图二：问答检索图

图名建议：

- `rag_query`

职责：

- 接收用户问题。
- 判断检索策略。
- 召回候选文档。
- 重排与裁剪。
- 生成答案并返回引用。

推荐流程：

```text
__start__
  -> analyze_query
  -> route_query
  -> rewrite_query
  -> retrieve
  -> rerank
  -> generate
  -> finalize
```

当前代码实现状态：

- `rag_query_graph` 已按上面流程落地
- `rag_ingest_graph` 已按 `load -> normalize -> split -> upsert -> finalize` 落地
- `embed_documents` 没有作为独立节点拆出，而是并入了 `upsert_documents` 所依赖的向量库写入过程
- 这种实现方式符合第一阶段“先简化节点数、再稳定 provider 接入”的策略

---

## 9. 问答图的节点职责定义

### 9.1 `analyze_query`

职责：

- 判断问题类型。
- 提取检索策略信息。
- 判断是否需要：
  - query rewrite
  - metadata filter
  - decomposition
  - fallback 回答

实现建议：

- 使用 `ChatDeepSeek.with_structured_output(...)`。
- 输出结构化分析对象，而不是自由文本。

输出示例：

```python
class QueryAnalysis(BaseModel):
    intent: Literal["faq", "knowledge_qa", "comparison", "multi_hop"]
    need_rewrite: bool = True
    need_rerank: bool = True
    need_metadata_filter: bool = False
    top_k: int = 12
```

设计原因：

- notebook 中 Part 10 和 Part 11 的思想表明，真正的 RAG 需要在检索前做查询理解。

### 9.2 `route_query`

职责：

- 未来多知识库时，根据问题路由到不同 collection 或不同 retriever 配置。

第一阶段策略：

- 保留节点和 schema，但默认走单知识库。

原因：

- 先把架构设计好，避免后续改图时大拆。

### 9.3 `rewrite_query`

职责：

- 在单问题检索前做轻量改写。

第一阶段推荐：

- 使用单条 rewrite，而不是一上来就上 multi-query。

原因：

- simple rewrite 收益高，成本可控。
- multi-query 会增加 Milvus 查询次数和整体延迟。

第二阶段增强：

- 切换到 multi-query 版本。
- 或在复杂问题上做 decomposition。

### 9.4 `retrieve`

职责：

- 执行基础召回。
- 返回候选文档列表。

实现策略：

- 使用 `langchain_milvus.Milvus` 构建 vector store。
- 由工厂方法创建 retriever。
- 通过 `search_kwargs` 控制 `k`、filters、score_threshold` 等参数。

第一阶段推荐召回模式：

- `dense retrieval`
- top-k 取值建议 `10~20`

原因：

- 保证链路稳定。
- 和 `BGE-M3 + Milvus + reranker` 的组合最匹配。

### 9.5 `rerank`

职责：

- 对召回文档重新排序。
- 去掉低相关候选。
- 压缩最终上下文。

实现建议：

- 首选 `CrossEncoderReranker` 风格组件。
- 使用 `bge-reranker-v2-m3` 作为 cross-encoder 模型。
- 上层封装成 `RerankService`。

第一阶段策略：

- 先召回 `top_k=12~20`
- 重排后保留 `top_n=4~6`

原因：

- 这是最接近 notebook 中 Part 15 的工程化落地方式。

### 9.6 `generate`

职责：

- 基于问题和最终文档生成回答。
- 要求回答严格受上下文约束。
- 同时整理引用信息。

实现建议：

- 模型统一使用 `ChatDeepSeek`。
- prompt 明确区分：
  - 系统指令
  - 检索上下文
  - 用户问题
  - 输出格式

第一阶段回答约束：

- 不知道就明确说不知道。
- 不允许编造来源。
- 引用必须绑定返回文档 ID。

### 9.7 `finalize`

职责：

- 将最终结果整理成统一响应结构。
- 输出：
  - answer
  - citations
  - debug_info
  - trace metadata

---

## 10. 状态模型设计

LangGraph 图的关键在于状态设计，而不是单个节点函数。

建议使用清晰的状态 schema。

```python
class RetrievedChunk(TypedDict):
    chunk_id: str
    document_id: str
    content: str
    score: float
    metadata: dict


class RagState(TypedDict, total=False):
    user_query: str
    rewritten_query: str
    analysis: dict
    filters: dict
    candidate_chunks: list[RetrievedChunk]
    reranked_chunks: list[RetrievedChunk]
    answer: str
    citations: list[dict]
    debug: dict
    error: str
```

设计原则：

- `state` 保存运行过程中的动态数据。
- `context` 保存运行时依赖和静态资源。
- 不把数据库连接、模型实例塞进 state。

---

## 11. Context 与依赖注入设计

当前模板已经体现了 `context_schema` 的概念，完整项目应充分利用它。

建议把运行时 context 用于传递：

- collection 名称
- 租户 ID
- 知识库 ID
- 检索策略
- 模型配置别名
- debug 开关

示例：

```python
class RagContext(TypedDict, total=False):
    assistant_id: str
    knowledge_base: str
    retriever_profile: str
    response_model: str
    enable_query_rewrite: bool
    enable_rerank: bool
```

而模型实例、Milvus 客户端等重量级对象建议通过：

- `dependencies.py`
- 工厂函数
- 单例缓存

进行管理。

原因：

- `context` 是运行时配置，不应承载复杂对象。
- 复杂对象应在基础设施层统一构造和复用。

---

## 12. 配置系统设计

建议建立统一配置入口 `config.py`。原设计提过基于 `pydantic-settings` 管理，但当前代码为了保证在依赖未完整安装时也能运行，实际落地采用了更轻量的环境变量读取方式。

当前实现补充说明：

- `config.py` 启动时会主动加载 `server/.env`
- `AppSettings` 继续保持 dataclass 风格，避免第一阶段引入过重配置框架
- 当前代码除 `.env.example` 外，也维护了可直接本地开发使用的 `.env`
- 当前 Milvus 相关字段名和索引行为也已经配置化，包括：
  - `MILVUS_PRIMARY_FIELD`
  - `MILVUS_TEXT_FIELD`
  - `MILVUS_VECTOR_FIELD`
  - `MILVUS_METADATA_FIELD`
  - `MILVUS_METRIC_TYPE`
  - `MILVUS_INDEX_TYPE`

配置范围建议包括：

- DeepSeek
  - `DEEPSEEK_API_KEY`
  - `DEEPSEEK_MODEL`
  - `DEEPSEEK_BASE_URL`
  - `DEEPSEEK_TEMPERATURE`
  - `DEEPSEEK_MAX_RETRIES`
- Embedding
  - `EMBEDDING_MODEL_NAME`
  - `EMBEDDING_DEVICE`
  - `EMBEDDING_NORMALIZE`
  - `EMBEDDING_QUERY_INSTRUCTION`
- Reranker
  - `RERANKER_MODEL_NAME`
  - `RERANK_TOP_N`
- Milvus
  - `MILVUS_URI`
  - `MILVUS_TOKEN`
  - `MILVUS_DB_NAME`
  - `MILVUS_COLLECTION`
  - `MILVUS_INDEX_PARAMS`
  - `MILVUS_SEARCH_PARAMS`
- Retrieval
  - `RETRIEVAL_TOP_K`
  - `SCORE_THRESHOLD`
- Chunking
  - `CHUNK_SIZE`
  - `CHUNK_OVERLAP`
- Runtime
  - `LOG_LEVEL`
  - `ENABLE_LANGSMITH`

原则：

- 所有 magic number 不写死在节点里。
- 所有 provider 配置统一由配置层注入。
- 已同步到 [`.env.example`](file:///e:/git/rag-from-scratch/server/.env.example)
- 当前 `.env` 与 `docker-compose.yml` 已按本地开发环境完成一轮对齐。

---

## 13. 最新推荐实现方式

本节明确说明应优先使用哪些包和抽象。

### 13.1 LLM 层

推荐：

- `langchain-deepseek`

统一写法：

- 使用 `ChatDeepSeek`
- 当前服务层已经把调用收敛成：
  - `Prompt | ChatDeepSeek | StrOutputParser`
  - `Prompt | ChatDeepSeek.with_structured_output(...)`

不推荐：

- 在节点里直接写 DeepSeek 原生 SDK。

### 13.2 Embedding 层

推荐：

- `langchain-huggingface`

统一写法：

- 使用 `HuggingFaceEmbeddings`

模型：

- `BAAI/bge-m3`

说明：

- 这样可以统一接入 LangChain 的 `Embeddings` 接口。
- 后续替换 embedding 模型时不会影响图层逻辑。
- 当前代码中已考虑 `BGE-M3` 的特殊配置位 `EMBEDDING_QUERY_INSTRUCTION`，默认保持空字符串。

### 13.3 Vector Store 层

推荐：

- `langchain-milvus`

统一写法：

- 使用 `Milvus`

说明：

- 第一阶段通过 LangChain VectorStore 完成主链路。
- 必要的索引参数在基础设施层统一配置。
- 当前工厂层还补充了：
  - `MILVUS_INDEX_PARAMS` / `MILVUS_SEARCH_PARAMS` 的安全 JSON 解析
  - 低层 `MilvusClient` 预留位
  - collection load 准备逻辑

### 13.4 Reranker 层

推荐顺序：

1. 优先使用 LangChain 的 cross-encoder / compression 抽象。
2. 底层模型使用 `BAAI/bge-reranker-v2-m3`。

建议封装形式：

- `RerankService`
- `DocumentCompressor`
- `ContextualCompressionRetriever`

设计要求：

- 无论底层最终选 `HuggingFaceCrossEncoder` 还是适配器封装，图层接口都保持一致。
- 当前代码已优先尝试 `HuggingFaceCrossEncoder`，失败时回退到词面重排。

### 13.5 Splitter 层

推荐：

- `RecursiveCharacterTextSplitter`

原因：

- 这是目前通用文本的稳定默认方案。
- 也是 notebook 中最核心、最具延续性的部分。
- 当前代码在 `langchain_text_splitters` 不可用时保留了 fallback splitter，以保证本地链路可运行。

### 13.6 Structured Output 层

推荐：

- `ChatDeepSeek.with_structured_output(PydanticModel)`

适用：

- 查询分析
- filter 提取
- route decision
- 回答格式约束

---

## 14. 关于 BGE-M3 与 Hybrid Retrieval 的设计取舍

这是本项目最需要讲清楚的一点。

`BGE-M3` 本身强调：

- 多语言
- 多粒度
- 多功能
- 可支持 dense / sparse / hybrid retrieval 思路

但在**LangChain 风格统一**这个约束下，需要做取舍。

### 14.1 第一阶段推荐方案

第一阶段采用：

- `BGE-M3 dense embedding`
- `Milvus dense retrieval`
- `BGE reranker`

原因：

1. 这条链路最稳定。
2. 最符合 LangChain 标准抽象。
3. 最容易接入 LangGraph 图。
4. 最容易做测试和性能调优。

### 14.2 第二阶段 hybrid 增强方案

第二阶段可扩展为：

- Dense retrieval
- Full-text / BM25 retrieval
- Milvus hybrid search
- Rerank merge

优先顺序建议：

1. 先用 `Milvus + full-text/BM25` 做 hybrid。
2. 再评估是否引入 `BGE-M3 sparse` 的专门适配层。

原因：

- 这样仍然可以把大部分代码留在 LangChain/Milvus 官方集成路径上。
- 避免为了追求“纯模型功能完整性”而过早把项目带回底层 SDK 拼装风格。

### 14.3 结论

本项目对 `BGE-M3` 的使用原则是：

- 第一阶段：把它作为主 dense embedding 模型。
- 第二阶段：再逐步释放其更复杂的 hybrid 能力。

这不是能力阉割，而是工程分阶段落地。

当前实现补充：

- embedding 层已预留 `EMBEDDING_QUERY_INSTRUCTION`
- 当前默认仍以 dense retrieval 为主
- hybrid / sparse / multi-vector 能力尚未在业务链路中启用

---

## 15. 数据模型设计

建议至少定义以下几个核心模型。

### 15.1 文档模型

```python
class SourceDocument(BaseModel):
    document_id: str
    source_type: str
    source_uri: str
    title: str | None = None
    content: str
    metadata: dict = Field(default_factory=dict)
```

### 15.2 切片模型

```python
class ChunkRecord(BaseModel):
    chunk_id: str
    document_id: str
    chunk_index: int
    content: str
    metadata: dict = Field(default_factory=dict)
```

### 15.3 检索结果模型

```python
class RetrievalHit(BaseModel):
    chunk_id: str
    document_id: str
    score: float
    content: str
    metadata: dict = Field(default_factory=dict)
```

### 15.4 响应模型

```python
class Citation(BaseModel):
    document_id: str
    chunk_id: str
    title: str | None = None
    source_uri: str | None = None


class RagResponse(BaseModel):
    answer: str
    citations: list[Citation]
    debug: dict = Field(default_factory=dict)
```

---

## 16. 检索策略设计

结合 notebook 中的经验，项目检索策略应分级。

### 16.1 默认策略

默认回答链路：

1. query analysis
2. single rewrite
3. dense retrieve
4. rerank
5. answer generation

这是主链路，也是第一阶段上线链路。

### 16.2 复杂问题策略

当 `analysis.intent in {"comparison", "multi_hop"}` 时：

- 可启用 decomposition 模式。

但第一阶段不要默认全量开启。

原因：

- 多跳问题比例通常不高。
- decomposition 会显著增加延迟和 token 成本。

### 16.3 高召回策略

当用户问题过短、术语过泛或检索命中率偏低时：

- 可启用 multi-query。

触发条件建议通过：

- query analysis
- offline evaluation
- 命中失败统计

来决定，而不是默认所有请求都开。

### 16.4 过滤检索策略

当知识库存在结构化 metadata 时：

- 使用结构化输出提取：
  - 时间范围
  - 文档类型
  - 标签
  - 业务域

然后把 filter 交给 retriever。

这直接承接 notebook 中第 11 部分的思想。

---

## 17. Prompt 体系设计

Prompt 不应散落在节点里，建议集中管理。

至少拆成以下几类：

### 17.1 Query Analysis Prompt

作用：

- 分类问题类型
- 抽取 filters
- 判断是否需要 rewrite / rerank / decomposition

### 17.2 Query Rewrite Prompt

作用：

- 把用户口语问题改写成更适合检索的查询。

### 17.3 Answer Prompt

作用：

- 约束模型只根据上下文回答。
- 没有证据时必须明确拒答或保守回答。
- 指导输出引用。

### 17.4 Synthesis Prompt

作用：

- 在 decomposition 或 multi-query 场景下综合多路结果。

Prompt 原则：

- 中文产品优先写中文 prompt。
- 指令短而稳定，不在第一阶段过度堆规则。
- 所有 prompt 版本化管理。

---

## 18. Milvus 设计细节

### 18.1 Collection 设计

建议每个知识库一个 collection，避免第一阶段多租户复杂度过高。

字段建议：

- `pk`
- `document_id`
- `chunk_id`
- `content`
- `dense_vector`
- `source_uri`
- `title`
- `biz_type`
- `created_at`
- `extra_metadata`

### 18.2 Index 设计

由基础设施层统一配置：

- 向量维度
- index type
- metric type
- search params

原则：

- 不在 graph/node 中写索引参数。
- 索引参数必须可通过配置调整。

### 18.3 Metadata 设计

metadata 必须保证后续可扩展：

- 文档来源
- 时间
- 标签
- 业务分类
- 权限字段

这样后续 metadata filter 才有意义。

### 18.4 当前阶段与后续边界

当前阶段：

- `Milvus` 可以直接承载：
  - chunk 文本
  - embedding
  - `document_id`
  - `chunk_id`
  - 基础检索 metadata
- 对于单知识库、单租户、先验证效果的场景，这已经足够支撑第一阶段问答闭环。
- 当前工厂层已补充：
  - `MILVUS_INDEX_PARAMS` / `MILVUS_SEARCH_PARAMS` 的环境变量解析
  - collection create/load 准备逻辑
  - 低层 client 预留位，方便后续补更完整的 collection/index 初始化

后续阶段：

- 不建议把 `Milvus` 继续扩展成业务主数据库。
- 一旦进入文档管理、权限控制、版本追踪、后台运营等需求，应该引入关系型数据库分担业务主数据。

---

## 19. 关系型数据库设计

本节以“后续目标 + 当前已落地部分”两个视角说明。

### 19.1 为什么需要关系型数据库

当系统从“RAG demo / 骨架”走向“正式后端服务”后，通常会出现以下需求：

- 文档版本管理
- 文档状态管理
  - 已上传
  - 处理中
  - 已切分
  - 已入向量库
  - 失败
- 文档去重
- 知识库管理
- 用户 / 租户 / 空间管理
- 权限控制
- 文档删除和级联删除
- 任务审计
- 入库批次记录
- 重建索引记录
- 前端文档列表页
- 后台管理页
- 文档和 chunk 的可追踪映射

这些数据都属于：

- 事务型
- 管理型
- 状态型
- 强一致
- 关系型

这类数据不适合长期只依赖 `Milvus` 管理。

换句话说：

- `Milvus` 很适合做“相似度检索”和“快速召回”。
- 但它不适合长期承担“文档中心 + 后台系统 + 状态机 + 审计系统”的职责。

如果不引入关系型数据库，并不是完全不能做，而是后面会越来越别扭，主要会体现在：

- 文档状态难以统一维护。
- 文档删除与 chunk 级联删除不容易做干净。
- 很难优雅支撑前端文档列表和后台管理页。
- 入库批次、失败重试、任务审计会缺少稳定的主记录。
- 文档版本、重建索引和权限变化缺少可靠的事务边界。
- `document_id -> chunk_id -> vector` 的可追踪映射容易分散在多处 metadata 中，后期维护成本高。

### 19.2 双存储职责划分

推荐采用：

- `Milvus`：检索主存储
- `PostgreSQL`：业务主存储

建议分工如下：

- `Milvus` 存储：
  - `chunk_id`
  - `document_id`
  - `content`
  - `dense_vector`
  - 检索必需 metadata
- 关系型数据库存储：
  - 原始文档记录
  - 文档状态
  - 文档版本
  - 知识库信息
  - 入库任务
  - 删除任务
  - 用户 / 租户 / 权限

也可以更直观地理解为：

- `Milvus`：检索面
  - 负责“查得快、查得像”
- 关系型数据库：业务面
  - 负责“存得清楚、管得明白”

### 19.3 推荐表设计方向

建议后续至少包含以下表：

- `knowledge_base`
  - 知识库定义、名称、业务域、启停状态
- `document`
  - 原始文档记录、来源、标题、状态、当前版本
- `document_version`
  - 文档版本、文件 hash、处理结果、更新时间
- `chunk_manifest`
  - 文档与 chunk 的映射关系、chunk 数量、索引批次
- `ingest_job`
  - 入库任务、状态、错误信息、执行耗时
- `delete_job`
  - 删除任务与级联清理状态
- `tenant`
  - 多租户主数据
- `user_permission`
  - 用户与知识库权限关系

### 19.4 与当前架构的对接方式

后续如果引入关系型数据库，建议这样接入：

- 图层仍然不直接访问数据库细节。
- 在应用服务层新增：
  - `DocumentRegistryService`
  - `IngestJobService`
  - `KnowledgeBaseService`
- 在基础设施层新增：
  - `PostgresSessionFactory`
  - `Repository` 层

这样可以保证：

- 图编排仍然保持轻量
- `Milvus` 与关系库职责清晰
- 后续后台管理、审计和权限功能更容易扩展

当前代码已经落地的对接方式：

- 图层仍然不直接操作 SQL，而是通过 `IngestApplicationService` / `DeleteApplicationService` / `ReindexApplicationService`
- `load_documents` 节点会创建 `ingest_job`
- `normalize_documents` 节点会注册 `document` 并同步创建 `document_version`
- `split_documents` 阶段会把 `version_id` / `version_number` 继续带入 chunk
- `upsert_documents` 在写入新版本前，会先基于历史版本查询旧 chunk id 并尝试从 `Milvus` 删除
- `upsert_documents` 完成后会登记 `chunk_manifest`，并回写任务、文档、版本状态
- `finalize_ingestion` 的结果中已返回 `registered_document_ids` 和 `registered_version_ids`
- 已新增 `rag_delete_graph`，用于承接文档删除任务
- 管理查询统一通过 `AdminApplicationService -> PostgresReadRepository` 执行

### 19.5 实施建议

建议采用分阶段方式：

1. 第一阶段：
   - 继续允许 `Milvus-only` 运行
   - 先打通问答与入库主链
   - 同时允许按需启用 `PostgreSQL`，承接最小主数据链路
2. 第二阶段：
   - 扩展 `PostgreSQL`
   - 从最小主数据链路扩展到更完整的文档主记录、任务状态、权限与版本信息
3. 第三阶段：
   - 打通后台运营与文档中心
   - 完善删除、重建、迁移与审计流程

---

## 20. 回答生成与引用策略

RAG 项目“好不好用”，不只看答得像不像，还看有没有证据链。

建议输出结构包含：

- `answer`
- `citations`
- `used_chunks`
- `debug`

引用策略：

1. 每个候选 chunk 都带 `chunk_id/document_id/source_uri`。
2. 生成完成后，按最终使用的文档顺序整理引用。
3. 前端未来只展示 `answer + citations`。
4. 调试模式下可返回候选文档与打分。

---

## 21. 可观测性与评测设计

### 20.1 LangSmith

建议全程接入 LangSmith。

跟踪内容：

- 每个节点耗时
- LLM token 使用
- retriever 输入输出
- reranker 输入输出
- 最终回答

### 20.2 评测指标

至少关注：

- 检索命中率
- 重排后命中率
- 回答准确率
- 引用准确率
- 平均延迟
- token 成本

### 20.3 错误定位

问题要能快速归因到以下层：

- query analysis 错了
- rewrite 错了
- retrieve 没召回
- rerank 排错了
- generate 幻觉了

这正是 LangGraph + LangSmith 组合的价值所在。

---

## 22. 测试策略

用户已明确说明：如需测试，使用 `cmd` 并通过 `conda activate mbs` 激活环境，不能依赖 PowerShell。

因此项目测试规范建议写死如下：

### 21.1 本地测试命令

```cmd
conda activate mbs
cd /d e:\git\rag-from-scratch\server
pytest
```

### 21.2 单元测试

覆盖：

- 配置加载
- prompt 输出格式
- query analysis schema
- rerank service
- citation formatting

### 21.3 集成测试

覆盖：

- LangGraph 图能成功运行
- 入库后可以正确召回
- 回答结果结构正确

### 21.4 端到端测试

覆盖：

- 从文档入库到问答返回引用的完整链路

原则：

- 第一阶段尽量 mock LLM。
- 对 Milvus 建立最小可复现测试数据。

---

## 23. 推荐依赖清单

建议在现有 `pyproject.toml` 基础上扩展如下依赖方向：

```text
langgraph
langgraph-cli[inmem]
langchain
langchain-core
langchain-community
langchain-deepseek
langchain-huggingface
langchain-milvus
sentence-transformers
pymilvus
pydantic-settings
python-dotenv
pytest
ruff
mypy
```

说明：

- `langchain-community` 主要保留给少数社区集成和过渡能力。
- 主 provider 仍优先使用独立包：
  - `langchain-deepseek`
  - `langchain-huggingface`
  - `langchain-milvus`

---

## 24. 分阶段实施路线

### 阶段一：基础可用版

目标：

- 单知识库
- 单轮问答
- dense retrieval
- rerank
- citations

完成项：

- 重构目录结构
- 接入 DeepSeek
- 接入 BGE-M3
- 接入 Milvus
- 接入 BGE reranker
- 完成 `rag_query` 图

当前状态：

- 已完成：
  - `rag_query_graph`
  - `rag_ingest_graph`
  - `.env.example`
  - `.env`
  - `docker-compose.yml`
  - `server/README.md` 项目化说明
  - 统一工厂层
  - 统一 Prompt 层
  - 服务层与节点层
  - 最小链路验证
- 已接入但仍依赖外部环境就绪：
  - `ChatDeepSeek`
  - `HuggingFaceEmbeddings`
  - `Milvus`
  - `HuggingFaceCrossEncoder`
- 已开始落地并具备第一版可追踪链路：
  - `PostgreSQL`
  - `ingest_job` / `document` / `document_version` / `chunk_manifest`
- 仍需继续补强：
  - 更完整的 collection/index 初始化与迁移策略
  - 完整真实数据入库
  - pytest 回归环境
  - 更完整的调用示例与联调说明
  - 删除后 chunk_manifest 的归档策略、版本回滚与重建流程

### 阶段二：知识库建设版

目标：

- 建立 `rag_ingest` 图
- 完整入库流程
- metadata 体系
- 后台更新能力
- 引入关系型数据库并承载业务主数据
- 补齐入库任务、文档状态与版本管理

### 阶段三：检索增强版

目标：

- multi-query
- decomposition
- metadata filter
- query router
- 文档中心与后台管理查询能力

### 阶段四：高级检索版

目标：

- hybrid retrieval
- 自适应检索策略
- failover / fallback answer
- 更完整评测体系

---

## 25. 最终落地建议

综合 notebook 思路、当前后端模板、以及技术栈约束，本项目的最佳落地方式不是直接“复刻所有 notebook”，而是：

1. 先把 notebook 中最有工程价值的主链抽出来：
   - query analysis
   - query rewrite
   - retrieve
   - rerank
   - generate

2. 用 LangGraph 把它们编排成清晰的图。

3. 用 LangChain 的 provider 封装统一管理：
   - `ChatDeepSeek`
   - `HuggingFaceEmbeddings`
   - `Milvus`
   - `CrossEncoderReranker`

4. 把高级策略做成可插拔增强项，而不是一开始就全部硬编码进主链路。

补充说明：

- 当前代码已经完成“第一阶段真实接入骨架”的同步，不再只是纯设计或纯占位 demo。
- 文档后续应继续按“设计目标 + 当前实现状态”双视角维护，避免再次出现设计与代码脱节。
- 关于存储层，当前允许 `Milvus-only` 运行，但长期建议演进为 `PostgreSQL + Milvus` 双存储架构。
- 当前实现已经把查询分析、查询改写、回答生成收敛到 LangChain Prompt/LCEL 风格，后续应继续沿着这种统一抽象推进，而不是回退到零散字符串 prompt 和底层 SDK 直连风格。

---

## 26. 本设计的核心结论

这套项目设计的核心不是“实现一个能答题的 demo”，而是建立一套**长期可演进的 RAG 后端骨架**。

最终架构原则可以归纳为 6 句话：

1. **LangGraph 负责流程，不负责底层实现。**
2. **LangChain 负责统一抽象，不直接把业务绑死在厂商 SDK 上。**
3. **DeepSeek 负责推理与结构化理解。**
4. **BGE-M3 负责统一 embedding，BGE reranker 负责精排。**
5. **Milvus 负责存储与召回，但业务只面向 retriever。**
6. **关系型数据库负责业务主数据，后续与 Milvus 形成双存储分工。**
7. **先做稳定主链，再逐步引入 notebook 中的高级策略。**

如果后续按照本文档推进，当前 `server` 模板就可以逐步演进成一套结构清晰、风格统一、便于测试和扩展的现代 RAG 服务端。
