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


#Forgot Password / Reset Password

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
    token_record = await PASSWORD_RESET_TOKENS().find_one({"email": email})
    today = get_today_date()
    current_time = now()
    
    if token_record:
        last_attempt_date = token_record.get("last_attempt_date")
        daily_attempts = token_record.get("daily_attempts", 0)
        last_otp_sent_at = token_record.get("last_otp_sent_at")
        # Ensure last_otp_sent_at is timezone-aware
        if last_otp_sent_at and last_otp_sent_at.tzinfo is None:
            last_otp_sent_at = last_otp_sent_at.replace(tzinfo=timezone.utc)

        # Step A: Check Daily Limit
        if last_attempt_date:
            # Convert to date if it's datetime
            if isinstance(last_attempt_date, datetime):
                last_attempt_date = last_attempt_date.date()
            
            if last_attempt_date == today:
                # Same day - check if limit reached
                if daily_attempts >= OTP_DAILY_LIMIT:
                    raise HTTPException(
                        status_code=429,
                        detail="Daily limit reached. Please try again tomorrow."
                    )
            else:
                # New day - reset counter
                daily_attempts = 0
        
        # Step B: Check Cooldown (60 seconds)
        if last_otp_sent_at:
            time_since_last = (current_time - last_otp_sent_at).total_seconds()
            if time_since_last < OTP_COOLDOWN_SECONDS:
                raise HTTPException(
                    status_code=429,
                    detail=f"Please wait 1 minute before resending."
                )
    else:
        daily_attempts = 0
    
    # Step C: Success Case - Generate and send OTP
    otp = generate_otp()
    expires_at = current_time + timedelta(minutes=OTP_EXPIRE_MINUTES)
    
    # Send OTP email
    email_sent = await send_otp_email(email, otp)
    if not email_sent:
        raise HTTPException(status_code=500, detail="Failed to send OTP email. Please try again.")
    
    # Update or insert token record
    update_data = {
        "email": email,
        "otp": otp,
        "expires_at": expires_at,
        "last_otp_sent_at": current_time,
        "daily_attempts": daily_attempts + 1,
        "last_attempt_date": datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc),
        "otp_attempts": 0,
        "created_at": current_time if not token_record else token_record.get("created_at", current_time),
        "updated_at": current_time,
    }
    
    await PASSWORD_RESET_TOKENS().update_one(
        {"email": email},
        {"$set": update_data},
        upsert=True
    )
    
    return {"message": "OTP sent to your email", "expires_in_minutes": OTP_EXPIRE_MINUTES}


async def reset_password_with_otp(email: str, otp: str, new_password: str) -> dict:
    """
    Reset password using OTP.
    """
    # Verifies OTP, updates password, and deletes the used OTP.
    # Find the token record
    token_record = await PASSWORD_RESET_TOKENS().find_one({"email": email})
    
    if not token_record:
        raise HTTPException(status_code=400, detail="No OTP request found for this email")
    
    # Check if OTP exists
    if not token_record.get("otp"):
        raise HTTPException(status_code=400, detail="No active OTP. try a new one.")
    
    # Check if OTP is expired
    expires_at = token_record.get("expires_at")
    if expires_at:
        # Ensure expires_at is timezone-aware for comparison
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now() > expires_at:  
            raise HTTPException(status_code=400, detail="OTP has expired. try a new one.")
    
    # Check OTP attempt limit (prevent brute force)
    otp_attempts = token_record.get("otp_attempts", 0)
    if otp_attempts >= 5:
        # Invalidate OTP after too many failed attempts
        await PASSWORD_RESET_TOKENS().update_one(
            {"email": email},
            {"$unset": {"otp": "", "expires_at": ""}}
        )
        raise HTTPException(
            status_code=429,
            detail="Too many failed attempts."
        )
    
    # Check if OTP matches
    if token_record.get("otp") != otp:
        # Increment failed attempt counter
        await PASSWORD_RESET_TOKENS().update_one(
            {"email": email},
            {"$inc": {"otp_attempts": 1}}
        )
        remaining_attempts = 4 - otp_attempts
        raise HTTPException(
            status_code=400,
            detail=f"Invalid OTP. {remaining_attempts} attempts remaining."
        )
    
    # Find the user
    user = await USERS().find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update the user's password
    await USERS().update_one(
        {"_id": user["_id"]},
        {"$set": {"passwordHash": hash_password(new_password), "updatedAt": now()}}
    )
    
    # Revoke all sessions for this user (security measure)
    await SESS().delete_many({"userId": user["_id"]})
    
    # Delete the used OTP record
    await PASSWORD_RESET_TOKENS().delete_one({"email": email})
    
    return {"message": "Password reset successfully. Please login with your new password."}

