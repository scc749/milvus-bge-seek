"""Repository for persisted assistant thread metadata and messages."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from agent.repositories.postgres_base import PostgresRepositoryBase


class AssistantThreadRepository(PostgresRepositoryBase):
    """Persist assistant threads and ordered messages in PostgreSQL."""

    def create_thread(self, title: str = "新对话") -> dict[str, Any]:
        thread_id = str(uuid4())
        with self._transaction() as conn:
            if conn is None:
                return {
                    "thread_id": thread_id,
                    "title": title,
                    "status": "regular",
                }
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into assistant_thread (
                        thread_id, title, status, created_at, updated_at
                    )
                    values (%s, %s, 'regular', now(), now())
                    """,
                    (thread_id, title),
                )
        return {
            "thread_id": thread_id,
            "title": title,
            "status": "regular",
        }

    def list_threads(self) -> list[dict[str, Any]]:
        conn = self._connect()
        if conn is None:
            return []
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select
                        t.thread_id,
                        t.title,
                        t.status,
                        t.updated_at,
                        coalesce(m.content_text, '') as last_message
                    from assistant_thread t
                    left join lateral (
                        select content_text
                        from assistant_message
                        where thread_id = t.thread_id
                        order by sequence_number desc
                        limit 1
                    ) m on true
                    order by t.updated_at desc
                    """
                )
                rows = cur.fetchall()
        finally:
            conn.close()
        return [
            {
                "thread_id": row[0],
                "title": row[1],
                "status": row[2],
                "updated_at": row[3].isoformat() if row[3] else None,
                "last_message": row[4],
            }
            for row in rows
        ]

    def get_thread(self, thread_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        if conn is None:
            return None
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select thread_id, title, status, created_at, updated_at
                    from assistant_thread
                    where thread_id = %s
                    """,
                    (thread_id,),
                )
                thread_row = cur.fetchone()
                if thread_row is None:
                    return None
                cur.execute(
                    """
                    select role, type, content_text, content_json, additional_kwargs_json,
                           response_metadata_json, message_id
                    from assistant_message
                    where thread_id = %s
                    order by sequence_number asc
                    """,
                    (thread_id,),
                )
                message_rows = cur.fetchall()
        finally:
            conn.close()
        return {
            "thread_id": thread_row[0],
            "title": thread_row[1],
            "status": thread_row[2],
            "created_at": thread_row[3].isoformat() if thread_row[3] else None,
            "updated_at": thread_row[4].isoformat() if thread_row[4] else None,
            "messages": [self._deserialize_message(row) for row in message_rows],
        }

    def save_thread_messages(self, thread_id: str, messages: list[dict[str, Any]]) -> dict[str, Any] | None:
        thread = self.get_thread(thread_id)
        if thread is None:
            return None
        title = self._derive_title(messages, fallback=thread.get("title") or "新对话")
        with self._transaction() as conn:
            if conn is None:
                return {
                    **thread,
                    "title": title,
                    "messages": messages,
                }
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update assistant_thread
                    set title = %s, updated_at = now()
                    where thread_id = %s
                    """,
                    (title, thread_id),
                )
                cur.execute(
                    """
                    delete from assistant_message
                    where thread_id = %s
                    """,
                    (thread_id,),
                )
                for index, message in enumerate(messages):
                    content = message.get("content", "")
                    cur.execute(
                        """
                        insert into assistant_message (
                            message_id,
                            thread_id,
                            sequence_number,
                            role,
                            type,
                            content_text,
                            content_json,
                            additional_kwargs_json,
                            response_metadata_json,
                            created_at
                        )
                        values (
                            %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, now()
                        )
                        """,
                        (
                            message.get("id") or str(uuid4()),
                            thread_id,
                            index,
                            message.get("role"),
                            message.get("type"),
                            content if isinstance(content, str) else "",
                            json.dumps(content if isinstance(content, list) else []),
                            json.dumps(message.get("additional_kwargs") or {}),
                            json.dumps(message.get("response_metadata") or {}),
                        ),
                    )
        return self.get_thread(thread_id)

    def delete_thread(self, thread_id: str) -> None:
        with self._transaction() as conn:
            if conn is None:
                return
            with conn.cursor() as cur:
                cur.execute(
                    """
                    delete from assistant_thread
                    where thread_id = %s
                    """,
                    (thread_id,),
                )

    def update_thread(
        self,
        thread_id: str,
        *,
        title: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any] | None:
        thread = self.get_thread(thread_id)
        if thread is None:
            return None
        next_title = title or thread.get("title") or "新对话"
        next_status = status or thread.get("status") or "regular"
        with self._transaction() as conn:
            if conn is None:
                return {
                    **thread,
                    "title": next_title,
                    "status": next_status,
                }
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update assistant_thread
                    set title = %s, status = %s, updated_at = now()
                    where thread_id = %s
                    """,
                    (next_title, next_status, thread_id),
                )
        return self.get_thread(thread_id)

    def _derive_title(self, messages: list[dict[str, Any]], fallback: str) -> str:
        for message in messages:
            if message.get("type") != "human":
                continue
            content = message.get("content", "")
            if isinstance(content, str):
                title = " ".join(content.split()).strip()
                if title:
                    return title[:60]
            if isinstance(content, list):
                text_parts = [
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict) and item.get("type") == "text"
                ]
                title = " ".join("".join(text_parts).split()).strip()
                if title:
                    return title[:60]
        return fallback

    def _deserialize_message(self, row: tuple[Any, ...]) -> dict[str, Any]:
        role, message_type, content_text, content_json, additional_kwargs, response_metadata, message_id = row
        content: Any = content_text
        if content_json:
            try:
                parsed_content = json.loads(content_json)
                if parsed_content:
                    content = parsed_content
            except Exception:
                pass
        return {
            "id": message_id,
            "role": role,
            "type": message_type,
            "content": content,
            "additional_kwargs": self._parse_json(additional_kwargs),
            "response_metadata": self._parse_json(response_metadata),
        }

    def _parse_json(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if isinstance(value, str) and value:
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                return {}
        return {}
