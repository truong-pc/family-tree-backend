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
    await db.sessions.create_index("expires_at", expireAfterSeconds=0)
    # Password reset tokens - index by email (unique) and auto-expire
    await db.password_reset_tokens.create_index("email", unique=True)
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    return mongo.client

async def close_mongo():
    if mongo.client:
        mongo.client.close()
