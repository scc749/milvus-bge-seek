from agent.services.admin_page_contract_service import AdminPageContractService


def test_document_list_page_contract_shape() -> None:
    service = AdminPageContractService()

    result = service.get_page_contract("document_list")["result"]["page_contract"]

    assert result["page_name"] == "document_list"
    assert result["primary_operation"] == "list_documents"
    assert result["sorts"]
    assert result["filters"]
    assert result["tables"]
    assert result["tables"][0]["columns"]


def test_job_page_contracts_expose_list_tables() -> None:
    service = AdminPageContractService()

    ingest_contract = service.get_page_contract("ingest_job")["result"]["page_contract"]
    delete_contract = service.get_page_contract("delete_job")["result"]["page_contract"]

    assert ingest_contract["tables"][0]["source_operation"] == "list_ingest_jobs"
    assert delete_contract["tables"][0]["source_operation"] == "list_delete_jobs"


def test_unknown_page_contract_returns_explicit_error() -> None:
    service = AdminPageContractService()

    result = service.get_page_contract("unknown_page")["result"]

    assert result["operation"] == "get_page_contract"
    assert "error" in result
    assert "available_pages" in result
