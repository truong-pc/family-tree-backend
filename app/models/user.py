from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    # bcrypt only evaluates the first 72 bytes; enforce a safe max length = Field(..., min_length=6, max_length=72)
    password: str
    full_name: str
    phone: Optional[str] = None
    dob: Optional[str] = None

class UserOut(BaseModel):
    userId: str = Field(..., alias="_id")
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    dob: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime

class UserPublic(BaseModel):
    userId: str
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    dob: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    dob: Optional[str] = None
