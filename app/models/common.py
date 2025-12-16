from pydantic import BaseModel, Field
from typing import Optional

class APIMessage(BaseModel):
    message: str

class Pagination(BaseModel):
    limit: int = 50
    cursor: Optional[str] = None
