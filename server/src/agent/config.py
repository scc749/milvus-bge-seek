"""Configuration helpers for the RAG server skeleton."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None else default


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None else default


@dataclass(frozen=True)
class AppSettings:
    """Application settings loaded from environment variables."""

    app_name: str = "langgraph-rag-server"
    app_env: str = "dev"
    log_level: str = "INFO"
    enable_langsmith: bool = False
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_temperature: float = 0.0
    deepseek_max_retries: int = 2
    embedding_model_name: str = "BAAI/bge-m3"
    embedding_device: str = "cpu"
    embedding_normalize: bool = True
    embedding_query_instruction: str = ""
    reranker_model_name: str = "BAAI/bge-reranker-v2-m3"
    rerank_top_n: int = 4
    milvus_uri: str = "http://localhost:19530"
    milvus_token: str = ""
    milvus_db_name: str = "default"
    milvus_collection: str = "rag_documents"
    milvus_primary_field: str = "pk"
    milvus_text_field: str = "text"
    milvus_vector_field: str = "vector"
    milvus_metadata_field: str = "metadata"
    milvus_metric_type: str = "COSINE"
    milvus_index_type: str = "AUTOINDEX"
    milvus_index_params: str = ""
    milvus_search_params: str = ""
    retrieval_top_k: int = 8
    score_threshold: float = 0.0
    chunk_size: int = 800
    chunk_overlap: int = 120
    source_storage_backend: str = "local"
    source_storage_root: str = "data/source_files"
    source_storage_bucket: str = "rag-source-files"
    source_storage_prefix: str = "documents"
    source_storage_minio_endpoint: str = "http://localhost:9090"
    source_storage_minio_access_key: str = "minioadmin"
    source_storage_minio_secret_key: str = "minioadmin"
    source_storage_minio_secure: bool = False
    url_recursive_default_enabled: bool = True
    url_recursive_default_max_depth: int = 2
    url_recursive_timeout_seconds: int = 10
    postgres_dsn: str = ""
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "rag_app"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_schema: str = "public"

    @classmethod
    def from_env(cls) -> "AppSettings":
        """Build settings from environment variables."""

        return cls(
            app_env=os.getenv("APP_ENV", cls.app_env),
            log_level=os.getenv("LOG_LEVEL", cls.log_level),
            enable_langsmith=_get_bool("ENABLE_LANGSMITH", cls.enable_langsmith),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", cls.deepseek_api_key),
            deepseek_model=os.getenv("DEEPSEEK_MODEL", cls.deepseek_model),
            deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", cls.deepseek_base_url),
            deepseek_temperature=_get_float("DEEPSEEK_TEMPERATURE", cls.deepseek_temperature),
            deepseek_max_retries=_get_int("DEEPSEEK_MAX_RETRIES", cls.deepseek_max_retries),
            embedding_model_name=os.getenv("EMBEDDING_MODEL_NAME", cls.embedding_model_name),
            embedding_device=os.getenv("EMBEDDING_DEVICE", cls.embedding_device),
            embedding_normalize=_get_bool("EMBEDDING_NORMALIZE", cls.embedding_normalize),
            embedding_query_instruction=os.getenv(
                "EMBEDDING_QUERY_INSTRUCTION",
                cls.embedding_query_instruction,
            ),
            reranker_model_name=os.getenv("RERANKER_MODEL_NAME", cls.reranker_model_name),
            rerank_top_n=_get_int("RERANK_TOP_N", cls.rerank_top_n),
            milvus_uri=os.getenv("MILVUS_URI", cls.milvus_uri),
            milvus_token=os.getenv("MILVUS_TOKEN", cls.milvus_token),
            milvus_db_name=os.getenv("MILVUS_DB_NAME", cls.milvus_db_name),
            milvus_collection=os.getenv("MILVUS_COLLECTION", cls.milvus_collection),
            milvus_primary_field=os.getenv("MILVUS_PRIMARY_FIELD", cls.milvus_primary_field),
            milvus_text_field=os.getenv("MILVUS_TEXT_FIELD", cls.milvus_text_field),
            milvus_vector_field=os.getenv("MILVUS_VECTOR_FIELD", cls.milvus_vector_field),
            milvus_metadata_field=os.getenv("MILVUS_METADATA_FIELD", cls.milvus_metadata_field),
            milvus_metric_type=os.getenv("MILVUS_METRIC_TYPE", cls.milvus_metric_type),
            milvus_index_type=os.getenv("MILVUS_INDEX_TYPE", cls.milvus_index_type),
            milvus_index_params=os.getenv("MILVUS_INDEX_PARAMS", cls.milvus_index_params),
            milvus_search_params=os.getenv("MILVUS_SEARCH_PARAMS", cls.milvus_search_params),
            retrieval_top_k=_get_int("RETRIEVAL_TOP_K", cls.retrieval_top_k),
            score_threshold=_get_float("SCORE_THRESHOLD", cls.score_threshold),
            chunk_size=_get_int("CHUNK_SIZE", cls.chunk_size),
            chunk_overlap=_get_int("CHUNK_OVERLAP", cls.chunk_overlap),
            source_storage_backend=os.getenv(
                "SOURCE_STORAGE_BACKEND",
                cls.source_storage_backend,
            ),
            source_storage_root=os.getenv("SOURCE_STORAGE_ROOT", cls.source_storage_root),
            source_storage_bucket=os.getenv("SOURCE_STORAGE_BUCKET", cls.source_storage_bucket),
            source_storage_prefix=os.getenv("SOURCE_STORAGE_PREFIX", cls.source_storage_prefix),
            source_storage_minio_endpoint=os.getenv(
                "SOURCE_STORAGE_MINIO_ENDPOINT",
                cls.source_storage_minio_endpoint,
            ),
            source_storage_minio_access_key=os.getenv(
                "SOURCE_STORAGE_MINIO_ACCESS_KEY",
                cls.source_storage_minio_access_key,
            ),
            source_storage_minio_secret_key=os.getenv(
                "SOURCE_STORAGE_MINIO_SECRET_KEY",
                cls.source_storage_minio_secret_key,
            ),
            source_storage_minio_secure=_get_bool(
                "SOURCE_STORAGE_MINIO_SECURE",
                cls.source_storage_minio_secure,
            ),
            url_recursive_default_enabled=_get_bool(
                "URL_RECURSIVE_DEFAULT_ENABLED",
                cls.url_recursive_default_enabled,
            ),
            url_recursive_default_max_depth=_get_int(
                "URL_RECURSIVE_DEFAULT_MAX_DEPTH",
                cls.url_recursive_default_max_depth,
            ),
            url_recursive_timeout_seconds=_get_int(
                "URL_RECURSIVE_TIMEOUT_SECONDS",
                cls.url_recursive_timeout_seconds,
            ),
            postgres_dsn=os.getenv("POSTGRES_DSN", cls.postgres_dsn),
            postgres_host=os.getenv("POSTGRES_HOST", cls.postgres_host),
            postgres_port=_get_int("POSTGRES_PORT", cls.postgres_port),
            postgres_db=os.getenv("POSTGRES_DB", cls.postgres_db),
            postgres_user=os.getenv("POSTGRES_USER", cls.postgres_user),
            postgres_password=os.getenv("POSTGRES_PASSWORD", cls.postgres_password),
            postgres_schema=os.getenv("POSTGRES_SCHEMA", cls.postgres_schema),
        )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached settings for the current process."""

    return AppSettings.from_env()
