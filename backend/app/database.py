import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings

logger = logging.getLogger("campusverse.database")

class Database:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

db_instance = Database()

async def connect_db():
    timeout_sec = 5.0 if settings.is_production else 2.0
    timeout_ms = int(timeout_sec * 1000)
    uri = (settings.MONGODB_URI or "").strip()
    if not uri or (not uri.startswith("mongodb://") and not uri.startswith("mongodb+srv://")):
        logger.warning("No valid MONGODB_URI configured ('%s'). Using fallback database store.", uri)
        from app.mock_db import mock_db_instance
        db_instance.db = mock_db_instance
        return

    logger.info("Connecting to MongoDB at: %s", uri.split("@")[-1] if "@" in uri else uri)
    try:
        db_instance.client = AsyncIOMotorClient(
            uri,
            serverSelectionTimeoutMS=timeout_ms,
            connectTimeoutMS=timeout_ms
        )
        db_name = (settings.DB_NAME or "").strip() or "campusverse"
        db_instance.db = db_instance.client[db_name]
    except Exception as ce:
        logger.warning("Failed to initialize MongoDB client: %s. Using fallback database.", ce)
        from app.mock_db import mock_db_instance
        db_instance.db = mock_db_instance
        return
    
    # Ping database with adaptive timeout so server startup is never blocked
    try:
        await asyncio.wait_for(db_instance.db.command("ping"), timeout=timeout_sec)
        logger.info("Successfully connected to MongoDB database '%s'", settings.DB_NAME)
        # Create indexes
        await init_indexes()
    except Exception as e:
        logger.warning("MongoDB is unreachable (%s). Using fallback in-memory store so authentication & uploads work without crashing.", e)
        from app.mock_db import mock_db_instance
        db_instance.db = mock_db_instance

async def close_db():
    if db_instance.client:
        db_instance.client.close()
        logger.info("MongoDB connection closed")

async def init_indexes():
    try:
        users = db_instance.db["users"]
        await users.create_index("email", unique=True)
        await users.create_index("role")

        materials = db_instance.db["materials"]
        await materials.create_index([("status", 1), ("createdAt", -1)])
        await materials.create_index([("department", 1), ("semester", 1), ("subject", 1)])
        await materials.create_index("uploader")
        await materials.create_index("fileHash")
        await materials.create_index([("title", "text"), ("description", "text"), ("subject", "text")])

        reviews = db_instance.db["reviews"]
        await reviews.create_index([("materialId", 1), ("createdAt", -1)])
        
        bookmarks = db_instance.db["bookmarks"]
        await bookmarks.create_index([("userId", 1), ("materialId", 1)], unique=True)
        
        downloads = db_instance.db["downloads"]
        await downloads.create_index([("userId", 1), ("downloadedAt", -1)])

        chunks = db_instance.db["document_chunks"]
        await chunks.create_index("materialId")
        await chunks.create_index("uploader")
        await chunks.create_index("status")

        chapter_summaries = db_instance.db["chapter_summaries"]
        await chapter_summaries.create_index("materialId", unique=True)

        chat_sessions = db_instance.db["chat_sessions"]
        await chat_sessions.create_index([("userId", 1), ("updatedAt", -1)])

        chat_messages = db_instance.db["chat_messages"]
        await chat_messages.create_index([("sessionId", 1), ("createdAt", 1)])

        logger.info("Database indexes initialized successfully")
    except Exception as e:
        logger.warning("Index creation notice: %s", e)

def get_db():
    if db_instance.db is None:
        try:
            timeout_sec = 2.0
            timeout_ms = 2000
            db_instance.client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=timeout_ms,
                connectTimeoutMS=timeout_ms
            )
            db_instance.db = db_instance.client[settings.DB_NAME]
        except Exception:
            from app.mock_db import mock_db_instance
            return mock_db_instance
    return db_instance.db
