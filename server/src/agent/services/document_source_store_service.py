"""Managed source storage for replayable document ingestion."""

from __future__ import annotations

import base64
import shutil
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from agent.config import get_settings


@dataclass(frozen=True)
class PreparedSource:
    """Normalized source information ready for parsing and replay."""

    load_source_uri: str
    display_source_uri: str
    source_name: str | None
    source_mime_type: str | None
    input_mode: str
    storage: dict[str, object]
    path_mapping: dict[str, str]
    load_options: dict[str, object]

    def to_state(self) -> dict[str, object]:
        """Convert to a graph-state friendly dictionary."""

        return {
            "prepared_source": {
                "load_source_uri": self.load_source_uri,
                "display_source_uri": self.display_source_uri,
                "source_name": self.source_name,
                "source_mime_type": self.source_mime_type,
                "input_mode": self.input_mode,
                "storage": self.storage,
                "path_mapping": self.path_mapping,
                "load_options": self.load_options,
            }
        }


class DocumentSourceStoreService:
    """Persist source files before parsing so reindex can replay them."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._root = Path(self._settings.source_storage_root).expanduser()
        if not self._root.is_absolute():
            self._root = Path(__file__).resolve().parents[3] / self._root

    def prepare_source(
        self,
        *,
        source_uri: str | None = None,
        source_name: str | None = None,
        source_content_b64: str | None = None,
        source_mime_type: str | None = None,
        backup_source: bool = True,
        recursive_url: bool | None = None,
        recursive_max_depth: int | None = None,
        recursive_prevent_outside: bool = True,
    ) -> PreparedSource:
        """Prepare a source into a replayable location and storage record."""

        if source_content_b64:
            filename = source_name or "uploaded_source.bin"
            payload = base64.b64decode(source_content_b64)
            staged = self._stage_bytes(filename, payload)
            storage = self._persist_storage_artifact(staged)
            display_source_uri = f"upload://{filename}"
            return PreparedSource(
                load_source_uri=str(staged),
                display_source_uri=display_source_uri,
                source_name=filename,
                source_mime_type=source_mime_type,
                input_mode="upload",
                storage=storage,
                path_mapping={str(staged): display_source_uri},
                load_options={},
            )

        if not source_uri:
            return PreparedSource(
                load_source_uri="",
                display_source_uri="",
                source_name=source_name,
                source_mime_type=source_mime_type,
                input_mode="empty",
                storage={},
                path_mapping={},
                load_options={},
            )

        display_source_uri = source_uri
        if source_uri.startswith("file://"):
            source_uri = source_uri.removeprefix("file://")

        if source_uri.startswith(("http://", "https://")):
            recursive_enabled = (
                self._settings.url_recursive_default_enabled
                if recursive_url is None
                else recursive_url
            )
            return PreparedSource(
                load_source_uri=source_uri,
                display_source_uri=display_source_uri,
                source_name=source_name,
                source_mime_type=source_mime_type,
                input_mode="url",
                storage={},
                path_mapping={},
                load_options={
                    "recursive_url": recursive_enabled,
                    "recursive_max_depth": int(
                        recursive_max_depth
                        if recursive_max_depth is not None
                        else self._settings.url_recursive_default_max_depth
                    ),
                    "recursive_prevent_outside": recursive_prevent_outside,
                    "recursive_timeout_seconds": self._settings.url_recursive_timeout_seconds,
                },
            )

        local_path = Path(source_uri)
        if local_path.exists() and local_path.is_file():
            if backup_source:
                staged = self._stage_file(local_path)
                storage = self._persist_storage_artifact(staged)
                return PreparedSource(
                    load_source_uri=str(staged),
                    display_source_uri=display_source_uri,
                    source_name=source_name or local_path.name,
                    source_mime_type=source_mime_type,
                    input_mode="file",
                    storage=storage,
                    path_mapping={str(staged): display_source_uri},
                    load_options={},
                )
            return PreparedSource(
                load_source_uri=str(local_path),
                display_source_uri=display_source_uri,
                source_name=source_name or local_path.name,
                source_mime_type=source_mime_type,
                input_mode="file",
                storage={},
                path_mapping={str(local_path): display_source_uri},
                load_options={},
            )

        if local_path.exists() and local_path.is_dir():
            if backup_source:
                staged_root, path_mapping = self._stage_directory(local_path)
                storage = self._persist_directory_artifacts(staged_root)
                return PreparedSource(
                    load_source_uri=str(staged_root),
                    display_source_uri=display_source_uri,
                    source_name=source_name or local_path.name,
                    source_mime_type=source_mime_type,
                    input_mode="directory",
                    storage=storage,
                    path_mapping=path_mapping,
                    load_options={},
                )
            return PreparedSource(
                load_source_uri=str(local_path),
                display_source_uri=display_source_uri,
                source_name=source_name or local_path.name,
                source_mime_type=source_mime_type,
                input_mode="directory",
                storage={},
                path_mapping={str(path): str(path) for path in local_path.rglob("*") if path.is_file()},
                load_options={},
            )

        return PreparedSource(
            load_source_uri=source_uri,
            display_source_uri=display_source_uri,
            source_name=source_name,
            source_mime_type=source_mime_type,
            input_mode="text",
            storage={},
            path_mapping={},
            load_options={},
        )

    def materialize_replay_source(self, document_record: dict[str, object] | None) -> str:
        """Resolve the replayable source for reindex, restoring from MinIO if needed."""

        if not document_record:
            return ""
        source_storage = document_record.get("source_storage") if isinstance(document_record, dict) else None
        source_storage_payload = source_storage if isinstance(source_storage, dict) else {}
        replay_source_uri = str(
            source_storage_payload.get("replay_source_uri") or document_record.get("source_uri") or ""
        )
        if not replay_source_uri:
            return ""
        if replay_source_uri.startswith(("http://", "https://")):
            return replay_source_uri
        replay_path = Path(replay_source_uri)
        if replay_path.exists():
            return str(replay_path)
        if source_storage_payload:
            return self._restore_from_storage(source_storage_payload, replay_path) or str(replay_path)
        return str(replay_path)

    def _stage_bytes(self, filename: str, payload: bytes) -> Path:
        directory = self._root / "uploads" / uuid4().hex
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / Path(filename).name
        target.write_bytes(payload)
        return target

    def _stage_file(self, source_path: Path) -> Path:
        directory = self._root / "files" / uuid4().hex
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / source_path.name
        shutil.copy2(source_path, target)
        return target

    def _stage_directory(self, source_directory: Path) -> tuple[Path, dict[str, str]]:
        directory = self._root / "directories" / uuid4().hex / source_directory.name
        path_mapping: dict[str, str] = {}
        for source_file in sorted(path for path in source_directory.rglob("*") if path.is_file()):
            relative_path = source_file.relative_to(source_directory)
            target = directory / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, target)
            path_mapping[str(target)] = str(source_file)
        return directory, path_mapping

    def _persist_storage_artifact(self, local_path: Path) -> dict[str, object]:
        storage = {
            "configured_backend": self._settings.source_storage_backend,
            "effective_backend": "local",
            "storage_uri": str(local_path),
            "local_path": str(local_path),
            "bucket": None,
            "object_key": None,
            "sync_status": "local_only",
        }
        if self._settings.source_storage_backend == "minio":
            remote = self._upload_file_to_minio(local_path)
            if remote:
                storage.update(remote)
        return storage

    def _persist_directory_artifacts(self, staged_root: Path) -> dict[str, object]:
        storage = {
            "configured_backend": self._settings.source_storage_backend,
            "effective_backend": "local",
            "storage_uri": str(staged_root),
            "local_path": str(staged_root),
            "bucket": None,
            "object_key": None,
            "sync_status": "local_only",
        }
        if self._settings.source_storage_backend == "minio":
            remote = self._upload_directory_to_minio(staged_root)
            if remote:
                storage.update(remote)
        return storage

    def _upload_file_to_minio(self, local_path: Path) -> dict[str, object] | None:
        client = self._build_minio_client()
        if client is None:
            return None
        try:
            bucket = self._settings.source_storage_bucket
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
            object_key = self._build_object_key(local_path.name)
            data = local_path.read_bytes()
            client.put_object(
                bucket,
                object_key,
                BytesIO(data),
                length=len(data),
                content_type=self._guess_content_type(local_path),
            )
            return {
                "effective_backend": "minio",
                "storage_uri": f"minio://{bucket}/{object_key}",
                "bucket": bucket,
                "object_key": object_key,
                "sync_status": "synced",
            }
        except Exception as exc:
            return {
                "effective_backend": "local",
                "sync_status": "local_fallback",
                "sync_error": str(exc),
            }

    def _upload_directory_to_minio(self, staged_root: Path) -> dict[str, object] | None:
        client = self._build_minio_client()
        if client is None:
            return None
        try:
            bucket = self._settings.source_storage_bucket
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
            object_prefix = self._build_object_key(staged_root.name)
            uploaded_count = 0
            for file_path in sorted(path for path in staged_root.rglob("*") if path.is_file()):
                relative_path = file_path.relative_to(staged_root).as_posix()
                object_key = f"{object_prefix}/{relative_path}"
                data = file_path.read_bytes()
                client.put_object(
                    bucket,
                    object_key,
                    BytesIO(data),
                    length=len(data),
                    content_type=self._guess_content_type(file_path),
                )
                uploaded_count += 1
            return {
                "effective_backend": "minio",
                "storage_uri": f"minio://{bucket}/{object_prefix}",
                "bucket": bucket,
                "object_key": object_prefix,
                "sync_status": "synced",
                "synced_file_count": uploaded_count,
            }
        except Exception as exc:
            return {
                "effective_backend": "local",
                "sync_status": "local_fallback",
                "sync_error": str(exc),
            }

    def _restore_from_storage(self, storage: dict[str, object], replay_path: Path) -> str | None:
        if storage.get("effective_backend") != "minio":
            return None
        bucket = storage.get("bucket")
        object_key = storage.get("object_key")
        if not isinstance(bucket, str) or not isinstance(object_key, str):
            return None
        client = self._build_minio_client()
        if client is None:
            return None
        try:
            if replay_path.suffix:
                replay_path.parent.mkdir(parents=True, exist_ok=True)
                client.fget_object(bucket, object_key, str(replay_path))
                return str(replay_path)
            replay_path.mkdir(parents=True, exist_ok=True)
            objects = client.list_objects(bucket, prefix=object_key, recursive=True)
            restored = False
            for obj in objects:
                relative = obj.object_name[len(object_key) :].lstrip("/")
                if not relative:
                    continue
                target = replay_path / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                client.fget_object(bucket, obj.object_name, str(target))
                restored = True
            return str(replay_path) if restored else None
        except Exception:
            return None

    def _build_minio_client(self):
        try:
            from minio import Minio
        except ImportError:
            return None
        parsed = urlparse(self._settings.source_storage_minio_endpoint)
        endpoint = parsed.netloc or parsed.path
        secure = (
            self._settings.source_storage_minio_secure
            if parsed.scheme == ""
            else parsed.scheme == "https"
        )
        return Minio(
            endpoint,
            access_key=self._settings.source_storage_minio_access_key,
            secret_key=self._settings.source_storage_minio_secret_key,
            secure=secure,
        )

    def _build_object_key(self, name: str) -> str:
        prefix = self._settings.source_storage_prefix.strip("/").replace("\\", "/")
        return f"{prefix}/{uuid4().hex}/{name}" if prefix else f"{uuid4().hex}/{name}"

    def _guess_content_type(self, path: Path) -> str:
        import mimetypes

        return mimetypes.guess_type(str(path))[0] or "application/octet-stream"
