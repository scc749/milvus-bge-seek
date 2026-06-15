import pytest
import base64

from agent import (
    assistant_graph,
    rag_admin_graph,
    rag_delete_graph,
    rag_ingest_graph,
    rag_query_graph,
    rag_reindex_graph,
)

pytestmark = pytest.mark.anyio


@pytest.mark.langsmith
async def test_assistant_graph_runs() -> None:
    inputs = {
        "messages": [
            {
                "type": "human",
                "content": "什么是 RAG 系统设计",
            }
        ]
    }
    res = await assistant_graph.ainvoke(inputs)
    assert res["messages"]
    assert res["messages"][-1]["type"] == "ai"


@pytest.mark.langsmith
async def test_rag_query_graph_runs() -> None:
    inputs = {"user_query": "什么是 RAG 系统设计"}
    res = await rag_query_graph.ainvoke(inputs)
    assert res["answer"]
    assert isinstance(res["citations"], list)


@pytest.mark.langsmith
async def test_rag_ingest_graph_runs() -> None:
    inputs = {"source_uri": "memory://test-doc"}
    res = await rag_ingest_graph.ainvoke(inputs)
    assert res["result"]["upserted_count"] >= 1
    assert "registered_version_ids" in res["result"]


@pytest.mark.langsmith
async def test_rag_ingest_graph_inline_upload_runs() -> None:
    inputs = {
        "source_name": "uploaded.txt",
        "source_content_b64": base64.b64encode("RAG upload content".encode("utf-8")).decode("utf-8"),
        "source_mime_type": "text/plain",
        "backup_source": True,
    }
    res = await rag_ingest_graph.ainvoke(inputs)
    assert res["result"]["source_name"] == "uploaded.txt"
    assert res["result"]["source_storage"]
    assert res["result"]["upserted_count"] >= 1


@pytest.mark.langsmith
async def test_rag_ingest_graph_invalid_source_fails_explicitly() -> None:
    res = await rag_ingest_graph.ainvoke({"source_uri": "missing-file.txt"})
    assert res["result"]["status"] == "failed"
    assert res["result"]["upserted_count"] == 0
    assert res["result"]["error"]


@pytest.mark.langsmith
async def test_rag_delete_graph_runs() -> None:
    inputs = {"document_id": "doc-for-delete"}
    res = await rag_delete_graph.ainvoke(inputs)
    assert res["result"]["document_id"] == "doc-for-delete"


@pytest.mark.langsmith
async def test_rag_reindex_graph_runs() -> None:
    inputs = {"document_id": "doc-for-reindex"}
    res = await rag_reindex_graph.ainvoke(inputs)
    assert "upserted_count" in res["result"]


@pytest.mark.langsmith
async def test_rag_admin_graph_runs() -> None:
    inputs = {
        "operation": "list_documents",
        "page": 1,
        "page_size": 5,
        "sort_by": "updated_at",
        "sort_direction": "desc",
    }
    res = await rag_admin_graph.ainvoke(inputs)
    assert res["result"]["operation"] == "list_documents"
    assert "total" in res["result"]
    assert "sort" in res["result"]
    assert "meta" in res["result"]


@pytest.mark.langsmith
async def test_rag_admin_graph_page_contract_runs() -> None:
    inputs = {
        "operation": "get_page_contract",
        "page_name": "document_list",
    }
    res = await rag_admin_graph.ainvoke(inputs)
    assert res["result"]["operation"] == "get_page_contract"
    assert res["result"]["page_contract"]["page_name"] == "document_list"


@pytest.mark.langsmith
async def test_rag_admin_graph_unknown_operation_returns_error() -> None:
    res = await rag_admin_graph.ainvoke({"operation": "unknown_operation"})
    assert res["result"]["operation"] == "unknown_operation"
    assert "error" in res["result"]
