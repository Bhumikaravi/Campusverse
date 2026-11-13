from typing import List, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os

class Settings(BaseSettings):
    ENVIRONMENT: Literal["development", "production", "test"] = "development"
    PORT: int = 5000
    CLIENT_URL: str = "http://localhost:5173,http://127.0.0.1:5173"
    
    # MongoDB Atlas / Local
    MONGODB_URI: str = "mongodb://localhost:27017/campusverse"
    DB_NAME: str = "campusverse"
    
    # Auth
    JWT_SECRET: str = "campusverse_super_secret_jwt_key_at_least_32_chars_long_2026"
    JWT_EXPIRES_DAYS: int = 7
    COOKIE_NAME: str = "cv_token"
    
    # Storage
    STORAGE_PROVIDER: Literal["local", "supabase", "cloudinary"] = "local"
    LOCAL_STORAGE_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 25
    
    # Supabase (Optional if STORAGE_PROVIDER != supabase)
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_BUCKET: str = "study-materials"
    
    # Cloudinary (Optional if STORAGE_PROVIDER != cloudinary)
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    
    # AI Moderation
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    
    # Publication policy & Scanning Booth Benchmarks
    AUTO_PUBLISH_AI_APPROVED: bool = True
    AUTO_PUBLISH_MIN_CONFIDENCE: float = 0.90
    MAX_DOCUMENT_PAGES: int = 150
    MAX_SUMMARY_WORDS: int = 500
    CONFIDENCE_HIGH_THRESHOLD: float = 0.80
    CONFIDENCE_MEDIUM_THRESHOLD: float = 0.50

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins(self) -> List[str]:
        return [url.strip() for url in self.CLIENT_URL.split(",") if url.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

settings = Settings()
