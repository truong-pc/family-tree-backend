import uuid
import random
from datetime import datetime, timedelta, timezone, date
from fastapi import HTTPException
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.config import settings
from app.db.mongo import mongo
from app.utils.email import send_otp_email

def now():
    return datetime.now(timezone.utc)

USERS = lambda: mongo.client[settings.MONGODB_DB].users
SESS = lambda: mongo.client[settings.MONGODB_DB].sessions
PASSWORD_RESET_TOKENS = lambda: mongo.client[settings.MONGODB_DB].password_reset_tokens

async def register_user(email: str, password: str, fullName: str, phone: str | None, dob: str | None):
    exists = await USERS().find_one({"email": email})
    if exists:
        raise HTTPException(status_code=409, detail="Email already registered")
    userId = str(uuid.uuid4())
    doc = {
        "_id": userId,
        "email": email,
        "passwordHash": hash_password(password),
        "fullName": fullName,
        "phone": phone,
        "dob": dob,
        "createdAt": now(),
        "updatedAt": now(),
    }
    await USERS().insert_one(doc)
    return doc

async def login_user(email: str, password: str, userAgent: str | None, ip: str | None):
    user = await USERS().find_one({"email": email})
    if not user or not verify_password(password, user["passwordHash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access = create_access_token(user["_id"])
    refresh = create_refresh_token(user["_id"])
    sessId = str(uuid.uuid4())
    await SESS().insert_one({
        "_id": sessId,
        "userId": user["_id"],
        "refreshToken": refresh,
        "userAgent": userAgent,
        "ip": ip,
        "createdAt": now(),
        "expiresAt": now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    })
    return access, refresh, user

async def refresh_access(refreshToken: str):
    sess = await SESS().find_one({"refreshToken": refreshToken})
    if not sess:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    newAccess = create_access_token(sess["userId"])
    await SESS().update_one({"_id": sess["_id"]}, {"$set": {"expiresAt": now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)}})
    return newAccess

async def logout(refreshToken: str):
    res = await SESS().delete_one({"refreshToken": refreshToken})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Session not found")
    return True

async def change_password(userId: str, oldPassword: str, newPassword: str):
    """Change user's password and revoke all existing refresh tokens (all sessions)."""
    user = await USERS().find_one({"_id": userId})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(oldPassword, user["passwordHash"]):
        raise HTTPException(status_code=400, detail="Old password is incorrect")

    # Revoke all sessions/refresh tokens for this user
    await SESS().delete_many({"userId": userId})

    # Update password hash
    await USERS().update_one(
        {"_id": userId},
        {"$set": {"passwordHash": hash_password(newPassword), "updatedAt": now()}}
    )

    return True

async def update_user_profile(userId: str, fullName: str | None = None, phone: str | None = None, dob: str | None = None):
    user = await USERS().find_one({"_id": userId})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updateFields = {}
    if fullName is not None:
        updateFields["fullName"] = fullName
    if phone is not None:
        updateFields["phone"] = phone
    if dob is not None:
        updateFields["dob"] = dob

    if not updateFields:
        return user

    updateFields["updatedAt"] = now()
    await USERS().update_one({"_id": userId}, {"$set": updateFields})
    newUser = await USERS().find_one({"_id": userId})
    return newUser


# Forgot Password / Reset Password

OTP_EXPIRE_MINUTES = 10
OTP_COOLDOWN_SECONDS = 60
OTP_DAILY_LIMIT = 5


def generate_otp() -> str:
    """Generate a 6-digit random OTP."""
    return str(random.randint(100000, 999999))


def get_today_date() -> date:
    """Get today's date in UTC."""
    return datetime.now(timezone.utc).date()


async def request_password_reset(email: str) -> dict:
    """
    Handle forgot password request with rate limiting.
    Rate limiting rules:
    - Max 5 OTP requests per day per email
    - 60 seconds cooldown between requests
    """
    # Check if user exists
    user = await USERS().find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User with this email does not exist")

    # Get existing token record for this email
    tokenRecord = await PASSWORD_RESET_TOKENS().find_one({"email": email})
    today = get_today_date()
    currentTime = now()

    if tokenRecord:
        lastAttemptDate = tokenRecord.get("lastAttemptDate")
        dailyAttempts = tokenRecord.get("dailyAttempts", 0)
        lastOtpSentAt = tokenRecord.get("lastOtpSentAt")
        # Ensure lastOtpSentAt is timezone-aware
        if lastOtpSentAt and lastOtpSentAt.tzinfo is None:
            lastOtpSentAt = lastOtpSentAt.replace(tzinfo=timezone.utc)

        # Step A: Check Daily Limit
        if lastAttemptDate:
            # Convert to date if it's datetime
            if isinstance(lastAttemptDate, datetime):
                lastAttemptDate = lastAttemptDate.date()

            if lastAttemptDate == today:
                # Same day - check if limit reached
                if dailyAttempts >= OTP_DAILY_LIMIT:
                    raise HTTPException(
                        status_code=429,
                        detail="Daily limit reached. Please try again tomorrow."
                    )
            else:
                # New day - reset counter
                dailyAttempts = 0

        # Step B: Check Cooldown (60 seconds)
        if lastOtpSentAt:
            timeSinceLast = (currentTime - lastOtpSentAt).total_seconds()
            if timeSinceLast < OTP_COOLDOWN_SECONDS:
                raise HTTPException(
                    status_code=429,
                    detail=f"Please wait 1 minute before resending."
                )
    else:
        dailyAttempts = 0

    # Step C: Success Case - Generate and send OTP
    otp = generate_otp()
    expiresAt = currentTime + timedelta(minutes=OTP_EXPIRE_MINUTES)

    # Send OTP email
    emailSent = await send_otp_email(email, otp)
    if not emailSent:
        raise HTTPException(status_code=500, detail="Failed to send OTP email. Please try again.")

    # Update or insert token record
    updateData = {
        "email": email,
        "otp": otp,
        "expiresAt": expiresAt,
        "lastOtpSentAt": currentTime,
        "dailyAttempts": dailyAttempts + 1,
        "lastAttemptDate": datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc),
        "otpAttempts": 0,
        "createdAt": currentTime if not tokenRecord else tokenRecord.get("createdAt", currentTime),
        "updatedAt": currentTime,
    }

    await PASSWORD_RESET_TOKENS().update_one(
        {"email": email},
        {"$set": updateData},
        upsert=True
    )

    return {"message": "OTP sent to your email", "expiresInMinutes": OTP_EXPIRE_MINUTES}


