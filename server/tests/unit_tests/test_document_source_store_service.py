import base64
from pathlib import Path

from agent.services.document_source_store_service import DocumentSourceStoreService


def test_prepare_source_copies_local_file_into_managed_storage(tmp_path: Path) -> None:
    service = DocumentSourceStoreService()
    service._root = tmp_path / "managed"  # type: ignore[attr-defined]
    source_file = tmp_path / "report.md"
    source_file.write_text("# RAG", encoding="utf-8")

    prepared = service.prepare_source(source_uri=str(source_file))

    assert prepared.display_source_uri == str(source_file)
    assert prepared.load_source_uri != str(source_file)
    assert Path(prepared.load_source_uri).exists()
    assert prepared.path_mapping[prepared.load_source_uri] == str(source_file)
    assert prepared.storage["storage_uri"] == prepared.load_source_uri


def test_prepare_source_persists_inline_upload_payload(tmp_path: Path) -> None:
    service = DocumentSourceStoreService()
    service._root = tmp_path / "managed"  # type: ignore[attr-defined]
    payload = base64.b64encode(b"hello rag").decode("utf-8")

    prepared = service.prepare_source(
        source_name="notes.txt",
        source_content_b64=payload,
        source_mime_type="text/plain",
    )

    stored_path = Path(prepared.load_source_uri)
    assert stored_path.exists()
    assert stored_path.read_text(encoding="utf-8") == "hello rag"
    assert prepared.display_source_uri == "upload://notes.txt"
    assert prepared.storage["storage_uri"] == prepared.load_source_uri


def test_materialize_replay_source_prefers_existing_replay_path(tmp_path: Path) -> None:
    service = DocumentSourceStoreService()
    replay_file = tmp_path / "stored.txt"
    replay_file.write_text("persisted", encoding="utf-8")

    resolved = service.materialize_replay_source(
        {
            "source_uri": "upload://stored.txt",
            "metadata": {
                "replay_source_uri": str(replay_file),
                "source_storage": {"storage_uri": str(replay_file)},
            },
        }
    )

    assert resolved == str(replay_file)
