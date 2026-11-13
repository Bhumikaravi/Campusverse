from abc import ABC, abstractmethod
from typing import Optional

class BaseStorage(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of storage provider ('local', 'supabase', 'cloudinary')"""
        pass

    @property
    @abstractmethod
    def supports_signed_urls(self) -> bool:
        """Whether provider supports temporary signed download URLs"""
        pass

    @abstractmethod
    async def upload(self, storage_key: str, data: bytes, mime_type: str) -> str:
        """Uploads file data and returns storage locator or URL"""
        pass

    @abstractmethod
    async def download(self, storage_key: str) -> bytes:
        """Downloads file binary buffer"""
        pass

    @abstractmethod
    async def remove(self, storage_key: str) -> None:
        """Deletes file binary from storage"""
        pass

    @abstractmethod
    async def get_signed_url(self, storage_key: str, expires_seconds: int = 60, filename: Optional[str] = None) -> str:
        """Returns temporary download link"""
        pass
