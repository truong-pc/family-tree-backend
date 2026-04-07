from fastapi import APIRouter, Depends, Request
from app.models.auth_model import LoginIn, TokenOut, RefreshIn, ChangePasswordIn, ForgotPasswordIn, ResetPasswordIn
from app.models.user_model import UserCreate, UserOut, UserPublic, UserUpdate
from app.services.auth_service import register_user, login_user, refresh_access, logout, change_password, update_user_profile, request_password_reset, reset_password_with_otp
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

@router.post("/register", response_model=UserPublic)
async def register(data: UserCreate):
    user = await register_user(data.email, data.password, data.fullName, data.phone, data.dob)
    return {
        "userId": user["_id"],
        "email": user["email"],
        "fullName": user["fullName"],
        "phone": user.get("phone"),
        "dob": user.get("dob"),
    }

@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, request: Request):
    access, refresh, user = await login_user(
        data.email, data.password,
        userAgent=request.headers.get("User-Agent"),
        ip=request.client.host if request.client else None
    )
    return {"accessToken": access, "refreshToken": refresh, "tokenType": "bearer"}

@router.post("/refresh", response_model=TokenOut)
async def refresh(data: RefreshIn):
    newAccess = await refresh_access(data.refreshToken)
    return {"accessToken": newAccess, "refreshToken": None, "tokenType": "bearer"}

@router.post("/logout")
async def do_logout(data: RefreshIn):
    await logout(data.refreshToken)
    return {"message": "Logged out"}

@router.get("/me", response_model=UserPublic)
async def me(user = Depends(get_current_user)):
    return {
        "userId": user["_id"],
        "email": user["email"],
        "fullName": user["fullName"],
        "phone": user.get("phone"),
        "dob": user.get("dob"),
    }

@router.post("/password/change")
async def password_change(data: ChangePasswordIn, user = Depends(get_current_user)):
    """Change user's password and revoke all sessions (all refresh tokens)."""
    await change_password(user["_id"], data.oldPassword, data.newPassword)
    return {"message": "Password updated. All sessions revoked. Please login again."}

@router.put("/me", response_model=UserPublic)
async def update_me(data: UserUpdate, user = Depends(get_current_user)):
    """Update current user's profile fields (fullName, phone, dob)."""
    updated = await update_user_profile(user["_id"], data.fullName, data.phone, data.dob)
    return {
        "userId": updated["_id"],
        "email": updated["email"],
        "fullName": updated["fullName"],
        "phone": updated.get("phone"),
        "dob": updated.get("dob"),
    }

@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordIn):
    """
    Request password reset OTP.

    Rate limiting:
    - Max 5 requests per day
    - 60 seconds cooldown between requests
    """
    result = await request_password_reset(data.email)
    return result

@router.post("/reset-password")
async def reset_password(data: ResetPasswordIn):
    """
    Reset password using OTP.
    
    Verifies OTP and updates password. All existing sessions will be revoked.
    """
    result = await reset_password_with_otp(data.email, data.otp, data.newPassword)
    return result
