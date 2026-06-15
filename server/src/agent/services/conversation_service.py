"""Helpers for adapting LangGraph state to assistant-ui message flows."""

from __future__ import annotations

import re
from typing import Any

from langchain_core.output_parsers import StrOutputParser

from agent.components.factories import create_chat_model
from agent.prompts import CONVERSATION_MEMORY_PROMPT


class ConversationService:
    """Normalize incoming message state and build assistant-ui-friendly outputs."""

    def extract_latest_user_query(self, messages: list[dict[str, Any]] | None) -> str:
        """Extract the most recent human message content from a LangChain-like message list."""

        for message in reversed(messages or []):
            message_type = message.get("type") or message.get("role")
            if message_type not in {"human", "user"}:
                continue
            return self._coerce_content_to_text(message.get("content"))
        return ""

    def append_assistant_message(
        self,
        messages: list[dict[str, Any]] | None,
        answer: str,
        citations: list[dict[str, Any]] | None = None,
        debug: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Append a normalized assistant message to the thread state."""

        return [
            *(messages or []),
            {
                "type": "ai",
                "content": answer,
                "additional_kwargs": {
                    "citations": citations or [],
                    "debug": debug or {},
                },
                "response_metadata": {},
            },
        ]

    def append_user_message(
        self,
        messages: list[dict[str, Any]] | None,
        content: str,
    ) -> list[dict[str, Any]]:
        """Append a normalized human message to the thread state."""

        return [
            *(messages or []),
            {
                "type": "human",
                "content": content,
            },
        ]

    def extract_latest_assistant_message(
        self,
        messages: list[dict[str, Any]] | None,
    ) -> str:
        """Extract the latest assistant response text from a message list."""

        for message in reversed(messages or []):
            message_type = message.get("type") or message.get("role")
            if message_type not in {"ai", "assistant"}:
                continue
            return self._coerce_content_to_text(message.get("content"))
        return ""

    def format_recent_history(
        self,
        messages: list[dict[str, Any]] | None,
        *,
        max_messages: int = 6,
    ) -> str:
        """Format recent user/assistant turns into plain text for downstream prompts."""

        normalized: list[str] = []
        for message in messages or []:
            message_type = message.get("type") or message.get("role")
            if message_type not in {"human", "user", "ai", "assistant"}:
                continue
            content = self._coerce_content_to_text(message.get("content")).strip()
            if not content:
                continue
            speaker = "用户" if message_type in {"human", "user"} else "助手"
            normalized.append(f"{speaker}: {content}")
        if not normalized:
            return ""
        return "\n".join(normalized[-max_messages:])

    def answer_from_recent_history(
        self,
        question: str,
        messages: list[dict[str, Any]] | None,
        *,
        max_messages: int = 6,
    ) -> str | None:
        """Return an answer directly from recent conversation memory when possible."""

        conversation_context = self.format_recent_history(
            messages,
            max_messages=max_messages,
        )
        if not conversation_context.strip():
            return None

        llm = create_chat_model()
        if llm is not None:
            try:
                chain = CONVERSATION_MEMORY_PROMPT | llm | StrOutputParser()
                answer = chain.invoke(
                    {
                        "question": question,
                        "conversation_context": conversation_context,
                    }
                ).strip()
                if answer and answer != "__NEED_KB__":
                    return answer
            except Exception:
                pass

        if any(token in question for token in ["叫什么", "名字", "叫啥", "是谁"]):
            for message in reversed(messages or []):
                message_type = message.get("type") or message.get("role")
                if message_type not in {"human", "user"}:
                    continue
                content = self._coerce_content_to_text(message.get("content"))
                match = re.search(r"(?:叫|名字叫)([^，。！？\s]{1,16})", content)
                if match:
                    return match.group(1)
        return None

    def _coerce_content_to_text(self, content: Any) -> str:
        """Normalize different message content shapes into plain text."""

        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "\n".join(part for part in parts if part)
        return ""