async def reset_password_with_otp(email: str, otp: str, newPassword: str) -> dict:
    """
    Reset password using OTP.
    """
    # Verifies OTP, updates password, and deletes the used OTP.
    # Find the token record
    tokenRecord = await PASSWORD_RESET_TOKENS().find_one({"email": email})

    if not tokenRecord:
        raise HTTPException(status_code=400, detail="No OTP request found for this email")

    # Check if OTP exists
    if not tokenRecord.get("otp"):
        raise HTTPException(status_code=400, detail="No active OTP. try a new one.")

    # Check if OTP is expired
    expiresAt = tokenRecord.get("expiresAt")
    if expiresAt:
        # Ensure expiresAt is timezone-aware for comparison
        if expiresAt.tzinfo is None:
            expiresAt = expiresAt.replace(tzinfo=timezone.utc)
        if now() > expiresAt:
            raise HTTPException(status_code=400, detail="OTP has expired. try a new one.")

    # Check OTP attempt limit (prevent brute force)
    # Reset attempts if it's a new day
    lastOtpAttemptDate = tokenRecord.get("lastOtpAttemptDate")
    currentDate = get_today_date()

    if lastOtpAttemptDate:
        if isinstance(lastOtpAttemptDate, datetime):
            lastOtpAttemptDate = lastOtpAttemptDate.date()

        if lastOtpAttemptDate != currentDate:
            # New day - reset OTP attempts
            await PASSWORD_RESET_TOKENS().update_one(
                {"email": email},
                {"$set": {"otpAttempts": 0, "lastOtpAttemptDate": datetime.combine(currentDate, datetime.min.time(), tzinfo=timezone.utc)}}
            )
            tokenRecord["otpAttempts"] = 0

    otpAttempts = tokenRecord.get("otpAttempts", 0)
    if otpAttempts >= 5:
        # Invalidate OTP after too many failed attempts
        await PASSWORD_RESET_TOKENS().update_one(
            {"email": email},
            {"$unset": {"otp": "", "expiresAt": ""}}
        )
        raise HTTPException(
            status_code=429,
            detail="Too many failed attempts."
        )

    # Check if OTP matches
    if tokenRecord.get("otp") != otp:
        # Increment failed attempt counter and update last attempt date
        await PASSWORD_RESET_TOKENS().update_one(
            {"email": email},
            {
                "$inc": {"otpAttempts": 1},
                "$set": {"lastOtpAttemptDate": datetime.combine(currentDate, datetime.min.time(), tzinfo=timezone.utc)}
            }
        )
        remainingAttempts = 4 - otpAttempts
        raise HTTPException(
            status_code=400,
            detail=f"Invalid OTP. {remainingAttempts} attempts remaining."
        )

    # Find the user
    user = await USERS().find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update the user's password
    await USERS().update_one(
        {"_id": user["_id"]},
        {"$set": {"passwordHash": hash_password(newPassword), "updatedAt": now()}}
    )

    # Revoke all sessions for this user (security measure)
    await SESS().delete_many({"userId": user["_id"]})

    # Delete the used OTP record
    await PASSWORD_RESET_TOKENS().delete_one({"email": email})

    return {"message": "Password reset successfully. Please login with your new password."}
