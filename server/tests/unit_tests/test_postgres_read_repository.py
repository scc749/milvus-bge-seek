from agent.repositories.postgres_read_repository import PostgresReadRepository


def test_read_repository_returns_empty_payloads_without_connection() -> None:
    repository = PostgresReadRepository()
    repository._connect = lambda: None  # type: ignore[method-assign]

    assert repository.list_documents()["records"] == []
    assert repository.list_documents()["total"] == 0
    assert repository.list_documents()["meta"]["sortable_fields"]
    assert repository.get_document_detail("doc-1")["records"] == []
    assert repository.list_document_versions("doc-1")["records"] == []
    assert repository.list_ingest_jobs()["records"] == []
    assert repository.list_delete_jobs()["records"] == []
    assert repository.get_ingest_job_detail("job-1")["records"] == []
    assert repository.get_delete_job_detail("job-1")["records"] == []
