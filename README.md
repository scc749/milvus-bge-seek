# milvus-bge-seek

一个围绕 `Milvus + BGE + DeepSeek + LangGraph` 搭建的全栈 RAG 工程骨架，包含：

- `client/`：基于 `Next.js App Router + assistant-ui` 的前端控制台与聊天界面
- `server/`：基于 `FastAPI compat API + LangGraph` 的后端编排层、任务层、读模型与存储层

当前仓库已经不是简单模板，而是一个可联调、可追踪、具备文档中心和任务中心能力的第一阶段工程实现。

## 项目定位

这个项目的核心目标不是只做一个“能回答问题的聊天页”，而是把 RAG 系统拆成可维护的前后端协作形态：

- 聊天链路：支持多轮会话、线程持久化、流式返回、单轮推理轨迹展示
- 文档链路：支持文件上传、URL 抓取、本地目录导入、版本化入库、重建索引、删除文档
- 后台链路：支持文档中心、版本历史、入库任务、删除任务，以及页面级契约
- 存储链路：同时使用 `PostgreSQL` 管理业务主数据、`Milvus` 管理向量检索、可选 `MinIO` 管理源文件备份

从代码形态上看，仓库已经形成了“前端契约消费 + 后端图编排 + 任务状态推进 + 数据持久化”的完整闭环。

## 仓库结构

```text
milvus-bge-seek/
├─ README.md
├─ client/                         # Next.js 前端
│  ├─ app/                         # 路由层与页面装配
│  ├─ components/                  # assistant-ui、console、通用 UI
│  ├─ lib/                         # facade、compat transport、contract 解析
│  ├─ package.json
│  └─ 前端架构规范文档.md
└─ server/                         # FastAPI + LangGraph 后端
   ├─ src/agent/
   │  ├─ api/                      # compat API 路由与请求模型
   │  ├─ nodes/                    # LangGraph 节点
   │  ├─ services/                 # 应用服务与领域服务
   │  ├─ repositories/             # PostgreSQL 读写仓储
   │  ├─ schemas/                  # 常量、DTO、页面契约
   │  ├─ components/               # LLM / Embedding / Milvus 工厂
   │  ├─ graph.py                  # 图定义
   │  ├─ dependencies.py           # 依赖容器
   │  └─ compat_api.py             # FastAPI 入口
   ├─ tests/                       # 集成测试与单元测试
   ├─ docker-compose.yml           # PostgreSQL / Milvus / MinIO / etcd
   ├─ pyproject.toml
   ├─ README.md
   ├─ 后端架构规范文档.md
   └─ RAG_项目架构设计文档.md
```

## 整体架构

当前联调默认走以下请求链路：

```text
Browser
  -> Next.js client
    -> /api/compat/*
      -> FastAPI compat API
        -> LangGraph graphs / Application Services
          -> PostgreSQL / Milvus / MinIO / 模型服务
```

职责划分如下：

- `client`
  - 负责聊天体验、管理台页面、表单交互、表格渲染、首屏 SSR 预取与浏览器侧刷新
- `server`
  - 负责图编排、任务语义、源文件处理、向量入库、删除与重建、线程持久化、后台查询
- `PostgreSQL`
  - 负责线程、文档、版本、任务、chunk manifest、源文件存储记录
- `Milvus`
  - 负责 chunk 向量检索与删除
- `MinIO`
  - 可选，用于将源文件从本地受控目录进一步同步到对象存储，便于后续重放

## 前端总结

### 技术栈

- `Next.js 16`
- `React 19`
- `assistant-ui`
- `@assistant-ui/react-langgraph`
- `Biome`
- 自定义 contract 解析与 compat gateway

### 路由与页面

前端根路由会直接跳转到 `/assistant`，主要页面包括：

- `/assistant`
  - 聊天入口
  - 左侧为线程列表，右侧为消息流
  - 线程 ID 和侧栏收缩状态会写入 `localStorage`
- `/documents`
  - 文档中心
  - 支持文件上传和 URL 入库
  - URL 模式支持站内递归抓取及最大深度配置
- `/documents/[documentId]`
  - 文档详情
  - 展示摘要、统计、最近版本、完整版本历史
  - 支持 `delete` 与 `reindex`
- `/jobs/ingest`
  - 入库任务列表与详情
- `/jobs/delete`
  - 删除任务列表与详情

### 前端分层

代码严格按四层组织：

- `app/`
  - 只做路由装配、查询参数解析、SSR 首屏预取
- `components/console/`
  - 管理台业务组件
  - 通过后端 page contract 决定列表列、详情字段、统计卡和 tab 区块
- `components/assistant-ui/`
  - 定制 assistant-ui 的消息渲染
  - 支持 Markdown、代码块复制、检索命中折叠展示、实时轨迹和历史轨迹恢复
- `lib/`
  - 封装前端 facade、transport、compat gateway、page-contract 解析

### 前端关键实现

- 所有管理台接口都收口在 `client/lib/api/`
  - 页面和组件不直接写 `fetch('/compat/...')`
