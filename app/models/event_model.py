from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date, datetime

Calendar = Literal["solar", "lunar"]
Repeat = Literal["once", "yearly"]
EventType = Literal["birthday", "death", "custom"]


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    day: int = Field(ge=1, le=31)
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=1900, le=2200)
    calendar: Calendar
    repeat: Repeat
    isLeapMonth: bool = False


class EventUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    day: Optional[int] = Field(default=None, ge=1, le=31)
    month: Optional[int] = Field(default=None, ge=1, le=12)
    year: Optional[int] = Field(default=None, ge=1900, le=2200)
    calendar: Optional[Calendar] = None
    repeat: Optional[Repeat] = None
    isLeapMonth: Optional[bool] = None


class EventOut(BaseModel):
    eventId: str
    chartId: str
    createdBy: str
    title: str
    description: Optional[str] = None
    day: int
    month: int
    year: int
    calendar: Calendar
    repeat: Repeat
    isLeapMonth: bool = False
    createdAt: datetime
    updatedAt: datetime


class MasterEventOut(BaseModel):
    type: EventType
    sourceId: str
    title: str
    day: int
    month: int
    year: int
    calendar: Calendar
    repeat: Repeat
    isLeapMonth: bool = False
    personId: Optional[int] = None
    description: Optional[str] = None


class UpcomingEventOut(MasterEventOut):
    occurrenceDate: date
    daysUntil: int
