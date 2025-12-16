from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.core.config import settings
from app.db.mongo import mongo
from datetime import datetime, timezone

bearer_scheme = HTTPBearer(bearerFormat="JWT", scheme_name="Authorization")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = await mongo.client[settings.MONGODB_DB].users.find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

async def get_chart_or_404(chart_id: str):
    chart = await mongo.client[settings.MONGODB_DB].charts_meta.find_one({"_id": chart_id})
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    owner = await mongo.client[settings.MONGODB_DB].users.find_one(
        {"_id": chart["ownerId"]},
        {"full_name": 1},
    )
    owner_name = owner.get("full_name") if owner else None
    return {**chart, "ownerName": owner_name}

def can_read(chart, user_id: str | None):
    return chart.get("published", True) or user_id == chart["ownerId"] or (user_id in chart.get("editors", []))

def can_write(chart, user_id: str):
    return (user_id == chart["ownerId"]) or (user_id in chart.get("editors", []))

def is_owner(chart, user_id: str):
    return user_id == chart["ownerId"]
