"""Runtime context schema for graph execution."""

from __future__ import annotations

from typing_extensions import NotRequired, TypedDict


class RagContext(TypedDict, total=False):
    """Immutable runtime context supplied with each graph invocation."""

    assistant_id: str
    knowledge_base: str
    retriever_profile: str
    response_model: str
    enable_query_rewrite: bool
    enable_rerank: bool
    top_k_override: int
    debug: bool
    tenant_id: NotRequired[str]