- `client/app/api/[..._path]/route.ts`
  - 作为 Edge 代理，把 `/api/*` 转发到后端 `LANGGRAPH_API_URL`
- `client/lib/serverCompatApi.ts`
  - Server Component 首屏预取使用
- `client/lib/langgraphApi.ts`
  - 浏览器侧管理台刷新、任务提交使用
- `client/lib/chatApi.ts`
  - 聊天专用 facade
  - 通过 `/compat/assistant/chat/stream` 消费 NDJSON 流
  - 把后端 `custom` 事件转成前端可展示的 `analysis / retrieval / generation` 轨迹
- `client/components/assistant-ui/thread.tsx`
  - 把“问题分析 -> 知识检索 -> 答案生成”嵌入到每一轮消息，而不是放在页面顶部固定面板
- 管理页支持静默轮询
  - 文档和任务处于 `created/pending/processing/running` 时，每 5 秒后台刷新一次

## 后端总结

### 技术栈

- `Python 3.10+`
- `FastAPI`
- `LangGraph`
- `LangChain`
- `Milvus`
- `PostgreSQL`
- `MinIO`
- `DeepSeek / HuggingFace` 接入位

### compat API

后端没有强依赖官方 LangGraph Server 作为联调入口，而是提供了一层本地兼容 API：

- `/health`
- `/compat/assistant/threads`
- `/compat/assistant/chat`
- `/compat/assistant/chat/stream`
- `/compat/admin/page-contract`
- `/compat/admin/query`
- `/compat/ingest`
- `/compat/delete`
- `/compat/reindex`

这层 API 的目标是：

- 在 Python 3.10 环境下稳定联调
- 同时服务聊天线程协议和管理台 HTTP 协议
- 把图输出归一成前端能直接消费的结构

### LangGraph 图定义

`server/src/agent/graph.py` 当前注册了 6 个主要图：

- `assistant_graph`
  - 消息态入口，兼容 `assistant-ui`
  - 从 `messages` 中提取最新用户问题，再复用查询链路生成答案
- `rag_query_graph`
  - 纯查询图
  - 步骤为 `analyze -> route -> rewrite -> retrieve -> rerank -> generate -> finalize`
- `rag_ingest_graph`
  - 入库图
  - 步骤为 `load -> normalize/register -> split -> upsert -> finalize`
- `rag_delete_graph`
  - 删除图
  - 步骤为 `create_delete_job -> collect targets -> delete -> finalize`
- `rag_reindex_graph`
  - 重建图
  - 先解析已有文档的可重放来源，再复用入库主链
- `rag_admin_graph`
  - 后台读模型图
  - 提供文档中心和任务中心查询

### 查询链路

查询相关能力主要位于：

- `RetrievalService`
  - 查询分析
  - 查询改写
  - 向量检索
  - 当真实依赖缺失时提供离线 fallback hits
- `RerankService`
  - 优先使用 Hugging Face cross-encoder
  - 不可用时退回词面重排
- `AnswerService`
  - 优先使用 DeepSeek 生成答案
  - 支持流式生成
  - 无模型时退回骨架占位答案
- `ConversationService`
  - 抽取最新用户问题
  - 组织最近对话上下文
  - 对明显可由近期记忆直接回答的问题，绕过知识库检索

后端流式聊天还会显式返回：

- `metadata`
  - 通知当前 `thread_id`
- `custom`
  - 阶段事件、问题分析结果、检索结果
- `messages`
  - 兼容 assistant-ui 的 `AIMessageChunk`
- `values`
  - 最终完整消息状态

最终助手消息会持久化这些附加信息：

- `citations`
- `retrieval_hits`
- `turn_trace`
- reasoning 摘要

因此历史会话回放时仍然能恢复单轮轨迹。

### 入库链路

入库的主要职责分散在以下模块：

- `DocumentSourceStoreService`
  - 统一准备来源
  - 支持本地文件、目录、URL、Base64 上传内容
  - 可将文件复制到受控目录
  - 可选同步到 `MinIO`
- `DocumentParserService`
  - 支持文本、结构化文本、PDF、Word、PPT、Excel
  - 对图片/音频/视频生成占位文本并保留元数据
- `DocumentSourceService`
  - 负责原始来源、可重放来源、路径映射、公开元数据清洗
- `IngestionService`
  - 负责加载、规范化、切块、向量写入、旧 chunk 删除
- `IngestApplicationService`
  - 负责把源文件处理、PostgreSQL 登记、Milvus 写入和任务状态串成一个用例

当前支持的来源模式包括：

- 本地文件
- 本地目录
- URL 单页抓取
- URL 递归抓取
- Base64 上传内容
- `memory://` 与 `text://` 调试来源

其中 URL 递归抓取不是把整站压成单文档，而是：

- 每个页面生成独立文档
- 保留 `crawl_root_uri`
- 保留 `page_url`
- 保留 `page_route`
- 保留递归配置元数据

### 删除与重建

