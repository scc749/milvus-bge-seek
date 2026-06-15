from agent.services.delete_application_service import DeleteApplicationService


class _FakeIngestionService:
    def __init__(self, deleted_count: int) -> None:
        self.deleted_count = deleted_count

    def delete_chunks(self, chunk_ids: list[str]) -> int:
        return self.deleted_count


class _FakeRegistryService:
    def __init__(self) -> None:
        self.finalize_calls: list[dict[str, object]] = []

    def create_delete_job(self, document_id: str) -> str:
        return f"del-{document_id}"

    def get_document_chunk_ids(self, document_id: str) -> list[str]:
        return [f"{document_id}-chunk-1", f"{document_id}-chunk-2"]

    def finalize_delete_job(self, **kwargs) -> None:
        self.finalize_calls.append(kwargs)


def test_delete_application_service_marks_failed_on_partial_delete() -> None:
    registry = _FakeRegistryService()
    service = DeleteApplicationService(
        ingestion_service=_FakeIngestionService(deleted_count=1),
        registry_repository=registry,  # type: ignore[arg-type]
    )

    result = service.delete_document_chunks(
        document_id="doc-1",
        delete_job_id="job-1",
        chunk_ids=["c1", "c2"],
    )

    assert result["delete_status"] == "failed"
    assert registry.finalize_calls[0]["status"] == "failed"
