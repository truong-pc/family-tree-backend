from pydantic import BaseModel, Field, model_validator
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
    fatherId: Optional[int] = None
    motherId: Optional[int] = None
    childOrder: Optional[int] = Field(default=None, ge=1, description="Birth order of child among siblings")
    
    @model_validator(mode="after")
    def check_at_least_one_parent(self):
        if self.fatherId is None and self.motherId is None:
            raise ValueError("At least one of fatherId or motherId must be provided")
        return self

class PersonCreateWithSpouse(PersonCreate):
    spouseId: int
    spouseOrder: Optional[int] = Field(default=None, ge=1, description="Marriage order")

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
    lunarDeathDay: Optional[int] = None
    lunarDeathMonth: Optional[int] = None
    lunarDeathYear: Optional[int] = None
    lunarIsLeap: Optional[bool] = None


# --- Relationship request models ---

class FatherOfIn(BaseModel):
    fatherId: int
    childId: int
    childOrder: Optional[int] = Field(default=None, ge=1, description="Birth order of child among siblings")

class MotherOfIn(BaseModel):
    motherId: int
    childId: int
    childOrder: Optional[int] = Field(default=None, ge=1, description="Birth order of child among siblings")

class SpouseOfIn(BaseModel):
    person1Id: int
    person2Id: int
    spouseOrder: Optional[int] = Field(default=None, ge=1, description="Marriage order")


# --- Person Detail response models ---

class ParentOfNodeOut(BaseModel):
    personId: int
    name: str
    gender: Gender
    birthOrder: Optional[int] = None

class SpouseOfNodeOut(BaseModel):
    personId: int
    name: str
    gender: Gender
    spouseOrder: Optional[int] = None

class ChildOfNodeOut(BaseModel):
    personId: int
    name: str
    gender: Gender
    childOrder: Optional[int] = None
    
class PersonDetailOut(PersonOut):
    parents: List[ParentOfNodeOut] = []
    spouses: List[SpouseOfNodeOut] = []
    children: List[ChildOfNodeOut] = []


# --- Tree response model ---

class TreeNode(BaseModel):
    id: int
    name: str
    gender: Gender
    level: int
    photoUrl: Optional[str] = None

class TreeLink(BaseModel):
    source: int
    target: int
    type: str

class TreeOut(BaseModel):
    nodes: list[TreeNode]
    links: list[TreeLink]
