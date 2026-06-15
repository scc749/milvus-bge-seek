from agent.services.document_source_service import DocumentSourceService


def test_public_metadata_strips_internal_source_fields() -> None:
    service = DocumentSourceService()

    result = service.public_metadata(
        {
            "title": "Doc",
            "source_storage": {"storage_uri": "x"},
            "replay_source_uri": "file:///tmp/a.txt",
            "source_path_mapping": {"a": "b"},
        }
    )

    assert result == {"title": "Doc"}


def test_pin_document_identity_rewrites_document_and_source_mapping() -> None:
    service = DocumentSourceService()

    result = service.pin_document_identity(
        raw_documents=[
            {
                "source_uri": "E:/managed/a.txt",
                "title": "New title",
                "metadata": {
                    "source_path_mapping": {"E:/managed/a.txt": "E:/origin/a.txt"},
                },
            }
        ],
        document_id="doc-1",
        source_uri="upload://a.txt",
        document_record={
            "title": "Stored title",
            "source_uri": "upload://a.txt",
            "source_storage": {
                "path_mapping": {
                    "E:/managed/a.txt": "upload://a.txt",
                    "E:/origin/a.txt": "upload://a.txt",
                }
            },
        },
    )

    assert result[0]["metadata"]["document_id"] == "doc-1"
    assert result[0]["source_uri"] == "upload://a.txt"
    assert result[0]["metadata"]["replay_source_uri"] == "E:/managed/a.txt"
