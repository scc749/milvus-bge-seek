"""Nodes for the main RAG query flow."""

from __future__ import annotations

from typing import Any

from langgraph.runtime import Runtime

from agent.context import RagContext
from agent.dependencies import get_container
from agent.state import RagState


async def analyze_query(state: RagState, runtime: Runtime[RagContext]) -> dict[str, Any]:
    """Analyze the incoming query and choose a retrieval profile."""

    container = get_container()
    analysis = container.retrieval_service.analyze_query(state["user_query"])
    context = runtime.context or {}
    return {
        "analysis": analysis.model_dump(),
        "debug": {
            "assistant_id": context.get("assistant_id", "default"),
            "knowledge_base": context.get("knowledge_base", "default"),
        },
    }


async def route_query(state: RagState, runtime: Runtime[RagContext]) -> dict[str, Any]:
    """Attach routing metadata for future multi-knowledge-base support."""

    context = runtime.context or {}
    return {
        "debug": {
            **state.get("debug", {}),
            "route": {
                "knowledge_base": context.get("knowledge_base", "default"),
                "retriever_profile": context.get("retriever_profile", "default"),
            },
        }
    }


async def rewrite_query(state: RagState, runtime: Runtime[RagContext]) -> dict[str, Any]:
    """Rewrite the user query before retrieval."""

    container = get_container()
    context = runtime.context or {}
    enable_rewrite = context.get(
        "enable_query_rewrite",
        state.get("analysis", {}).get("need_rewrite", True),
    )
    rewritten_query = container.retrieval_service.rewrite_query(
        state["user_query"],
        enable_rewrite=enable_rewrite,
    )
    return {"rewritten_query": rewritten_query}


async def retrieve(state: RagState, runtime: Runtime[RagContext]) -> dict[str, Any]:
    """Retrieve candidate chunks from the vector store."""

    container = get_container()
    context = runtime.context or {}
    analysis = state.get("analysis", {})
    top_k = context.get("top_k_override") or analysis.get("top_k", 8)
    query = state.get("rewritten_query") or state["user_query"]
    hits = container.retrieval_service.retrieve(query, top_k=top_k)
    return {"candidate_chunks": hits}


async def rerank(state: RagState, runtime: Runtime[RagContext]) -> dict[str, Any]:
    """Rerank retrieved chunks before generation."""

    container = get_container()
    context = runtime.context or {}
    enable_rerank = context.get(
        "enable_rerank",
        state.get("analysis", {}).get("need_rerank", True),
    )
    if not enable_rerank:
        return {"reranked_chunks": state.get("candidate_chunks", [])}

    reranked = container.rerank_service.rerank(
        question=state["user_query"],
        hits=state.get("candidate_chunks", []),
    )
    return {"reranked_chunks": reranked}


async def generate(state: RagState, runtime: Runtime[RagContext]) -> dict[str, Any]:
    """Generate the final answer from reranked context."""

    del runtime
    container = get_container()
    hits = state.get("reranked_chunks") or state.get("candidate_chunks", [])
    response = container.answer_service.generate(state["user_query"], hits)
    return {
        "answer": response.answer,
        "citations": [citation.model_dump() for citation in response.citations],
    }


async def finalize(state: RagState, runtime: Runtime[RagContext]) -> dict[str, Any]:
    """Finalize graph output for clients."""

    context = runtime.context or {}
    debug = {
        **state.get("debug", {}),
        "response_model": context.get("response_model", "default"),
        "candidate_count": len(state.get("candidate_chunks", [])),
        "final_context_count": len(state.get("reranked_chunks", [])),
    }
    return {"debug": debug}
