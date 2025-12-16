from pydantic import BaseModel, EmailStr
from typing import Optional

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"

class RefreshIn(BaseModel):
    refresh_token: str

class SessionOut(BaseModel):
    sessionId: str
    userAgent: Optional[str] = None
    ip: Optional[str] = None

class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str