- `DeleteApplicationService`
  - 先创建 `delete_job`
  - 再从 `chunk_manifest` 收集已有 chunk id
  - 删除 Milvus 数据
  - 回写文档、版本、manifest 与任务状态
- `ReindexApplicationService`
  - 先读取当前文档主记录
  - 优先恢复 `replay_source_uri`
  - 必要时从 MinIO 恢复本地可重放文件
  - 然后复用入库链路，并固定原有 `document_id`

### 后台读模型与页面契约

后台查询分为两层：

- `PostgresReadRepository`
  - 负责分页、排序、筛选、详情聚合
- `AdminApplicationService`
  - 通过显式 handler map 分发 `operation`
  - 未注册操作会返回显式错误，而不是静默回退

后端还提供了稳定的页面契约：

- `document_list`
- `document_detail`
- `ingest_job`
- `delete_job`

这些 contract 会描述：

- 查询参数
- 过滤项
- 排序项
- 表格列
- 详情字段
- 统计卡
- tabs / sections

前端管理台实际就是围绕这些 contract 渲染，不再手写大量重复字段。

## 数据模型

`PostgreSQL` 当前主要表包括：

- `assistant_thread`
- `assistant_message`
- `ingest_job`
- `delete_job`
- `document`
- `document_version`
- `document_source_storage`
- `chunk_manifest`

各表大致分工：

- `assistant_*`
  - 聊天线程和历史消息
- `document`
  - 文档主记录与当前版本指针
- `document_version`
  - 文档版本历史
- `document_source_storage`
  - 源文件原始地址、可重放地址、备份位置、对象存储同步状态
- `ingest_job / delete_job`
  - 后台任务追踪
- `chunk_manifest`
  - chunk 与版本的映射、生命周期状态、删除归档状态

## 运行方式

### 1. 启动基础设施

在 `server/` 下准备本地依赖：

```bash
docker compose up -d
```

默认包含：

- `postgres`
- `milvus`
- `etcd`
- `minio`

### 2. 配置后端环境变量

复制：

```bash
cp server/.env.example server/.env
```

至少关注这些配置：

- `DEEPSEEK_API_KEY`
- `MILVUS_URI`
- `MILVUS_COLLECTION`
- `EMBEDDING_MODEL_NAME`
- `RERANKER_MODEL_NAME`
- `POSTGRES_DSN`
- `SOURCE_STORAGE_BACKEND`

### 3. 启动后端

```bash
conda run -n mbs python -m uvicorn agent.compat_api:app --app-dir server/src --host 127.0.0.1 --port 2024
```

或进入 `server/` 后执行：

```bash
conda run -n mbs python -m uvicorn agent.compat_api:app --app-dir src --host 127.0.0.1 --port 2024
```

### 4. 配置前端环境变量

在 `client/.env.local` 中至少配置：

```bash
LANGCHAIN_API_KEY=
LANGGRAPH_API_URL=http://127.0.0.1:2024
NEXT_PUBLIC_LANGGRAPH_API_URL=http://127.0.0.1:3000/api
NEXT_PUBLIC_LANGGRAPH_ASSISTANT_ID=assistant
NEXT_PUBLIC_LANGGRAPH_ADMIN_ID=rag_admin
NEXT_PUBLIC_LANGGRAPH_INGEST_ID=rag_ingest
NEXT_PUBLIC_LANGGRAPH_DELETE_ID=rag_delete
NEXT_PUBLIC_LANGGRAPH_REINDEX_ID=rag_reindex
```

### 5. 启动前端

```bash
cd client
npm install
npm run dev
```

打开 [http://localhost:3000](http://localhost:3000) 即可。

## 测试覆盖

当前 `server/tests/` 已覆盖以下重点：

- 图级集成测试
  - `assistant_graph`
  - `rag_query_graph`
  - `rag_ingest_graph`
  - `rag_delete_graph`
  - `rag_reindex_graph`
  - `rag_admin_graph`
- 服务级与仓储级单测
  - `AdminApplicationService`
  - `DocumentParserService`
  - `DocumentSourceService`
  - `DocumentSourceStoreService`
  - `IngestionService`
  - `DeleteApplicationService`
  - `PostgresRepositoryBase`
  - `PostgresReadRepository`

前端当前没有看到独立测试目录，主要依赖分层设计、契约收敛与联调验证。

## 当前阶段判断

从代码现状来看，这个项目已经具备：

- 可运行的前后端联调链路
- 查询、入库、删除、重建、后台查询五类核心能力
- 线程、文档、版本、任务、chunk 的持久化追踪
- 基于 contract 的前后端边界
- 离线 fallback，方便在模型或向量环境不完整时先调通流程

同时也保留了明显的“第一阶段骨架”特征：

- 仍偏向单知识库、单租户场景
- 管理台能力已经成型，但还不是生产级权限/审计系统
- 模型、检索与重排具备真实接入位，但还缺更完整的评测与运维能力

## 建议优先阅读

- `client/README.md`
- `client/前端架构规范文档.md`
- `server/README.md`
- `server/后端架构规范文档.md`
- `server/RAG_项目架构设计文档.md`
