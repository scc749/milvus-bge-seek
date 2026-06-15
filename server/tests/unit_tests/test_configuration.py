from langgraph.pregel import Pregel

from agent.config import get_settings
from agent.graph import (
    assistant_graph,
    graph,
    rag_admin_graph,
    rag_delete_graph,
    rag_ingest_graph,
    rag_query_graph,
    rag_reindex_graph,
)
from agent.prompts import format_retrieval_context


def test_graph_exports_are_pregel() -> None:
    assert isinstance(graph, Pregel)
    assert isinstance(assistant_graph, Pregel)
    assert isinstance(rag_query_graph, Pregel)
    assert isinstance(rag_ingest_graph, Pregel)
    assert isinstance(rag_delete_graph, Pregel)
    assert isinstance(rag_reindex_graph, Pregel)
    assert isinstance(rag_admin_graph, Pregel)


def test_settings_defaults() -> None:
    settings = get_settings()
    assert settings.embedding_model_name == "BAAI/bge-m3"
    assert settings.embedding_query_instruction == ""
    assert settings.reranker_model_name == "BAAI/bge-reranker-v2-m3"
    assert settings.deepseek_temperature == 0.0
    assert settings.deepseek_max_retries == 2
    assert settings.milvus_primary_field == "pk"
    assert settings.milvus_vector_field == "vector"
    assert settings.milvus_metric_type == "COSINE"
    assert settings.postgres_db == "rag_app"
    assert settings.postgres_schema == "public"


def test_retrieval_context_formatting() -> None:
    context = format_retrieval_context(
        [
            {
                "document_id": "doc-1",
                "chunk_id": "chunk-1",
                "content": "RAG combines retrieval with generation.",
                "metadata": {"title": "Intro"},
            }
        ]
    )
    assert "[Source 1]" in context
    assert "document_id: doc-1" in context
    assert "RAG combines retrieval with generation." in context
