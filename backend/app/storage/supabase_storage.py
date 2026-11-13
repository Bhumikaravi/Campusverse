import logging
from typing import Optional
from supabase import create_client, Client
from fastapi import HTTPException, status
from app.config import settings
from .base import BaseStorage

logger = logging.getLogger("campusverse.supabase")

class SupabaseStorage(BaseStorage):
    def __init__(self):
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        self.bucket = settings.SUPABASE_BUCKET

    @property
    def name(self) -> str:
        return "supabase"

    @property
    def supports_signed_urls(self) -> bool:
        return True

    async def upload(self, storage_key: str, data: bytes, mime_type: str) -> str:
        try:
            self.client.storage.from_(self.bucket).upload(
                path=storage_key,
                file=data,
                file_options={"content-type": mime_type, "upsert": "false"}
            )
            return storage_key
        except Exception as e:
            logger.error("Supabase upload failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Cloud storage upload failed: {str(e)}"
            )

    async def download(self, storage_key: str) -> bytes:
        try:
            res = self.client.storage.from_(self.bucket).download(storage_key)
            return res
        except Exception as e:
            logger.error("Supabase download failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material file not found in cloud storage."
            )

    async def remove(self, storage_key: str) -> None:
        try:
            self.client.storage.from_(self.bucket).remove([storage_key])
        except Exception as e:
            logger.warning("Supabase file removal notice: %s", e)

    async def get_signed_url(self, storage_key: str, expires_seconds: int = 60, filename: Optional[str] = None) -> str:
        try:
            options = {"download": filename} if filename else {}
            res = self.client.storage.from_(self.bucket).create_signed_url(
                path=storage_key,
                expires_in=expires_seconds,
                options=options
            )
            signed_url = res.get("signedURL") or res.get("signedUrl")
            if not signed_url:
                raise ValueError("Signed URL was not returned by Supabase")
            return signed_url
        except Exception as e:
            logger.error("Failed to generate Supabase signed URL: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not generate secure download link."
            )
