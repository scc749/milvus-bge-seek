from agent.services.admin_application_service import AdminApplicationService
from agent.services.admin_page_contract_service import AdminPageContractService
from agent.repositories.postgres_read_repository import PostgresReadRepository


class StubReadRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def list_documents(self, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append(("list_documents", kwargs))
        return {"operation": "list_documents", "records": []}


def test_unknown_admin_operation_returns_explicit_error() -> None:
    service = AdminApplicationService(
        read_repository=PostgresReadRepository(),
        admin_page_contract_service=AdminPageContractService(),
    )

    result = service.fetch_records({"operation": "unknown_operation"})["response"]

    assert result["operation"] == "unknown_operation"
    assert "error" in result
    assert "available_operations" in result["meta"]


def test_list_documents_routes_through_registered_handler() -> None:
    repository = StubReadRepository()
    service = AdminApplicationService(
        read_repository=repository,  # type: ignore[arg-type]
        admin_page_contract_service=AdminPageContractService(),
    )

    result = service.fetch_records(
        {
            "operation": "list_documents",
            "page": 2,
            "page_size": 10,
            "status_filter": "completed",
            "source_type_filter": "file",
            "query": "RAG",
            "sort_by": "updated_at",
            "sort_direction": "asc",
        }
    )["response"]

    assert result["operation"] == "list_documents"
    assert repository.calls == [
        (
            "list_documents",
            {
                "page": 2,
                "page_size": 10,
                "status": "completed",
                "source_type": "file",
                "query": "RAG",
                "sort_by": "updated_at",
                "sort_direction": "asc",
            },
        )
    ]
