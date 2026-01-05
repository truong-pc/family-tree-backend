from fastapi import APIRouter, Depends, Request
from app.models.auth_model import LoginIn, TokenOut, RefreshIn, ChangePasswordIn
from app.models.user_model import UserCreate, UserOut, UserPublic, UserUpdate
from app.services.auth_service import register_user, login_user, refresh_access, logout, change_password, update_user_profile
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

@router.post("/register", response_model=UserPublic)
async def register(data: UserCreate):
    user = await register_user(data.email, data.password, data.full_name, data.phone, data.dob)
    return {
        "userId": user["_id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "phone": user.get("phone"),
        "dob": user.get("dob"),
    }

@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, request: Request):
    access, refresh, user = await login_user(
        data.email, data.password,
        user_agent=request.headers.get("User-Agent"),
        ip=request.client.host if request.client else None
    )
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}

@router.post("/refresh", response_model=TokenOut)
async def refresh(data: RefreshIn):
    new_access = await refresh_access(data.refresh_token)
    return {"access_token": new_access, "refresh_token": None, "token_type": "bearer"}

@router.post("/logout")
async def do_logout(data: RefreshIn):
    await logout(data.refresh_token)
    return {"message": "Logged out"}

@router.get("/me", response_model=UserPublic)
async def me(user = Depends(get_current_user)):
    return {
        "userId": user["_id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "phone": user.get("phone"),
        "dob": user.get("dob"),
    }

@router.post("/password/change")
async def password_change(data: ChangePasswordIn, user = Depends(get_current_user)):
    """Change user's password and revoke all sessions (all refresh tokens)."""
    await change_password(user["_id"], data.old_password, data.new_password)
    return {"message": "Password updated. All sessions revoked. Please login again."}

@router.put("/me", response_model=UserPublic)
async def update_me(data: UserUpdate, user = Depends(get_current_user)):
    """Update current user's profile fields (full_name, phone, dob)."""
    updated = await update_user_profile(user["_id"], data.full_name, data.phone, data.dob)
    return {
        "userId": updated["_id"],
        "email": updated["email"],
        "full_name": updated["full_name"],
        "phone": updated.get("phone"),
        "dob": updated.get("dob"),
    }
