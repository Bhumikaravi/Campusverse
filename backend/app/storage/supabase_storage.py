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
                file_options={"content-type": mime_type, "upsert": "true"}
            )
            logger.info("Supabase upload successful: key='%s', size=%d bytes, mime='%s'", storage_key, len(data), mime_type)
            return storage_key
        except Exception as e:
            logger.error("Supabase upload failed for key '%s': %s", storage_key, e)
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
            # supabase-py v2 returns {"signedUrl": "..."} directly
            # supabase-py v1 returns {"signedURL": "..."} (uppercase L)
            # Some versions wrap in {"data": {"signedUrl": "..."}}
            signed_url = None
            if isinstance(res, dict):
                signed_url = (
                    res.get("signedUrl")
                    or res.get("signedURL")
                    or (res.get("data") or {}).get("signedUrl")
                    or (res.get("data") or {}).get("signedURL")
                )
            if not signed_url:
                logger.error("Supabase signed URL response missing expected key. Response keys: %s", list(res.keys()) if isinstance(res, dict) else type(res).__name__)
                raise ValueError(
                    f"Signed URL not returned by Supabase. "
                    f"Response keys: {list(res.keys()) if isinstance(res, dict) else type(res).__name__}"
                )
            logger.info("Supabase signed URL generated for key='%s', expires=%ds", storage_key, expires_seconds)
            return signed_url
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to generate Supabase signed URL for key '%s': %s", storage_key, e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not generate secure download link."
            )
