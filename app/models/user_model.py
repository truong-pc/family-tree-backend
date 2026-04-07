from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    # bcrypt only evaluates the first 72 bytes; enforce a safe max length = Field(..., min_length=6, max_length=72)
    password: str
    fullName: str
    phone: Optional[str] = None
    dob: Optional[str] = None

class UserOut(BaseModel):
    userId: str = Field(..., alias="_id")
    email: EmailStr
    fullName: str
    phone: Optional[str] = None
    dob: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime

    model_config = {"populate_by_name": True}

class UserPublic(BaseModel):
    userId: str
    email: EmailStr
    fullName: str
    phone: Optional[str] = None
    dob: Optional[str] = None

class UserUpdate(BaseModel):
    fullName: Optional[str] = None
    phone: Optional[str] = None
    dob: Optional[str] = None
