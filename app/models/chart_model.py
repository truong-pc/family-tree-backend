from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

class ChartCreate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class ChartUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    published: Optional[bool] = None

class ChartOut(BaseModel):
    chartId: str = Field(..., alias="_id")
    ownerId: str
    editors: list[str] = []
    ownerName: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    published: bool = True
    createdAt: datetime

    model_config = {"populate_by_name": True}

class EditorIn(BaseModel):
    email: EmailStr

class ChartPublicOut(BaseModel):
    chartId: str = Field(..., alias="_id")
    ownerId: str
    ownerName: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    createdAt: datetime

    model_config = {"populate_by_name": True}

class EditorBasicOut(BaseModel):
    userId: str = Field(..., alias="_id")
    fullName: Optional[str] = None  # MongoDB field renamed to fullName (no alias needed)
    email: EmailStr

    model_config = {"populate_by_name": True}
