"""Lazy factories for LLM, embeddings, vector store, and retriever."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from agent.config import get_settings


def _safe_load_json(raw: str) -> dict[str, Any] | None:
    """Parse a JSON object from env text and ignore invalid values."""

    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _build_milvus_connection_args() -> dict[str, Any]:
    """Build shared Milvus connection arguments from app settings."""

    settings = get_settings()
    connection_args: dict[str, Any] = {"uri": settings.milvus_uri}
    if settings.milvus_token:
        connection_args["token"] = settings.milvus_token
    if settings.milvus_db_name:
        connection_args["db_name"] = settings.milvus_db_name
    return connection_args


def ensure_milvus_orm_connection(alias: str = "default") -> bool:
    """Ensure a pymilvus ORM connection exists for Collection-based operations.

    `langchain_milvus.Milvus` internally mixes `MilvusClient` with ORM `Collection`.
    The ORM layer requires a registered `connections.connect(...)` alias.
    """

    try:
        from pymilvus import connections
    except ImportError:
        return False

    try:
        connections.connect(alias=alias, **_build_milvus_connection_args())
    except Exception:
        return False
    return True


@lru_cache(maxsize=1)
def create_chat_model() -> Any:
    """Return the configured chat model or None in offline skeleton mode."""

    settings = get_settings()
    try:
        from langchain_deepseek import ChatDeepSeek
    except ImportError:
        return None
    if not settings.deepseek_api_key:
        return None
    return ChatDeepSeek(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=settings.deepseek_temperature,
        max_retries=settings.deepseek_max_retries,
    )


@lru_cache(maxsize=1)
def create_embeddings() -> Any:
    """Return the configured embedding model or None in offline skeleton mode."""

    settings = get_settings()
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:
        return None
    encode_kwargs = {"normalize_embeddings": settings.embedding_normalize}
    query_instruction = settings.embedding_query_instruction
    if query_instruction:
        encode_kwargs["prompt"] = query_instruction
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model_name,
        model_kwargs={"device": settings.embedding_device},
        encode_kwargs=encode_kwargs,
    )


@lru_cache(maxsize=1)
def create_vectorstore() -> Any:
    """Return the configured Milvus vector store or None in offline mode."""

    settings = get_settings()
    embeddings = create_embeddings()
    try:
        from langchain_milvus import Milvus
    except ImportError:
        return None
    if embeddings is None:
        return None

    connection_args = _build_milvus_connection_args()
    bootstrap_client = create_milvus_client()
    if bootstrap_client is None:
        return None
    ensure_milvus_orm_connection(getattr(bootstrap_client, "_using", "default"))

    kwargs: dict[str, Any] = {
        "embedding_function": embeddings,
        "collection_name": settings.milvus_collection,
        "connection_args": connection_args,
        "auto_id": False,
        "primary_field": settings.milvus_primary_field,
        "text_field": settings.milvus_text_field,
        "vector_field": settings.milvus_vector_field,
        "metadata_field": settings.milvus_metadata_field,
    }
    index_params = _safe_load_json(settings.milvus_index_params)
    if index_params:
        kwargs["index_params"] = index_params
    return Milvus(**kwargs)


@lru_cache(maxsize=1)
def create_milvus_client() -> Any:
    """Return a low-level Milvus client for admin operations when available."""

    try:
        from pymilvus import MilvusClient
    except ImportError:
        return None

    return MilvusClient(**_build_milvus_connection_args())


def ensure_milvus_collection_loaded() -> None:
    """Load the configured Milvus collection when the admin client is available."""

    settings = get_settings()
    client = create_milvus_client()
    if client is None:
        return
    try:
        if client.has_collection(collection_name=settings.milvus_collection):
            client.load_collection(collection_name=settings.milvus_collection)
    except Exception:
        return


def create_retriever(search_kwargs: dict[str, Any] | None = None) -> Any:
    """Return a retriever when the vector store is configured."""

    settings = get_settings()
    vectorstore = create_vectorstore()
    if vectorstore is None:
        return None
    ensure_milvus_collection_loaded()

    kwargs: dict[str, Any] = {"k": settings.retrieval_top_k}
    if settings.score_threshold > 0:
        kwargs["score_threshold"] = settings.score_threshold
    search_params = _safe_load_json(settings.milvus_search_params)
    if search_params:
        kwargs["search_params"] = search_params
    if search_kwargs:
        kwargs.update(search_kwargs)
    return vectorstore.as_retriever(search_kwargs=kwargs)


@lru_cache(maxsize=1)
def create_reranker() -> Any:
    """Return a Hugging Face cross encoder when dependencies are installed."""

    settings = get_settings()
    try:
        from langchain_community.cross_encoders import HuggingFaceCrossEncoder
    except ImportError:
        return None
    return HuggingFaceCrossEncoder(model_name=settings.reranker_model_name)


def create_text_splitter() -> Any:
    """Return the configured text splitter."""

    settings = get_settings()
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        return RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
    except ImportError:
        class _FallbackSplitter:
            def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
                self.chunk_size = chunk_size
                self.chunk_overlap = chunk_overlap

            def split_text(self, text: str) -> list[str]:
                if len(text) <= self.chunk_size:
                    return [text]
                chunks: list[str] = []
                start = 0
                while start < len(text):
                    end = start + self.chunk_size
                    chunks.append(text[start:end])
                    if end >= len(text):
                        break
                    start = max(end - self.chunk_overlap, start + 1)
                return chunks

        return _FallbackSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
