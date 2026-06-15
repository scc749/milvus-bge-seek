"""Business service for ingestion flow."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit, urlunsplit
from typing import Any

from agent.components.factories import create_text_splitter, create_vectorstore
from agent.config import get_settings
from agent.services.document_parser_service import DocumentParserService
from agent.services.milvus_admin_service import MilvusAdminService
from agent.utils.documents import ensure_chunk_id, ensure_document_id


class IngestionService:
    """Encapsulate document normalization, chunking, and upsert orchestration."""

    def __init__(
        self,
        milvus_admin_service: MilvusAdminService | None = None,
        document_parser_service: DocumentParserService | None = None,
    ) -> None:
        self._milvus_admin_service = milvus_admin_service or MilvusAdminService()
        self._document_parser_service = document_parser_service or DocumentParserService()
        self._settings = get_settings()

    def load_documents(
        self,
        source_uri: str | None,
        *,
        load_options: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Load source documents from local files, URLs, or offline fallback."""

        options = load_options if isinstance(load_options, dict) else {}
        if not source_uri:
            return []
        if source_uri.startswith("file://"):
            source_uri = source_uri.removeprefix("file://")
        if source_uri.startswith(("http://", "https://")):
            recursive_enabled = bool(
                options.get("recursive_url", self._settings.url_recursive_default_enabled)
            )
            if recursive_enabled:
                return self._load_recursive_url_documents(source_uri, options)
            return self._load_single_url_documents(source_uri)
        from pathlib import Path

        if source_uri.startswith("memory://"):
            return [
                {
                    "source_uri": source_uri,
                    "source_type": "memory",
                    "title": "Memory document",
                    "content": f"Ingestion placeholder content loaded from {source_uri}.",
                    "metadata": {"source_uri": source_uri},
                }
            ]
        if source_uri.startswith("text://"):
            content = source_uri.removeprefix("text://")
            return [
                {
                    "source_uri": "text://",
                    "source_type": "text",
                    "title": "Text document",
                    "content": content,
                    "metadata": {"source_uri": "text://"},
                }
            ]

        local_path = Path(source_uri)
        if local_path.exists() and local_path.is_dir():
            documents = self._document_parser_service.parse_directory(local_path)
            for document in documents:
                document["source_type"] = "directory"
                document.setdefault("metadata", {})["directory_source_uri"] = str(local_path)
            return documents
        if local_path.exists() and local_path.is_file():
            parsed = self._document_parser_service.parse_file(local_path)
            if parsed is not None:
                return [parsed]
        return []

    def normalize_documents(self, raw_documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Normalize raw documents into the internal schema."""

        normalized: list[dict[str, Any]] = []
        for raw in raw_documents:
            metadata = dict(raw.get("metadata", {}))
            document_id = ensure_document_id(metadata)
            metadata["document_id"] = document_id
            normalized.append(
                {
                    "document_id": document_id,
                    "source_type": raw.get("source_type", "text"),
                    "source_uri": raw.get("source_uri", ""),
                    "title": raw.get("title"),
                    "content": raw.get("content", ""),
                    "metadata": metadata,
                }
            )
        return normalized

    def split_documents(self, normalized_documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Split documents into persistable chunks."""

        splitter = create_text_splitter()
        chunks: list[dict[str, Any]] = []
        for doc in normalized_documents:
            texts = splitter.split_text(doc["content"]) or [doc["content"]]
            for index, text in enumerate(texts):
                chunks.append(
                    {
                        "chunk_id": ensure_chunk_id(doc["document_id"], index),
                        "document_id": doc["document_id"],
                        "version_id": doc.get("version_id"),
                        "version_number": doc.get("version_number"),
                        "chunk_index": index,
                        "content": text,
                        "metadata": {
                            **doc["metadata"],
                            "title": doc.get("title"),
                            "source_uri": doc.get("source_uri"),
                        },
                    }
                )
        return chunks

    def upsert_chunks(self, chunks: list[dict[str, Any]]) -> int:
        """Persist chunks to Milvus when available; otherwise return 0.

        Important: returning len(chunks) on failure will make upstream jobs look "completed"
        while Milvus has nothing. This method is strict by design.
        """

        try:
            vectorstore = create_vectorstore()
        except Exception:
            return 0
        if vectorstore is None:
            return 0
        try:
            self._milvus_admin_service.ensure_collection()
            from langchain_core.documents import Document

            documents = [
                Document(
                    page_content=chunk["content"],
                    metadata={
                        **chunk.get("metadata", {}),
                        "chunk_id": chunk["chunk_id"],
                        "document_id": chunk["document_id"],
                        "chunk_index": chunk["chunk_index"],
                    },
                )
                for chunk in chunks
            ]
            ids = [chunk["chunk_id"] for chunk in chunks]
            vectorstore.add_documents(documents=documents, ids=ids)
        except Exception:
            return 0
        return len(chunks)

    def delete_chunks(self, chunk_ids: list[str]) -> int:
        """Delete chunk records from Milvus when the vector store is available."""

        if not chunk_ids:
            return 0
        try:
            vectorstore = create_vectorstore()
        except Exception:
            return 0
        if vectorstore is None:
            return 0
        try:
            vectorstore.delete(ids=chunk_ids)
        except Exception:
            return 0
        return len(chunk_ids)

    def _load_single_url_documents(self, source_uri: str) -> list[dict[str, Any]]:
        try:
            from langchain_community.document_loaders import WebBaseLoader

            docs = WebBaseLoader(source_uri).load()
        except Exception:
            return []
        return self._build_url_documents(
            docs=docs,
            root_url=source_uri,
            recursive=False,
            recursive_max_depth=0,
        )

    def _load_recursive_url_documents(
        self,
        source_uri: str,
        options: dict[str, Any],
    ) -> list[dict[str, Any]]:
        try:
            from langchain_community.document_loaders import RecursiveUrlLoader
        except ImportError as exc:
            raise RuntimeError("当前环境缺少 RecursiveUrlLoader 依赖。") from exc

        max_depth = int(
            options.get(
                "recursive_max_depth",
                self._settings.url_recursive_default_max_depth,
            )
            or self._settings.url_recursive_default_max_depth
        )
        loader = RecursiveUrlLoader(
            source_uri,
            max_depth=max_depth,
            use_async=False,
            extractor=self._extract_html_text,
            timeout=int(
                options.get(
                    "recursive_timeout_seconds",
                    self._settings.url_recursive_timeout_seconds,
                )
            ),
            prevent_outside=bool(options.get("recursive_prevent_outside", True)),
            base_url=source_uri,
            check_response_status=True,
        )
        docs = loader.load()
        return self._build_url_documents(
            docs=docs,
            root_url=source_uri,
            recursive=True,
            recursive_max_depth=max_depth,
        )

    def _build_url_documents(
        self,
        *,
        docs: list[Any],
        root_url: str,
        recursive: bool,
        recursive_max_depth: int,
    ) -> list[dict[str, Any]]:
        normalized_root = self._canonicalize_url(root_url)
        pages: list[dict[str, Any]] = []
        seen: set[str] = set()
        for doc in docs:
            metadata = dict(getattr(doc, "metadata", {}) or {})
            page_url = self._canonicalize_url(
                str(metadata.get("source") or metadata.get("url") or root_url)
            )
            if not page_url or page_url in seen:
                continue
            seen.add(page_url)
            page_content = str(getattr(doc, "page_content", "") or "").strip()
            if not page_content:
                continue
            route_path = self._build_route_path(normalized_root, page_url)
            title = metadata.get("title") or route_path or page_url
            metadata.update(
                {
                    "source_uri": page_url,
                    "document_id": self._build_url_document_id(page_url),
                    "crawl_root_uri": normalized_root,
                    "page_url": page_url,
                    "page_route": route_path,
                    "crawl_mode": "recursive" if recursive else "single_page",
                    "recursive_max_depth": recursive_max_depth,
                }
            )
            pages.append(
                {
                    "source_uri": page_url,
                    "source_type": "url",
                    "title": title,
                    "content": page_content,
                    "metadata": metadata,
                }
            )
        return pages

    def _extract_html_text(self, html: str) -> str:
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "lxml")
            text = soup.get_text("\n", strip=True)
        except Exception:
            text = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\n{3,}", "\n\n", text).strip()

    def _canonicalize_url(self, url: str) -> str:
        parts = urlsplit(url)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))

    def _build_route_path(self, root_url: str, page_url: str) -> str:
        root_parts = urlsplit(root_url)
        page_parts = urlsplit(page_url)
        root_path = root_parts.path.rstrip("/")
        page_path = page_parts.path
        route = page_path
        if root_path and page_path.startswith(root_path):
            route = page_path[len(root_path) :] or "/"
        if not route:
            route = "/"
        if page_parts.query:
            route = f"{route}?{page_parts.query}"
        return route

    def _build_url_document_id(self, page_url: str) -> str:
        digest = hashlib.sha1(page_url.encode("utf-8")).hexdigest()[:24]
        return f"url::{digest}"
