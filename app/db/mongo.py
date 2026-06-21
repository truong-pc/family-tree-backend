from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class Mongo:
    client: AsyncIOMotorClient | None = None

mongo = Mongo()

async def connect_to_mongo():
    mongo.client = AsyncIOMotorClient(settings.MONGODB_URI)
    # Optionally: create indexes
    db = mongo.client[settings.MONGODB_DB]
    await db.users.create_index("email", unique=True)
    await db.charts_meta.create_index("ownerId")
    await db.charts_meta.create_index("editors")
    await db.sessions.create_index("userId")
    # Expire sessions after their expiration date
    await db.sessions.create_index("expiresAt", expireAfterSeconds=0)
    # Password reset tokens - index by email (unique)
    await db.password_reset_tokens.create_index("email", unique=True)
    # Events - index by chartId (family-wide custom events)
    await db.events.create_index("chartId")
    await db.events.create_index([("chartId", 1), ("month", 1), ("day", 1)])
    # News - public feed (cursor theo publishedAt, _id) + quản lý theo chart
    await db.news.create_index([("public", 1), ("publishedAt", -1), ("_id", -1)])
    await db.news.create_index([("chartId", 1), ("createdAt", -1)])
    await db.news.create_index("tags")
    return mongo.client

async def close_mongo():
    if mongo.client:
        mongo.client.close()
