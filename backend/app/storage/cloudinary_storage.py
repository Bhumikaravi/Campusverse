import logging
from typing import Optional
import httpx
import cloudinary
import cloudinary.uploader
import cloudinary.utils
from fastapi import HTTPException, status
from app.config import settings
from .base import BaseStorage

logger = logging.getLogger("campusverse.cloudinary")

class CloudinaryStorage(BaseStorage):
    def __init__(self):
        if not settings.CLOUDINARY_CLOUD_NAME or not settings.CLOUDINARY_API_KEY or not settings.CLOUDINARY_API_SECRET:
            raise ValueError("Cloudinary credentials must be set in .env")
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True
        )

    @property
    def name(self) -> str:
        return "cloudinary"

    @property
    def supports_signed_urls(self) -> bool:
        return True

    async def upload(self, storage_key: str, data: bytes, mime_type: str) -> str:
        try:
            res_type = "image" if mime_type.startswith("image/") else "raw"
            result = cloudinary.uploader.upload(
                data,
                public_id=storage_key,
                resource_type=res_type,
                type="authenticated"
            )
            return result.get("public_id", storage_key)
        except Exception as e:
            logger.error("Cloudinary upload error: %s", e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Cloudinary upload failed: {str(e)}"
            )

    async def download(self, storage_key: str) -> bytes:
        try:
            url = await self.get_signed_url(storage_key, expires_seconds=120)
            async with httpx.AsyncClient() as client:
                res = await client.get(url)
                if res.status_code != 200:
                    raise ValueError(f"Download HTTP {res.status_code}")
                return res.content
        except Exception as e:
            logger.error("Cloudinary download error: %s", e)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material file could not be retrieved from Cloudinary."
            )

    async def remove(self, storage_key: str) -> None:
        try:
            cloudinary.uploader.destroy(storage_key, resource_type="raw", type="authenticated")
        except Exception as e:
            logger.warning("Cloudinary destroy notice: %s", e)

    async def get_signed_url(self, storage_key: str, expires_seconds: int = 60, filename: Optional[str] = None) -> str:
        try:
            url, _ = cloudinary.utils.cloudinary_url(
                storage_key,
                resource_type="raw",
                type="authenticated",
                sign_url=True,
                attachment=filename or True
            )
            return url
        except Exception as e:
            logger.error("Cloudinary URL signing error: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not generate secure Cloudinary link."
            )
