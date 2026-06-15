from pathlib import Path

from agent.services.ingestion_service import IngestionService


def test_split_documents_preserves_version_tracking_fields() -> None:
    service = IngestionService()
    chunks = service.split_documents(
        [
            {
                "document_id": "doc-1",
                "version_id": "ver-1",
                "version_number": 3,
                "source_type": "file",
                "source_uri": "memory://doc-1",
                "title": "Doc 1",
                "content": "RAG systems combine retrieval and generation.",
                "metadata": {"source_uri": "memory://doc-1"},
            }
        ]
    )

    assert chunks
    assert chunks[0]["document_id"] == "doc-1"
    assert chunks[0]["version_id"] == "ver-1"
    assert chunks[0]["version_number"] == 3
    assert chunks[0]["chunk_id"].startswith("doc-1::chunk::")


def test_load_documents_supports_structured_local_file(tmp_path: Path) -> None:
    service = IngestionService()
    csv_file = tmp_path / "kb.csv"
    csv_file.write_text("question,answer\nRAG,Retrieval-Augmented Generation\n", encoding="utf-8")

    documents = service.load_documents(str(csv_file))

    assert len(documents) == 1
    assert documents[0]["source_type"] == "file"
    assert "Retrieval-Augmented Generation" in documents[0]["content"]


def test_load_documents_supports_directory_with_mixed_files(tmp_path: Path) -> None:
    service = IngestionService()
    (tmp_path / "intro.md").write_text("# Intro", encoding="utf-8")
    (tmp_path / "data.json").write_text('{"topic":"rag"}', encoding="utf-8")
    (tmp_path / "skip.bin").write_bytes(b"\x00\x01")

    documents = service.load_documents(str(tmp_path))

    assert len(documents) == 2
    assert all(document["source_type"] == "directory" for document in documents)


def test_load_documents_requires_explicit_text_or_memory_scheme_for_fallback() -> None:
    service = IngestionService()

    assert service.load_documents("missing-file.txt") == []

    memory_docs = service.load_documents("memory://doc-1")
    assert len(memory_docs) == 1
    assert memory_docs[0]["source_type"] == "memory"

    text_docs = service.load_documents("text://hello rag")
    assert len(text_docs) == 1
    assert text_docs[0]["content"] == "hello rag"
