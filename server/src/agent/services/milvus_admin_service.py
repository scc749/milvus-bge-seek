"""Administrative helpers for managing the Milvus collection lifecycle."""

from __future__ import annotations

from typing import Any

from agent.components.factories import (
    _safe_load_json,
    create_embeddings,
    create_milvus_client,
)
from agent.config import get_settings


class MilvusAdminService:
    """Encapsulate Milvus collection initialization and load operations."""

    def ensure_collection(self) -> bool:
        """Ensure the configured Milvus collection exists and is loaded."""

        settings = get_settings()
        client = create_milvus_client()
        embeddings = create_embeddings()
        if client is None or embeddings is None:
            return False

        try:
            if not client.has_collection(collection_name=settings.milvus_collection):
                self._create_collection(client, embeddings)
            client.load_collection(collection_name=settings.milvus_collection)
            return True
        except Exception:
            return False

    def _create_collection(self, client: Any, embeddings: Any) -> None:
        """Create the Milvus collection with schema and index configuration."""

        settings = get_settings()
        from pymilvus import DataType, MilvusClient

        dim = self._resolve_embedding_dim(embeddings)

        schema = MilvusClient.create_schema(
            auto_id=False,
            enable_dynamic_field=False,
        )
        schema.add_field(
            field_name=settings.milvus_primary_field,
            datatype=DataType.VARCHAR,
            is_primary=True,
            max_length=512,
        )
        schema.add_field(
            field_name=settings.milvus_text_field,
            datatype=DataType.VARCHAR,
            max_length=65535,
        )
        schema.add_field(
            field_name=settings.milvus_vector_field,
            datatype=DataType.FLOAT_VECTOR,
            dim=dim,
        )
        schema.add_field(
            field_name=settings.milvus_metadata_field,
            datatype=DataType.JSON,
            nullable=True,
        )

        index_params = client.prepare_index_params()
        vector_index_kwargs = {
            "field_name": settings.milvus_vector_field,
            "index_name": f"{settings.milvus_vector_field}_index",
            "index_type": settings.milvus_index_type,
            "metric_type": settings.milvus_metric_type,
        }
        parsed_index_params = _safe_load_json(settings.milvus_index_params)
        if parsed_index_params and "params" in parsed_index_params:
            vector_index_kwargs["params"] = parsed_index_params["params"]
        index_params.add_index(**vector_index_kwargs)

        client.create_collection(
            collection_name=settings.milvus_collection,
            schema=schema,
            index_params=index_params,
        )

    def _resolve_embedding_dim(self, embeddings: Any) -> int:
        """Determine the embedding dimensionality from the configured model."""

        sample = embeddings.embed_query("dimension probe")
        if not sample:
            raise ValueError("Embedding model returned an empty vector.")
        return len(sample)
