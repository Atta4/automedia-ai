from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from loguru import logger
from config.settings import get_settings

_client: AsyncIOMotorClient | None = None


async def get_db() -> AsyncIOMotorDatabase:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncIOMotorClient(settings.mongodb_uri)
        logger.info(f"MongoDB connected → {settings.mongodb_db}")
    return _client[get_settings().mongodb_db]


async def close_db():
    global _client
    if _client:
        _client.close()
        _client = None
        logger.info("MongoDB connection closed")


async def init_indexes():
    """Create all collection indexes on startup."""
    db = await get_db()

    await db.topics.create_index("keyword", unique=True)
    await db.topics.create_index("status")
    await db.topics.create_index("created_at")
    await db.topics.create_index("is_validated")

    await db.scripts.create_index("topic_keyword")
    await db.scripts.create_index("created_at")

    await db.videos.create_index("topic_keyword")
    await db.videos.create_index("status")

    logger.info("MongoDB indexes initialized")
