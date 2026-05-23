from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)

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
    oldPassword: str = Field(..., min_length=6, max_length=128)
    newPassword: str = Field(..., min_length=6, max_length=128)

# Forgot Password / Reset Password models
class ForgotPasswordIn(BaseModel):
    email: EmailStr

class ResetPasswordIn(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=128)
    newPassword: str = Field(..., min_length=6, max_length=128)
