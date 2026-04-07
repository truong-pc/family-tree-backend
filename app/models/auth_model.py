from pydantic import BaseModel, EmailStr
from typing import Optional

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    accessToken: str
    refreshToken: str | None = None
    tokenType: str = "bearer"

class RefreshIn(BaseModel):
    refreshToken: str

class SessionOut(BaseModel):
    sessionId: str
    userAgent: Optional[str] = None
    ip: Optional[str] = None

class ChangePasswordIn(BaseModel):
    oldPassword: str
    newPassword: str

# Forgot Password / Reset Password models
class ForgotPasswordIn(BaseModel):
    email: EmailStr

class ResetPasswordIn(BaseModel):
    email: EmailStr
    otp: str
    newPassword: str
