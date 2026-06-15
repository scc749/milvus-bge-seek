"""Dependency container for graph nodes."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from agent.repositories.assistant_thread_repository import AssistantThreadRepository
from agent.repositories.postgres_read_repository import PostgresReadRepository
from agent.repositories.postgres_registry_repository import PostgresRegistryRepository
from agent.repositories.postgres_schema_manager import PostgresSchemaManager
from agent.services.answer_service import AnswerService
from agent.services.admin_application_service import AdminApplicationService
from agent.services.admin_page_contract_service import AdminPageContractService
from agent.services.compat_application_service import CompatApplicationService
from agent.services.conversation_service import ConversationService
from agent.services.delete_application_service import DeleteApplicationService
from agent.services.document_source_service import DocumentSourceService
from agent.services.ingestion_service import IngestionService
from agent.services.ingest_application_service import IngestApplicationService
from agent.services.document_source_store_service import DocumentSourceStoreService
from agent.services.milvus_admin_service import MilvusAdminService
from agent.services.reindex_application_service import ReindexApplicationService
from agent.services.rerank_service import RerankService
from agent.services.retrieval_service import RetrievalService


@dataclass(frozen=True)
class ServiceContainer:
    """Container for application services used by graph nodes."""

    ingestion_service: IngestionService
    milvus_admin_service: MilvusAdminService
    postgres_registry_repository: PostgresRegistryRepository
    postgres_read_repository: PostgresReadRepository
    assistant_thread_repository: AssistantThreadRepository
    document_source_store_service: DocumentSourceStoreService
    document_source_service: DocumentSourceService
    ingest_application_service: IngestApplicationService
    delete_application_service: DeleteApplicationService
    reindex_application_service: ReindexApplicationService
    admin_application_service: AdminApplicationService
    admin_page_contract_service: AdminPageContractService
    compat_application_service: CompatApplicationService
    conversation_service: ConversationService
    retrieval_service: RetrievalService
    rerank_service: RerankService
    answer_service: AnswerService


@lru_cache(maxsize=1)
def get_container() -> ServiceContainer:
    """Return cached service container."""

    from agent.graph import (
        assistant_graph,
        rag_admin_graph,
        rag_delete_graph,
        rag_ingest_graph,
        rag_reindex_graph,
    )

    milvus_admin_service = MilvusAdminService()
    document_source_store_service = DocumentSourceStoreService()
    postgres_schema_manager = PostgresSchemaManager()
    postgres_registry_repository = PostgresRegistryRepository(
        schema_manager=postgres_schema_manager
    )
    postgres_read_repository = PostgresReadRepository(schema_manager=postgres_schema_manager)
    assistant_thread_repository = AssistantThreadRepository(
        schema_manager=postgres_schema_manager
    )
    admin_page_contract_service = AdminPageContractService()
    ingestion_service = IngestionService(milvus_admin_service=milvus_admin_service)
    retrieval_service = RetrievalService()
    rerank_service = RerankService()
    answer_service = AnswerService()
    document_source_service = DocumentSourceService()
    ingest_application_service = IngestApplicationService(
        ingestion_service=ingestion_service,
        registry_repository=postgres_registry_repository,
        document_source_store_service=document_source_store_service,
        document_source_service=document_source_service,
    )
    delete_application_service = DeleteApplicationService(
        ingestion_service=ingestion_service,
        registry_repository=postgres_registry_repository,
    )
    reindex_application_service = ReindexApplicationService(
        registry_repository=postgres_registry_repository,
        document_source_store_service=document_source_store_service,
        document_source_service=document_source_service,
    )
    admin_application_service = AdminApplicationService(
        read_repository=postgres_read_repository,
        admin_page_contract_service=admin_page_contract_service,
    )
    conversation_service = ConversationService()
    compat_application_service = CompatApplicationService(
        assistant_graph=assistant_graph,
        admin_graph=rag_admin_graph,
        ingest_graph=rag_ingest_graph,
        delete_graph=rag_delete_graph,
        reindex_graph=rag_reindex_graph,
        conversation_service=conversation_service,
        retrieval_service=retrieval_service,
        rerank_service=rerank_service,
        answer_service=answer_service,
        assistant_thread_repository=assistant_thread_repository,
        postgres_registry_repository=postgres_registry_repository,
    )
    return ServiceContainer(
        ingestion_service=ingestion_service,
        milvus_admin_service=milvus_admin_service,
        postgres_registry_repository=postgres_registry_repository,
        postgres_read_repository=postgres_read_repository,
        assistant_thread_repository=assistant_thread_repository,
        document_source_store_service=document_source_store_service,
        document_source_service=document_source_service,
        ingest_application_service=ingest_application_service,
        delete_application_service=delete_application_service,
        reindex_application_service=reindex_application_service,
        admin_application_service=admin_application_service,
        admin_page_contract_service=admin_page_contract_service,
        compat_application_service=compat_application_service,
        conversation_service=conversation_service,
        retrieval_service=retrieval_service,
        rerank_service=rerank_service,
        answer_service=answer_service,
    )
