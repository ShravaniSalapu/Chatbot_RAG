"""
MinIO / S3-compatible object storage with local-disk fallback.
"""

import os
import tempfile
from pathlib import Path
from typing import Optional

from app.config import get_settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class StorageClient:
    """Upload and download tenant document files."""

    def __init__(self):
        settings = get_settings()
        self._use_minio = settings.use_minio
        self._bucket = settings.minio_bucket
        self._client = None

        if self._use_minio:
            try:
                from minio import Minio

                self._client = Minio(
                    settings.minio_endpoint,
                    access_key=settings.minio_access_key,
                    secret_key=settings.minio_secret_key,
                    secure=settings.minio_secure,
                )
                if not self._client.bucket_exists(self._bucket):
                    self._client.make_bucket(self._bucket)
                logger.info(f"MinIO connected (bucket={self._bucket})")
            except Exception as exc:
                logger.warning(f"MinIO unavailable, using local disk: {exc}")
                self._use_minio = False
                self._client = None

        self._local_root = Path(os.getenv("DATA_DIR", "./data")) / "raw"
        self._local_root.mkdir(parents=True, exist_ok=True)

    @property
    def using_minio(self) -> bool:
        return self._use_minio and self._client is not None

    def ping(self) -> bool:
        if not self.using_minio:
            return self._local_root.exists()
        try:
            self._client.bucket_exists(self._bucket)
            return True
        except Exception:
            return False

    @staticmethod
    def build_object_key(tenant_id: str, document_id: str, filename: str) -> str:
        safe_name = Path(filename).name
        return f"{tenant_id}/{document_id}/{safe_name}"

    def upload_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Store file; returns storage key (MinIO object key or local path)."""
        if self.using_minio:
            from io import BytesIO

            self._client.put_object(
                self._bucket,
                key,
                BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
            logger.info(f"Uploaded to MinIO: {key}")
            return key

        local_path = self._local_root / key.replace("/", "_")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(data)
        logger.info(f"Saved locally: {local_path}")
        return str(local_path)

    def download_to_temp(self, storage_key: str) -> str:
        """Download object to a temporary file and return its path."""
        if self.using_minio and not Path(storage_key).is_file():
            suffix = Path(storage_key).suffix or ".bin"
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.close()
            self._client.fget_object(self._bucket, storage_key, tmp.name)
            return tmp.name

        path = Path(storage_key)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {storage_key}")
        return str(path)

    def delete_object(self, storage_key: str) -> bool:
        try:
            if self.using_minio and not Path(storage_key).is_file():
                self._client.remove_object(self._bucket, storage_key)
                return True
            path = Path(storage_key)
            if path.is_file():
                path.unlink()
            return True
        except Exception as exc:
            logger.warning(f"Could not delete storage object {storage_key}: {exc}")
            return False

    @staticmethod
    def cleanup_temp(path: str) -> None:
        try:
            p = Path(path)
            if p.exists() and str(tempfile.gettempdir()) in str(p):
                p.unlink()
        except Exception:
            pass


_storage_instance: Optional[StorageClient] = None


def get_storage() -> StorageClient:
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = StorageClient()
    return _storage_instance
