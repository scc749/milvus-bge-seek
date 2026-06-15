"""LangGraph definitions for the RAG server skeleton."""

from __future__ import annotations

from langgraph.graph import StateGraph

from agent.context import RagContext
from agent.nodes.assistant_flow import append_assistant_message, capture_latest_user_query
from agent.nodes.admin_flow import fetch_admin_records, finalize_admin_records
from agent.nodes.delete_flow import (
    collect_delete_targets,
    create_delete_job,
    delete_document_chunks,
    finalize_delete,
)
from agent.nodes.ingest_flow import (
    finalize_ingestion,
    load_documents,
    normalize_documents,
    split_documents,
    upsert_documents,
)
from agent.nodes.query_flow import (
    analyze_query,
    finalize,
    generate,
    rerank,
    retrieve,
    rewrite_query,
    route_query,
)
from agent.nodes.reindex_flow import pin_document_identity, resolve_reindex_source
from agent.state import AdminState, AssistantState, DeleteState, IngestState, RagState


rag_query_graph = (
    StateGraph(RagState, context_schema=RagContext)
    .add_node("analyze_query", analyze_query)
    .add_node("route_query", route_query)
    .add_node("rewrite_query", rewrite_query)
    .add_node("retrieve", retrieve)
    .add_node("rerank", rerank)
    .add_node("generate", generate)
    .add_node("finalize", finalize)
    .add_edge("__start__", "analyze_query")
    .add_edge("analyze_query", "route_query")
    .add_edge("route_query", "rewrite_query")
    .add_edge("rewrite_query", "retrieve")
    .add_edge("retrieve", "rerank")
    .add_edge("rerank", "generate")
    .add_edge("generate", "finalize")
    .add_edge("finalize", "__end__")
    .compile(name="RAG Query Graph")
)

assistant_graph = (
    StateGraph(AssistantState, context_schema=RagContext)
    .add_node("capture_latest_user_query", capture_latest_user_query)
    .add_node("analyze_query", analyze_query)
    .add_node("route_query", route_query)
    .add_node("rewrite_query", rewrite_query)
    .add_node("retrieve", retrieve)
    .add_node("rerank", rerank)
    .add_node("generate", generate)
    .add_node("finalize", finalize)
    .add_node("append_assistant_message", append_assistant_message)
    .add_edge("__start__", "capture_latest_user_query")
    .add_edge("capture_latest_user_query", "analyze_query")
    .add_edge("analyze_query", "route_query")
    .add_edge("route_query", "rewrite_query")
    .add_edge("rewrite_query", "retrieve")
    .add_edge("retrieve", "rerank")
    .add_edge("rerank", "generate")
    .add_edge("generate", "finalize")
    .add_edge("finalize", "append_assistant_message")
    .add_edge("append_assistant_message", "__end__")
    .compile(name="Assistant Query Graph")
)

rag_ingest_graph = (
    StateGraph(IngestState, context_schema=RagContext)
    .add_node("load_documents", load_documents)
    .add_node("normalize_documents", normalize_documents)
    .add_node("split_documents", split_documents)
    .add_node("upsert_documents", upsert_documents)
    .add_node("finalize_ingestion", finalize_ingestion)
    .add_edge("__start__", "load_documents")
    .add_edge("load_documents", "normalize_documents")
    .add_edge("normalize_documents", "split_documents")
    .add_edge("split_documents", "upsert_documents")
    .add_edge("upsert_documents", "finalize_ingestion")
    .add_edge("finalize_ingestion", "__end__")
    .compile(name="RAG Ingest Graph")
)

rag_delete_graph = (
    StateGraph(DeleteState, context_schema=RagContext)
    .add_node("create_delete_job", create_delete_job)
    .add_node("collect_delete_targets", collect_delete_targets)
    .add_node("delete_document_chunks", delete_document_chunks)
    .add_node("finalize_delete", finalize_delete)
    .add_edge("__start__", "create_delete_job")
    .add_edge("create_delete_job", "collect_delete_targets")
    .add_edge("collect_delete_targets", "delete_document_chunks")
    .add_edge("delete_document_chunks", "finalize_delete")
    .add_edge("finalize_delete", "__end__")
    .compile(name="RAG Delete Graph")
)

rag_reindex_graph = (
    StateGraph(IngestState, context_schema=RagContext)
    .add_node("resolve_reindex_source", resolve_reindex_source)
    .add_node("load_documents", load_documents)
    .add_node("pin_document_identity", pin_document_identity)
    .add_node("normalize_documents", normalize_documents)
    .add_node("split_documents", split_documents)
    .add_node("upsert_documents", upsert_documents)
    .add_node("finalize_ingestion", finalize_ingestion)
    .add_edge("__start__", "resolve_reindex_source")
    .add_edge("resolve_reindex_source", "load_documents")
    .add_edge("load_documents", "pin_document_identity")
    .add_edge("pin_document_identity", "normalize_documents")
    .add_edge("normalize_documents", "split_documents")
    .add_edge("split_documents", "upsert_documents")
    .add_edge("upsert_documents", "finalize_ingestion")
    .add_edge("finalize_ingestion", "__end__")
    .compile(name="RAG Reindex Graph")
)

rag_admin_graph = (
    StateGraph(AdminState, context_schema=RagContext)
    .add_node("fetch_admin_records", fetch_admin_records)
    .add_node("finalize_admin_records", finalize_admin_records)
    .add_edge("__start__", "fetch_admin_records")
    .add_edge("fetch_admin_records", "finalize_admin_records")
    .add_edge("finalize_admin_records", "__end__")
    .compile(name="RAG Admin Graph")
)

# Keep the default export assistant-ui compatible with the original template entrypoint.
graph = assistant_graph
