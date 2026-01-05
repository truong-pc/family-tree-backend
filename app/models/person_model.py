from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import date

Gender = Literal["M", "F", "O"]

class PersonCreate(BaseModel):
    name: str
    gender: Gender
    level: int = Field(ge=0, description="Generational level; must be >= 0")  # user provides level explicitly
    dob: Optional[date] = None
    dod: Optional[date] = None
    description: Optional[str] = None
    photoUrl: Optional[str] = None
    parentIds: Optional[List[int]] = None

class PersonUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[Gender] = None
    level: Optional[int] = Field(default=None, ge=0, description="Generational level; must be >= 0")
    dob: Optional[date] = None
    dod: Optional[date] = None
    description: Optional[str] = None
    photoUrl: Optional[str] = None

class PersonOut(BaseModel):
    personId: int
    ownerId: str
    chartId: str
    name: str
    gender: Gender
    level: int
    dob: Optional[date] = None
    dod: Optional[date] = None
    description: Optional[str] = None
    photoUrl: Optional[str] = None

class TreeOut(BaseModel):
    nodes: list[dict]
    links: list[dict]
