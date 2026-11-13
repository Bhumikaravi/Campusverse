import logging
from app.config import settings
from .base import BaseStorage
from .local import LocalStorage

logger = logging.getLogger("campusverse.storage")

_storage_instance: BaseStorage = None

def get_storage() -> BaseStorage:
    global _storage_instance
    if _storage_instance is not None:
        return _storage_instance

    provider = settings.STORAGE_PROVIDER.lower()
    if provider == "supabase":
        try:
            from .supabase_storage import SupabaseStorage
            _storage_instance = SupabaseStorage()
            logger.info("Using Supabase Storage provider")
            return _storage_instance
        except Exception as e:
            logger.warning("Could not initialize SupabaseStorage (%s). Falling back to LocalStorage.", e)

    elif provider == "cloudinary":
        try:
            from .cloudinary_storage import CloudinaryStorage
            _storage_instance = CloudinaryStorage()
            logger.info("Using Cloudinary Storage provider")
            return _storage_instance
        except Exception as e:
            logger.warning("Could not initialize CloudinaryStorage (%s). Falling back to LocalStorage.", e)

    _storage_instance = LocalStorage()
    logger.info("Using LocalStorage provider at '%s'", settings.LOCAL_STORAGE_DIR)
    return _storage_instance
