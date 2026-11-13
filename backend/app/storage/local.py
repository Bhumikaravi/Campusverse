import os
import aiofiles
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, status
from app.config import settings
from .base import BaseStorage

class LocalStorage(BaseStorage):
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or settings.LOCAL_STORAGE_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def name(self) -> str:
        return "local"

    @property
    def supports_signed_urls(self) -> bool:
        return False

    def _resolve_safe_path(self, storage_key: str) -> Path:
        normalized = os.path.normpath(storage_key).lstrip("/\\")
        target = (self.base_dir / normalized).resolve()
        # Path traversal guard
        if not str(target).startswith(str(self.base_dir)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file storage path."
            )
        return target

    async def upload(self, storage_key: str, data: bytes, mime_type: str) -> str:
        target = self._resolve_safe_path(storage_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as f:
            f.write(data)
        return storage_key

    async def download(self, storage_key: str) -> bytes:
        target = self._resolve_safe_path(storage_key)
        if not target.exists() or not target.is_file():
            # Check sample_files directory
            sample_dir = Path(__file__).resolve().parent.parent.parent.parent / "sample_files"
            candidate = sample_dir / Path(storage_key).name
            if candidate.exists() and candidate.is_file():
                with open(candidate, "rb") as f:
                    return f.read()

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stored material file not found on disk."
            )
        with open(target, "rb") as f:
            return f.read()

    async def remove(self, storage_key: str) -> None:
        target = self._resolve_safe_path(storage_key)
        if target.exists() and target.is_file():
            target.unlink()

    async def get_signed_url(self, storage_key: str, expires_seconds: int = 60, filename: Optional[str] = None) -> str:
        # Not applicable for local storage, files are served via authenticated /download or /file endpoint
        raise NotImplementedError("Local storage does not provide external signed URLs.")
