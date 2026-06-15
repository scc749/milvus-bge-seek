"""Business service for retrieval and query preparation."""

from __future__ import annotations

from pydantic import BaseModel
from langchain_core.output_parsers import StrOutputParser

from agent.components.factories import create_chat_model, create_retriever
from agent.config import get_settings
from agent.prompts import QUERY_ANALYSIS_PROMPT, QUERY_REWRITE_PROMPT


class QueryAnalysisModel(BaseModel):
    """Structured query analysis used before retrieval."""

    intent: str = "knowledge_qa"
    need_rewrite: bool = True
    need_rerank: bool = True
    need_metadata_filter: bool = False
    top_k: int = 8


class RetrievalService:
    """Provide query analysis, rewriting, and retrieval orchestration."""

    def analyze_query(
        self,
        question: str,
        *,
        conversation_context: str = "",
    ) -> QueryAnalysisModel:
        """Infer a retrieval strategy with LLM fallback to heuristics."""

        llm = create_chat_model()
        if llm is not None:
            try:
                analysis_chain = QUERY_ANALYSIS_PROMPT | llm.with_structured_output(QueryAnalysisModel)
                result = analysis_chain.invoke(
                    {
                        "question": question,
                        "conversation_context": conversation_context or "无",
                    }
                )
                if isinstance(result, QueryAnalysisModel):
                    return result
            except Exception:
                pass

        lowered = question.lower()
        intent = "knowledge_qa"
        if any(keyword in lowered for keyword in ("compare", "difference", "区别", "对比")):
            intent = "comparison"
        elif any(keyword in lowered for keyword in ("步骤", "how", "why", "原因", "流程")):
            intent = "multi_hop"
        return QueryAnalysisModel(
            intent=intent,
            need_rewrite=True,
            need_rerank=True,
            need_metadata_filter=False,
            top_k=get_settings().retrieval_top_k,
        )

    def rewrite_query(
        self,
        question: str,
        *,
        enable_rewrite: bool = True,
        conversation_context: str = "",
    ) -> str:
        """Return a retrieval-friendly query string."""

        if not enable_rewrite:
            return question
        llm = create_chat_model()
        if llm is not None:
            try:
                rewrite_chain = QUERY_REWRITE_PROMPT | llm | StrOutputParser()
                rewritten = rewrite_chain.invoke(
                    {
                        "question": question,
                        "conversation_context": conversation_context or "无",
                    }
                ).strip()
                if rewritten:
                    return rewritten
            except Exception:
                pass
        return " ".join(question.split())

    def retrieve(self, question: str, top_k: int) -> list[dict]:
        """Retrieve candidate chunks from backend or fallback set."""

        retriever = create_retriever({"k": top_k})
        if retriever is None:
            return self._build_fallback_hits(question, top_k)

        try:
            docs = retriever.invoke(question)
        except Exception:
            return self._build_fallback_hits(question, top_k)
        hits: list[dict] = []
        for index, doc in enumerate(docs):
            hits.append(
                {
                    "chunk_id": doc.metadata.get("chunk_id", f"chunk-{index}"),
                    "document_id": doc.metadata.get("document_id", f"doc-{index}"),
                    "content": doc.page_content,
                    "score": float(doc.metadata.get("score", max(top_k - index, 1))),
                    "metadata": dict(doc.metadata),
                }
            )
        return hits

    def _build_fallback_hits(self, question: str, top_k: int) -> list[dict]:
        """Return deterministic fallback hits so the skeleton runs offline."""

        return [
            {
                "chunk_id": f"fallback-{idx}",
                "document_id": "skeleton-doc",
                "content": (
                    "这是离线骨架返回的候选片段，用于展示检索、重排和生成链路。"
                    f" 当前查询是：{question}。"
                ),
                "score": float(top_k - idx),
                "metadata": {
                    "title": "Skeleton Knowledge Base",
                    "source_uri": "memory://skeleton",
                },
            }
            for idx in range(min(top_k, 3))
        ]
