from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import date

Gender = Literal["M", "F", "O"]

class PersonCreate(BaseModel):
    name: str
    gender: Gender
    level: int = Field(ge=0, description="Generational level; must be >= 0")
    dob: Optional[date] = None
    dod: Optional[date] = None
    description: Optional[str] = None
    photoUrl: Optional[str] = None

class PersonCreateWithParent(PersonCreate):
    parentId: int
    childOrder: Optional[int] = Field(default=None, ge=1, description="Birth order of child among siblings")

class PersonCreateWithSpouse(PersonCreate):
    spouseId: int
    order: Optional[int] = Field(default=None, ge=1, description="Marriage order")

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


# --- Relationship request models ---

class ParentOfIn(BaseModel):
    parentId: int
    childId: int
    childOrder: Optional[int] = Field(default=None, ge=1, description="Birth order of child among siblings")

class SpouseOfIn(BaseModel):
    person1Id: int
    person2Id: int
    order: Optional[int] = Field(default=None, ge=1, description="Marriage order")



# --- Tree response model ---

class TreeNode(BaseModel):
    id: int
    name: str
    gender: Gender
    level: int
    dob: Optional[str] = None
    dod: Optional[str] = None
    description: Optional[str] = None
    photoUrl: Optional[str] = None

class TreeLink(BaseModel):
    source: int
    target: int
    type: str
    childOrder: Optional[int] = None
    order: Optional[int] = None

class TreeOut(BaseModel):
    nodes: list[TreeNode]
    links: list[TreeLink]
