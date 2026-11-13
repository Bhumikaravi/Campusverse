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
    logger.info("Connecting to MongoDB at: %s", settings.MONGODB_URI.split("@")[-1] if "@" in settings.MONGODB_URI else settings.MONGODB_URI)
    db_instance.client = AsyncIOMotorClient(
        settings.MONGODB_URI,
        serverSelectionTimeoutMS=timeout_ms,
        connectTimeoutMS=timeout_ms
    )
    db_instance.db = db_instance.client[settings.DB_NAME]
    
    # Ping database with adaptive timeout so server startup is never blocked
    try:
        await asyncio.wait_for(db_instance.db.command("ping"), timeout=timeout_sec)
        logger.info("Successfully connected to MongoDB database '%s'", settings.DB_NAME)
        # Create indexes
        await init_indexes()
    except Exception as e:
        logger.warning("MongoDB connection could not be established: %s", e)
        raise

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

def get_db() -> AsyncIOMotorDatabase:
    if db_instance.db is None:
        timeout_sec = 5.0 if settings.is_production else 2.0
        timeout_ms = int(timeout_sec * 1000)
        db_instance.client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=timeout_ms,
            connectTimeoutMS=timeout_ms
        )
        db_instance.db = db_instance.client[settings.DB_NAME]
    return db_instance.db
