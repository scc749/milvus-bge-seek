"""Application service behind the local FastAPI compat layer."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import uuid4

from agent.repositories.assistant_thread_repository import AssistantThreadRepository
from agent.repositories.postgres_registry_repository import PostgresRegistryRepository
from agent.services.answer_service import AnswerService, RagResponseModel
from agent.services.conversation_service import ConversationService
from agent.services.rerank_service import RerankService
from agent.services.retrieval_service import QueryAnalysisModel, RetrievalService


class AsyncGraphInvoker(Protocol):
    """Protocol for compiled LangGraph objects used by the compat layer."""

    async def ainvoke(self, input: dict[str, Any]) -> dict[str, Any]:
        """Invoke a compiled graph asynchronously."""


@dataclass
class CompatApplicationService:
    """Expose graph-backed operations in a frontend-friendly shape."""

    assistant_graph: AsyncGraphInvoker
    admin_graph: AsyncGraphInvoker
    ingest_graph: AsyncGraphInvoker
    delete_graph: AsyncGraphInvoker
    reindex_graph: AsyncGraphInvoker
    conversation_service: ConversationService
    retrieval_service: RetrievalService
    rerank_service: RerankService
    answer_service: AnswerService
    assistant_thread_repository: AssistantThreadRepository
    postgres_registry_repository: PostgresRegistryRepository

    def create_thread(self) -> dict[str, str]:
        """Create a new assistant conversation thread."""

        thread = self.assistant_thread_repository.create_thread()
        return {"thread_id": thread["thread_id"]}

    def list_threads(self) -> dict[str, object]:
        """Return persisted thread metadata for sidebar/history rendering."""

        return {"threads": self.assistant_thread_repository.list_threads()}

    def get_thread(self, thread_id: str) -> dict[str, object] | None:
        """Load a stored thread for assistant-ui."""

        return self.assistant_thread_repository.get_thread(thread_id)

    def delete_thread(self, thread_id: str) -> None:
        """Delete a persisted thread and its messages."""

        self.assistant_thread_repository.delete_thread(thread_id)

    def update_thread(
        self,
        *,
        thread_id: str,
        title: str | None = None,
        status: str | None = None,
    ) -> dict[str, object] | None:
        """Update thread metadata."""

        return self.assistant_thread_repository.update_thread(
            thread_id,
            title=title,
            status=status,
        )

    async def assistant_chat(
        self,
        *,
        thread_id: str | None,
        message: str,
    ) -> dict[str, object]:
        """Run one assistant turn through the message-based assistant graph."""

        final_payload: dict[str, object] | None = None
        async for event in self.assistant_chat_stream(thread_id=thread_id, message=message):
            if event.get("event") == "values":
                payload = event.get("data")
                if isinstance(payload, dict):
                    final_payload = payload
        if final_payload is None:
            raise RuntimeError("Assistant stream finished without final state.")
        return {
            "thread_id": final_payload.get("thread_id"),
            "answer": self.conversation_service.extract_latest_assistant_message(
                final_payload.get("messages") or []
            ),
            "citations": final_payload.get("citations") or [],
            "messages": final_payload.get("messages") or [],
        }

    async def assistant_chat_stream(
        self,
        *,
        thread_id: str | None,
        message: str,
    ):
        """Stream assistant turn progress, partial answer text, and final state."""

        thread = (
            self.assistant_thread_repository.get_thread(thread_id)
            if thread_id
            else None
        )
        if thread is None:
            thread = self.assistant_thread_repository.create_thread()
            thread = self.assistant_thread_repository.get_thread(thread["thread_id"])
        if thread is None:
            raise RuntimeError("Unable to create or load assistant thread.")

        effective_thread_id = str(thread["thread_id"])
        history = list(thread.get("messages") or [])
        messages = self.conversation_service.append_user_message(history, message)
        conversation_context = self.conversation_service.format_recent_history(
            history,
            max_messages=6,
        )

        yield {"event": "metadata", "data": {"thread_id": effective_thread_id}}
        yield {
            "event": "custom",
            "data": {
                "type": "stage",
                "stage": "analysis",
                "status": "running",
                "label": "问题分析中",
            },
        }

        direct_memory_answer = self.conversation_service.answer_from_recent_history(
            message,
            history,
            max_messages=6,
        )

        if direct_memory_answer:
            analysis = self.retrieval_service.analyze_query(
                message,
                conversation_context=conversation_context,
            )
            rewritten_query = message
            yield {
                "event": "custom",
                "data": {
                    "type": "analysis",
                    "stage": "analysis",
                    "status": "completed",
                    "label": "问题分析完成",
                    "intent": analysis.intent,
                    "top_k": analysis.top_k,
                    "need_rewrite": False,
                    "need_rerank": False,
                    "rewritten_query": rewritten_query,
                },
            }
            yield {
                "event": "custom",
                "data": {
                    "type": "retrieval",
                    "stage": "retrieval",
                    "status": "completed",
                    "label": "已基于当前会话上下文直接回答，无需检索知识库",
                    "query": rewritten_query,
                    "total_hits": 0,
                    "matched_documents": 0,
                    "items": [],
                },
            }
            yield {
                "event": "custom",
                "data": {
                    "type": "stage",
                    "stage": "generation",
                    "status": "running",
                    "label": "答案生成中",
                },
            }
            assistant_message_id = str(uuid4())
            for char in direct_memory_answer:
                yield {
                    "event": "messages",
                    "data": [
                        {
                            "id": assistant_message_id,
                            "type": "AIMessageChunk",
                            "content": char,
                        },
                        {
                            "run_attempt": 1,
                        },
                    ],
                }
            final_response = RagResponseModel(answer=direct_memory_answer, citations=[])
            assistant_message = self._build_assistant_message(
                message_id=assistant_message_id,
                message=final_response.answer,
                analysis=analysis,
                rewritten_query=rewritten_query,
                hits=[],
                citations=[],
            )
            final_messages = [*messages, assistant_message]
            persisted_thread = self.assistant_thread_repository.save_thread_messages(
                effective_thread_id,
                final_messages,
            )
            if persisted_thread is None:
                persisted_thread = {
                    "thread_id": effective_thread_id,
                    "messages": final_messages,
                }
            yield {
                "event": "custom",
                "data": {
                    "type": "stage",
                    "stage": "generation",
                    "status": "completed",
                    "label": "答案生成完成",
                },
            }
            yield {
                "event": "values",
                "data": {
                    "thread_id": effective_thread_id,
                    "messages": persisted_thread.get("messages") or final_messages,
                    "citations": [],
                },
            }
            return

        analysis = self.retrieval_service.analyze_query(
            message,
            conversation_context=conversation_context,
        )
        rewritten_query = self.retrieval_service.rewrite_query(
            message,
            enable_rewrite=analysis.need_rewrite,
            conversation_context=conversation_context,
        )
        yield {
            "event": "custom",
            "data": {
                "type": "analysis",
                "stage": "analysis",
                "status": "completed",
                "label": "问题分析完成",
                "intent": analysis.intent,
                "top_k": analysis.top_k,
                "need_rewrite": analysis.need_rewrite,
                "need_rerank": analysis.need_rerank,
                "rewritten_query": rewritten_query,
            },
        }

        yield {
            "event": "custom",
            "data": {
                "type": "stage",
                "stage": "retrieval",
                "status": "running",
                "label": "知识检索中",
                "query": rewritten_query,
            },
        }
        hits = self.retrieval_service.retrieve(rewritten_query, analysis.top_k)
        reranked_hits = (
            self.rerank_service.rerank(message, hits, analysis.top_k)
            if analysis.need_rerank
            else hits
        )
        yield {
            "event": "custom",
            "data": {
                "type": "retrieval",
                "stage": "retrieval",
                "status": "completed",
                "label": "知识检索完成",
                "query": rewritten_query,
                "total_hits": len(reranked_hits),
                "matched_documents": self._count_unique_documents(reranked_hits),
                "items": [self._build_source_item(hit) for hit in reranked_hits],
            },
        }

        yield {
            "event": "custom",
            "data": {
                "type": "stage",
                "stage": "generation",
                "status": "running",
                "label": "答案生成中",
            },
        }

        final_response: RagResponseModel | None = None
        assistant_message_id = str(uuid4())
        async for chunk in self.answer_service.stream_generate(
            message,
            reranked_hits,
            conversation_context=conversation_context,
        ):
            if chunk.get("type") == "chunk":
                yield {
                    "event": "messages",
                    "data": [
                        {
                            "id": assistant_message_id,
                            "type": "AIMessageChunk",
                            "content": chunk.get("text", ""),
                        },
                        {
                            "run_attempt": 1,
                        }
                    ],
                }
            elif chunk.get("type") == "final":
                final_response = chunk.get("response")

        if final_response is None:
            raise RuntimeError("Assistant generation finished without final response.")

        assistant_message = self._build_assistant_message(
            message_id=assistant_message_id,
            message=final_response.answer,
            analysis=analysis,
            rewritten_query=rewritten_query,
            hits=reranked_hits,
            citations=[citation.model_dump() for citation in final_response.citations],
        )
        final_messages = [*messages, assistant_message]
        persisted_thread = self.assistant_thread_repository.save_thread_messages(
            effective_thread_id,
            final_messages,
        )
        if persisted_thread is None:
            persisted_thread = {
                "thread_id": effective_thread_id,
                "messages": final_messages,
            }

        yield {
            "event": "custom",
            "data": {
                "type": "stage",
                "stage": "generation",
                "status": "completed",
                "label": "答案生成完成",
            },
        }
        yield {
            "event": "values",
            "data": {
                "thread_id": effective_thread_id,
                "messages": persisted_thread.get("messages") or final_messages,
                "citations": [citation.model_dump() for citation in final_response.citations],
            },
        }

    async def admin_page_contract(self, page_name: str) -> dict[str, object]:
        """Return an admin page contract."""

        result = await self.admin_graph.ainvoke(
            {
                "operation": "get_page_contract",
                "page_name": page_name,
            }
        )
        return result.get("result", {})

    async def admin_query(
        self,
        operation: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        """Return admin read-model data for a specific operation."""

        result = await self.admin_graph.ainvoke({"operation": operation, **payload})
        return result.get("result", {})

    async def ingest_document(self, payload: dict[str, Any]) -> dict[str, object]:
        """Submit an ingest job and continue the graph in the background."""

        source_uri = payload.get("source_uri")
        source_name = payload.get("source_name")
        display_source = str(source_uri or source_name or "").strip() or None
        job_id = self.postgres_registry_repository.create_ingest_job(display_source)

        if not job_id:
            raise RuntimeError("创建入库任务失败。")

        def _run_ingest() -> None:
            try:
                import asyncio

                async def _invoke() -> None:
                    await self.ingest_graph.ainvoke(
                        {
                            **payload,
                            "ingest_job_id": job_id,
                        }
                    )

                asyncio.run(_invoke())
            except Exception as exc:
                try:
                    self.postgres_registry_repository.finalize_ingest_job(
                        ingest_job_id=job_id,
                        chunks=[],
                        upserted_count=0,
                        status="failed",
                        error=str(exc),
                    )
                except Exception:
                    return

        threading.Thread(
            target=_run_ingest,
            name=f"ingest-job-{job_id}",
            daemon=True,
        ).start()

        return {
            "ingest_job_id": job_id,
            "source_uri": display_source,
            "source_name": source_name,
            "status": "created",
            "message": "入库任务已提交，后台正在处理中。",
        }

    async def delete_document(self, payload: dict[str, Any]) -> dict[str, object]:
        """Run the delete graph and normalize the response envelope."""

        result = await self.delete_graph.ainvoke(payload)
        return result.get("result", {})

    async def reindex_document(self, payload: dict[str, Any]) -> dict[str, object]:
        """Run the reindex graph and normalize the response envelope."""

        result = await self.reindex_graph.ainvoke(payload)
        return result.get("result", {})

    def _build_assistant_message(
        self,
        *,
        message_id: str,
        message: str,
        analysis: QueryAnalysisModel,
        rewritten_query: str,
        hits: list[dict[str, Any]],
        citations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        turn_trace = self._build_turn_trace(
            analysis=analysis,
            rewritten_query=rewritten_query,
            hits=hits,
        )
        reasoning_lines = [
            f"- 问题意图：{analysis.intent}",
            f"- 检索范围：Top-{analysis.top_k}",
            f"- 检索命中：{len(hits)} 个知识片段，涉及 {self._count_unique_documents(hits)} 篇文档",
        ]
        if rewritten_query != message:
            reasoning_lines.append(f"- 检索改写：{rewritten_query}")
        custom_metadata = {
            "citations": citations,
            "retrieval_hits": [self._build_source_item(hit) for hit in hits],
            "turn_trace": turn_trace,
        }
        return {
            "id": message_id,
            "role": "assistant",
            "type": "ai",
            "content": message,
            "additional_kwargs": {
                "metadata": custom_metadata,
                "reasoning": {
                    "type": "reasoning",
                    "summary": [
                        {
                            "type": "summary_text",
                            "text": "\n".join(reasoning_lines),
                        }
                    ],
                }
            },
            "response_metadata": {
                **custom_metadata,
            },
        }

    def _build_turn_trace(
        self,
        *,
        analysis: QueryAnalysisModel,
        rewritten_query: str,
        hits: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "analysis": {
                "status": "completed",
                "label": "问题分析完成",
                "intent": analysis.intent,
                "top_k": analysis.top_k,
                "need_rewrite": analysis.need_rewrite,
                "need_rerank": analysis.need_rerank,
                "rewritten_query": rewritten_query,
            },
            "retrieval": {
                "status": "completed",
                "label": "知识检索完成",
                "query": rewritten_query,
                "total_hits": len(hits),
                "matched_documents": self._count_unique_documents(hits),
                "items": [self._build_source_item(hit) for hit in hits],
            },
            "generation": {
                "status": "completed",
                "label": "答案生成完成",
            },
        }

    def _build_source_item(self, hit: dict[str, Any]) -> dict[str, Any]:
        metadata = hit.get("metadata", {}) or {}
        return {
            "document_id": hit.get("document_id"),
            "chunk_id": hit.get("chunk_id"),
            "title": metadata.get("title") or hit.get("document_id"),
            "source_uri": metadata.get("source_uri"),
            "score": hit.get("rerank_score", hit.get("score")),
            "snippet": str(hit.get("content", ""))[:200],
        }

    def _count_unique_documents(self, hits: list[dict[str, Any]]) -> int:
        document_ids = {
            str(hit.get("document_id"))
            for hit in hits
            if hit.get("document_id")
        }
        return len(document_ids)
