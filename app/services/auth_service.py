import uuid
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.config import settings
from app.db.mongo import mongo

def now():
    return datetime.now(timezone.utc)

USERS = lambda: mongo.client[settings.MONGODB_DB].users
SESS = lambda: mongo.client[settings.MONGODB_DB].sessions

async def register_user(email: str, password: str, full_name: str, phone: str | None, dob: str | None):
    exists = await USERS().find_one({"email": email})
    if exists:
        raise HTTPException(status_code=409, detail="Email already registered")
    user_id = str(uuid.uuid4())
    doc = {
        "_id": user_id,
        "email": email,
        "passwordHash": hash_password(password),
        "full_name": full_name,
        "phone": phone,
        "dob": dob,
        "createdAt": now(),
        "updatedAt": now(),
    }
    await USERS().insert_one(doc)
    return doc

async def login_user(email: str, password: str, user_agent: str | None, ip: str | None):
    user = await USERS().find_one({"email": email})
    if not user or not verify_password(password, user["passwordHash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access = create_access_token(user["_id"])
    refresh = create_refresh_token(user["_id"])
    sess_id = str(uuid.uuid4())
    await SESS().insert_one({
        "_id": sess_id,
        "userId": user["_id"],
        "refreshToken": refresh,  # (đơn giản: lưu plain, có thể hash nếu muốn)
        "userAgent": user_agent,
        "ip": ip,
        "createdAt": now(),
        "expiresAt": now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    })
    return access, refresh, user

async def refresh_access(refresh_token: str):
    sess = await SESS().find_one({"refreshToken": refresh_token})
    if not sess:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    # optionally: check exp by decoding; đơn giản hóa: tạo access mới
    new_access = create_access_token(sess["userId"])
    await SESS().update_one({"_id": sess["_id"]}, {"$set": {"expiresAt": now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)}})
    return new_access

async def logout(refresh_token: str):
    res = await SESS().delete_one({"refreshToken": refresh_token})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Session not found")
    return True

async def change_password(user_id: str, old_password: str, new_password: str):
    """Change user's password and revoke all existing refresh tokens (all sessions)."""
    user = await USERS().find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(old_password, user["passwordHash"]):
        raise HTTPException(status_code=400, detail="Old password is incorrect")

    # Revoke all sessions/refresh tokens for this user
    await SESS().delete_many({"userId": user_id})

    # Update password hash
    await USERS().update_one(
        {"_id": user_id},
        {"$set": {"passwordHash": hash_password(new_password), "updatedAt": now()}}
    )

    return True

async def update_user_profile(user_id: str, full_name: str | None = None, phone: str | None = None, dob: str | None = None):
    user = await USERS().find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_fields = {}
    if full_name is not None:
        update_fields["full_name"] = full_name
    if phone is not None:
        update_fields["phone"] = phone
    if dob is not None:
        update_fields["dob"] = dob

    if not update_fields:
        # Nothing to update
        return user

    update_fields["updatedAt"] = now()
    await USERS().update_one({"_id": user_id}, {"$set": update_fields})
    # Return fresh document
    new_user = await USERS().find_one({"_id": user_id})
    return new_user
