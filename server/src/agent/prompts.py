"""Prompt definitions used by the RAG services."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate


CONVERSATION_MEMORY_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "你是会话记忆助手。请只根据最近会话历史回答当前问题。"
                "如果最近会话历史已经足够回答，就直接给出简洁答案。"
                "如果仍然无法回答，必须只返回 __NEED_KB__，不要输出任何其他内容。"
            ),
        ),
        (
            "human",
            "最近会话历史：\n{conversation_context}\n\n当前问题：\n{question}",
        ),
    ]
)


QUERY_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "你是 RAG 查询分析器。请根据用户问题判断其检索意图，并输出结构化结果。"
                "intent 只能从 faq、knowledge_qa、comparison、multi_hop 中选择。"
                "top_k 只返回正整数。"
                "如果当前问题明显依赖前文指代、追问或省略信息，请结合会话历史一起判断。"
            ),
        ),
        (
            "human",
            "最近会话历史：\n{conversation_context}\n\n请分析这个问题：\n{question}",
        ),
    ]
)


QUERY_REWRITE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "你是知识库检索优化助手。请在不改变用户原意的前提下，将问题改写成更适合"
                "向量检索的查询。若当前问题依赖前文，请把必要的上下文补全进改写结果。"
                "只返回改写结果，不要解释。"
            ),
        ),
        ("human", "最近会话历史：\n{conversation_context}\n\n当前问题：\n{question}"),
    ]
)


ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "你是企业知识库问答助手。你只能根据给定上下文回答问题。"
                "这里的上下文同时包括最近会话历史和知识库检索结果。"
                "如果上下文不足，请明确说明不知道，不要编造。"
                "回答尽量准确、简洁，并优先引用上下文中的事实。"
                "如果当前问题是对前文的追问，请结合最近会话历史理解用户真正想问的对象和范围。"
            ),
        ),
        (
            "human",
            "问题：{question}\n\n最近会话历史：\n{conversation_context}\n\n知识库检索上下文：\n{context}\n\n请直接给出最终回答。",
        ),
    ]
)


def format_retrieval_context(hits: list[dict]) -> str:
    """Format retrieval hits into a prompt-friendly context string."""

    blocks: list[str] = []
    for index, hit in enumerate(hits, start=1):
        metadata = hit.get("metadata", {})
        title = metadata.get("title") or metadata.get("source_uri") or "unknown"
        blocks.append(
            "\n".join(
                [
                    f"[Source {index}]",
                    f"title: {title}",
                    f"document_id: {hit.get('document_id', '')}",
                    f"chunk_id: {hit.get('chunk_id', '')}",
                    hit.get("content", ""),
                ]
            )
        )
    return "\n\n".join(blocks)
