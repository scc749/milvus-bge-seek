This is the [assistant-ui](https://github.com/assistant-ui/assistant-ui) starter project for langgraph.

当前项目联调时，前端不直接连接官方 LangGraph Server，而是通过 Next.js 代理访问后端兼容 API。

架构规范请优先参考：

- `前端架构规范文档.md`

## Getting Started

First, add your local proxy and backend compat API settings to `.env.local`:

```
LANGCHAIN_API_KEY=
LANGGRAPH_API_URL=http://127.0.0.1:2024
NEXT_PUBLIC_LANGGRAPH_API_URL=http://127.0.0.1:3000/api
NEXT_PUBLIC_LANGGRAPH_ASSISTANT_ID=assistant
NEXT_PUBLIC_LANGGRAPH_ADMIN_ID=rag_admin
NEXT_PUBLIC_LANGGRAPH_INGEST_ID=rag_ingest
NEXT_PUBLIC_LANGGRAPH_DELETE_ID=rag_delete
NEXT_PUBLIC_LANGGRAPH_REINDEX_ID=rag_reindex
```

This workspace now includes:

- `/assistant`
  - assistant-ui chat experience backed by the `assistant` graph
- `/documents`
  - document center backed by `rag_admin` + `rag_ingest`
- `/documents/[documentId]`
  - document detail, version list, delete and reindex actions
- `/jobs/ingest`
  - ingest task center
- `/jobs/delete`
  - delete task center

Then, start the backend compat API in `server` first:

```bash
conda run -n mbs python -m uvicorn agent.compat_api:app --app-dir src --host 127.0.0.1 --port 2024
```

After that, run the frontend development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

The root page now redirects to `/assistant`, and all management pages are routed under the shared console layout.

Current request path:

- browser -> `http://127.0.0.1:3000`
- Next proxy -> `/api/compat/*`
- backend compat API -> `http://127.0.0.1:2024`

Current validated pages:

- `/assistant`
- `/documents`
- `/documents/[documentId]`
- `/jobs/ingest`
- `/jobs/delete`
