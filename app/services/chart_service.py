import uuid
from datetime import datetime, timezone
from typing import Any
from fastapi import HTTPException
from app.db.mongo import mongo
from app.core.config import settings
from app.db.neo4j import neo4j
from app.services.event_service import delete_events_by_chart
from app.services.news_service import delete_news_by_chart
from app.utils.cloudinary_helper import delete_images

def now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)

CHARTS = lambda: mongo.client[settings.MONGODB_DB].charts_meta

async def create_chart_for_owner(owner_id: str, name: str | None, description: str | None):
    existed = await CHARTS().find_one({"ownerId": owner_id})
    if existed:
        raise HTTPException(status_code=409, detail="User already has a chart")
    chart_id = str(uuid.uuid4())
    doc = {
        "_id": chart_id,
        "ownerId": owner_id,
        "editors": [],
        "name": name,
        "description": description,
        "published": True,  # mặc định
        "createdAt": now(),
    }
    await CHARTS().insert_one(doc)
    return doc

async def delete_chart_hard(chart_id: str, owner_id: str):
    chart = await CHARTS().find_one({"_id": chart_id})
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    if chart["ownerId"] != owner_id:
        raise HTTPException(status_code=403, detail="Only owner can delete chart")
    # Delete all nodes/edges in Neo4j. Grab every person's avatar URL first so we can clean
    # those up from Cloudinary afterwards.
    async with neo4j.driver.session() as session:
        res = await session.run(
            "MATCH (p:Person {chartId:$cid}) WHERE p.photoUrl IS NOT NULL RETURN p.photoUrl AS photo",
            cid=chart_id,
        )
        photos = [rec["photo"] async for rec in res]
        await session.run("MATCH (p:Person {chartId:$cid}) DETACH DELETE p", cid=chart_id)
        await session.run("MATCH (c:Counter {chartId:$cid}) DETACH DELETE c", cid=chart_id)
    if photos:
        await delete_images(photos)  
    # Events and news both key off chartId; news also owns Cloudinary images.
    await delete_events_by_chart(chart_id)
    await delete_news_by_chart(chart_id)
    await CHARTS().delete_one({"_id": chart_id})
    return True

async def add_editor(chart_id: str, owner_id: str, email: str):
    chart = await CHARTS().find_one({"_id": chart_id})
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    if chart["ownerId"] != owner_id:
        raise HTTPException(status_code=403, detail="Only owner can manage editors")

    # Find target user by email
    users_col = mongo.client[settings.MONGODB_DB].users
    target_user = await users_col.find_one({"email": email})
    if not target_user:
        raise HTTPException(status_code=404, detail="User with this email not found")

    target_user_id = target_user["_id"]
    if target_user_id == owner_id:
        return chart
    await CHARTS().update_one({"_id": chart_id}, {"$addToSet": {"editors": target_user_id}})
    return await CHARTS().find_one({"_id": chart_id})

async def remove_editor(chart_id: str, owner_id: str, email: str):
    chart = await CHARTS().find_one({"_id": chart_id})
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    if chart["ownerId"] != owner_id:
        raise HTTPException(status_code=403, detail="Only owner can manage editors")

    # Find target user by email
    users_col = mongo.client[settings.MONGODB_DB].users
    target_user = await users_col.find_one({"email": email})
    if not target_user:
        raise HTTPException(status_code=404, detail="User with this email not found")

    target_user_id = target_user["_id"]
    await CHARTS().update_one({"_id": chart_id}, {"$pull": {"editors": target_user_id}})
    return await CHARTS().find_one({"_id": chart_id})

async def list_published_charts_public() -> list[dict]:
    """Return published charts with a slim projection and ownerName from users.full_name.
    Fields: _id, ownerId, ownerName, name, description, createdAt
    """
    db = mongo.client[settings.MONGODB_DB]
    pipeline = [
        {"$match": {"published": True}},
        {"$lookup": {
            "from": "users",
            "localField": "ownerId",
            "foreignField": "_id",
            "as": "owner"
        }},
        {"$unwind": {"path": "$owner", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "_id": 1,
            "ownerId": 1,
            "ownerName": "$owner.fullName",
            "name": 1,
            "description": 1,
            "createdAt": 1,
        }}
    ]
    cursor = db.charts_meta.aggregate(pipeline)
    results = await cursor.to_list(length=1000)
    return results

async def list_edited_charts(match: dict[str, Any], projection: dict[str, Any] | None = None) -> list[dict]:
    """Return charts that match a filter, enriched with ownerName via aggregation."""
    pipeline: list[dict[str, Any]] = [
        {"$match": match},
        {"$lookup": {
            "from": "users",
            "localField": "ownerId",
            "foreignField": "_id",
            "as": "owner",
        }},
        {"$unwind": {"path": "$owner", "preserveNullAndEmptyArrays": True}},
        {"$addFields": {"ownerName": "$owner.fullName"}},
    ]
    if projection:
        pipeline.append({"$project": projection})
    cursor = CHARTS().aggregate(pipeline)
    return await cursor.to_list(length=1000)

async def get_editor_basic_by_id(user_id: str) -> dict:
    """Return user's id, full name, and email for editor display purposes."""
    doc = await mongo.client[settings.MONGODB_DB].users.find_one(
        {"_id": user_id},
        {"_id": 1, "fullName": 1, "email": 1},
    )
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    return doc
