import asyncio

from agent.services.compat_application_service import CompatApplicationService
from agent.services.conversation_service import ConversationService


class _FakeGraph:
    def __init__(self, result: dict[str, object]) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    async def ainvoke(self, input: dict[str, object]) -> dict[str, object]:
        self.calls.append(input)
        return self.result


def test_create_thread_persists_empty_history() -> None:
    graph = _FakeGraph({})
    service = CompatApplicationService(
        assistant_graph=graph,
        admin_graph=graph,
        ingest_graph=graph,
        delete_graph=graph,
        reindex_graph=graph,
        conversation_service=ConversationService(),
    )

    created = service.create_thread()
    thread = service.get_thread(created["thread_id"])

    assert created["thread_id"].startswith("thread_")
    assert thread == {"thread_id": created["thread_id"], "messages": []}


def test_assistant_chat_uses_message_graph_and_updates_thread() -> None:
    assistant_graph = _FakeGraph(
        {
            "messages": [
                {"type": "human", "content": "你好"},
                {"type": "ai", "content": "你好，我可以帮助你整理 RAG 架构。"},
            ],
            "citations": [{"document_id": "doc-1"}],
        }
    )
    service = CompatApplicationService(
        assistant_graph=assistant_graph,
        admin_graph=_FakeGraph({}),
        ingest_graph=_FakeGraph({}),
        delete_graph=_FakeGraph({}),
        reindex_graph=_FakeGraph({}),
        conversation_service=ConversationService(),
    )

    result = asyncio.run(service.assistant_chat(thread_id=None, message="你好"))

    assert assistant_graph.calls[0] == {
        "messages": [{"type": "human", "content": "你好"}]
    }
    assert result["answer"] == "你好，我可以帮助你整理 RAG 架构。"
    assert result["citations"] == [{"document_id": "doc-1"}]
    assert len(result["messages"]) == 2
