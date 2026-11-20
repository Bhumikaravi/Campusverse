"""
GridFS Storage Adapter for CampusVerse
=======================================
Stores uploaded study material files directly inside MongoDB Atlas using GridFS.
This avoids the need for external storage services (Supabase, Cloudinary, S3).

GridFS splits files into 255 KB chunks and stores them in two collections:
  - fs.files  — file metadata (name, size, mime type, upload date)
  - fs.chunks — raw binary chunks

Requirements: motor>=3.7.0, pymongo>=4.11.0 (already in requirements.txt)

Configuration (set in Render Environment Variables):
  STORAGE_PROVIDER=gridfs
  MONGODB_URI=mongodb+srv://...   (same Atlas URI used for the main database)
  DB_NAME=campusverse             (GridFS lives in this same database)
"""

import logging
import io
from typing import Optional

from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from app.config import settings
from app.database import db_instance
from .base import BaseStorage

logger = logging.getLogger("campusverse.gridfs_storage")


class GridFSStorage(BaseStorage):
    """
    Stores files in MongoDB Atlas via GridFS.
    Reuses the existing Motor database connection — no new connection needed.
    """

    def __init__(self):
        # Validation: requires a real MongoDB URI (not localhost for production)
        uri = (settings.MONGODB_URI or "").strip()
        if not uri or not (uri.startswith("mongodb://") or uri.startswith("mongodb+srv://")):
            raise ValueError(
                "GridFS storage requires a valid MONGODB_URI. "
                "Set MONGODB_URI=mongodb+srv://... in your environment variables."
            )

    def _get_bucket(self) -> AsyncIOMotorGridFSBucket:
        """Returns the Motor GridFS bucket, reusing the existing DB connection."""
        db = db_instance.db
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database is not connected. Cannot access file storage."
            )
        return AsyncIOMotorGridFSBucket(db, bucket_name="study_files")

    @property
    def name(self) -> str:
        return "gridfs"

    @property
    def supports_signed_urls(self) -> bool:
        # GridFS serves files through the FastAPI /file and /download endpoints
        return False

    async def upload(self, storage_key: str, data: bytes, mime_type: str) -> str:
        """
        Uploads file bytes to GridFS.
        storage_key is used as the GridFS filename so it can be retrieved later.
        Returns the storage_key unchanged (consistent with other adapters).
        """
        try:
            bucket = self._get_bucket()

            # Remove any existing file with the same storage_key to avoid duplicates
            await self._delete_by_filename(bucket, storage_key)

            # Upload the new file
            stream = io.BytesIO(data)
            await bucket.upload_from_stream(
                filename=storage_key,
                source=stream,
                metadata={
                    "contentType": mime_type,
                    "storageKey": storage_key,
                    "provider": "gridfs"
                }
            )

            logger.info("GridFS upload successful: %s (%d bytes, %s)", storage_key, len(data), mime_type)
            return storage_key

        except HTTPException:
            raise
        except Exception as e:
            logger.error("GridFS upload failed for '%s': %s", storage_key, e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"File storage upload failed: {str(e)}"
            )

    async def download(self, storage_key: str) -> bytes:
        """
        Downloads file bytes from GridFS by storage_key (filename).
        """
        try:
            bucket = self._get_bucket()
            stream = io.BytesIO()
            await bucket.download_to_stream_by_name(storage_key, stream)
            data = stream.getvalue()

            if not data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Stored file is empty or not found in GridFS."
                )

            logger.debug("GridFS download successful: %s (%d bytes)", storage_key, len(data))
            return data

        except HTTPException:
            raise
        except Exception as e:
            err_str = str(e).lower()
            if "not found" in err_str or "no file" in err_str or "gridout" in err_str:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Material file not found in GridFS storage."
                )
            logger.error("GridFS download failed for '%s': %s", storage_key, e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"File retrieval error: {str(e)}"
            )

    async def remove(self, storage_key: str) -> None:
        """
        Deletes a file from GridFS by storage_key (filename).
        Silently succeeds if the file does not exist.
        """
        try:
            bucket = self._get_bucket()
            await self._delete_by_filename(bucket, storage_key)
            logger.info("GridFS delete successful: %s", storage_key)
        except HTTPException:
            pass
        except Exception as e:
            logger.warning("GridFS delete notice for '%s': %s", storage_key, e)

    async def get_signed_url(self, storage_key: str, expires_seconds: int = 60, filename: Optional[str] = None) -> str:
        """
        GridFS does not support pre-signed URLs.
        Files are served through FastAPI's authenticated /file and /download endpoints.
        """
        raise NotImplementedError(
            "GridFS storage does not support signed URLs. "
            "Files are served through FastAPI /api/materials/{id}/file and /api/materials/{id}/download."
        )

    @staticmethod
    async def _delete_by_filename(bucket: AsyncIOMotorGridFSBucket, filename: str) -> None:
        """Deletes all GridFS files matching the given filename."""
        try:
            async for grid_file in bucket.find({"filename": filename}):
                await bucket.delete(grid_file._id)
        except Exception:
            pass  # File may not exist — that's fine
