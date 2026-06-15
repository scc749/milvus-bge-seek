"""Business service for answer generation."""

from __future__ import annotations

from pydantic import BaseModel, Field
from langchain_core.output_parsers import StrOutputParser

from agent.components.factories import create_chat_model
from agent.prompts import ANSWER_PROMPT, format_retrieval_context


class CitationModel(BaseModel):
    """Citation model for normalized graph output."""

    document_id: str
    chunk_id: str
    title: str | None = None
    source_uri: str | None = None


class RagResponseModel(BaseModel):
    """Normalized response returned by the answer service."""

    answer: str
    citations: list[CitationModel] = Field(default_factory=list)
    debug: dict = Field(default_factory=dict)


class AnswerService:
    """Generate answers from retrieved context."""

    def _build_combined_context(
        self,
        *,
        hits: list[dict],
        conversation_context: str,
    ) -> str:
        retrieval_context = format_retrieval_context(hits) if hits else ""
        sections: list[str] = []
        if conversation_context.strip():
            sections.append(f"[Recent Conversation]\n{conversation_context.strip()}")
        if retrieval_context.strip():
            sections.append(f"[Knowledge Base]\n{retrieval_context.strip()}")
        return "\n\n".join(sections)

    def generate(
        self,
        question: str,
        hits: list[dict],
        *,
        conversation_context: str = "",
    ) -> RagResponseModel:
        """Generate an answer with DeepSeek when available, else use fallback."""

        if not hits and not conversation_context.strip():
            return RagResponseModel(answer="当前知识库中没有足够上下文来回答这个问题。")

        context = self._build_combined_context(
            hits=hits,
            conversation_context=conversation_context,
        )
        llm = create_chat_model()
        if llm is not None:
            try:
                answer_chain = ANSWER_PROMPT | llm | StrOutputParser()
                answer = answer_chain.invoke(
                    {
                        "question": question,
                        "context": context,
                        "conversation_context": conversation_context or "无",
                    }
                ).strip()
            except Exception:
                answer = ""
        else:
            answer = ""
        if not answer:
            answer = (
                "这是 RAG 骨架返回的占位答案。\n"
                f"最近会话：{conversation_context[:160] or '无'}\n"
                f"问题：{question}\n"
                "系统已经完成了查询分析、检索和重排，后续只需要把生成阶段替换为真实 DeepSeek 调用即可。\n"
                f"参考上下文摘要：{context[:280]}"
            )
        citations = [
            CitationModel(
                document_id=hit["document_id"],
                chunk_id=hit["chunk_id"],
                title=hit.get("metadata", {}).get("title"),
                source_uri=hit.get("metadata", {}).get("source_uri"),
            )
            for hit in hits
        ]
        return RagResponseModel(answer=answer, citations=citations)

    async def stream_generate(
        self,
        question: str,
        hits: list[dict],
        *,
        conversation_context: str = "",
    ):
        """Yield answer text chunks and then the normalized response."""

        if not hits and not conversation_context.strip():
            response = RagResponseModel(answer="当前知识库中没有足够上下文来回答这个问题。")
            yield {"type": "chunk", "text": response.answer}
            yield {"type": "final", "response": response}
            return

        context = self._build_combined_context(
            hits=hits,
            conversation_context=conversation_context,
        )
        citations = [
            CitationModel(
                document_id=hit["document_id"],
                chunk_id=hit["chunk_id"],
                title=hit.get("metadata", {}).get("title"),
                source_uri=hit.get("metadata", {}).get("source_uri"),
            )
            for hit in hits
        ]

        llm = create_chat_model()
        if llm is not None:
            collected = ""
            try:
                answer_chain = ANSWER_PROMPT | llm | StrOutputParser()
                async for chunk in answer_chain.astream(
                    {
                        "question": question,
                        "context": context,
                        "conversation_context": conversation_context or "无",
                    }
                ):
                    text = str(chunk or "")
                    if not text:
                        continue
                    collected += text
                    yield {"type": "chunk", "text": text}
                answer = collected.strip()
                if answer:
                    yield {
                        "type": "final",
                        "response": RagResponseModel(answer=answer, citations=citations),
                    }
                    return
            except Exception:
                pass

        answer = (
            "这是 RAG 骨架返回的占位答案。\n"
            f"最近会话：{conversation_context[:160] or '无'}\n"
            f"问题：{question}\n"
            "系统已经完成了查询分析、检索和重排，后续只需要把生成阶段替换为真实 DeepSeek 调用即可。\n"
            f"参考上下文摘要：{context[:280]}"
        )
        for char in answer:
            yield {"type": "chunk", "text": char}
        yield {
            "type": "final",
            "response": RagResponseModel(answer=answer, citations=citations),
        }
