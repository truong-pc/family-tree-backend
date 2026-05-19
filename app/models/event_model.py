from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal
from datetime import date, datetime

Calendar = Literal["solar", "lunar"]
Repeat = Literal["once", "yearly"]
EventType = Literal["birthday", "death", "custom"]


def _validate_date_combo(year: int, month: int, day: int, calendar: str, is_leap: bool):
    """Validate that (year, month, day, calendar, isLeap) is a real calendar date."""
    if calendar == "solar":
        if is_leap:
            raise ValueError("isLeapMonth chỉ áp dụng cho lịch âm")
        date(year, month, day)
    else:
        from app.utils.lunar_converter import lunar_to_solar
        lunar_to_solar(year, month, day, is_leap)


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    day: int = Field(ge=1, le=30)
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=1900, le=2200)
    calendar: Calendar
    repeat: Repeat
    isLeapMonth: bool = False

    @model_validator(mode="after")
    def check_date(self):
        _validate_date_combo(self.year, self.month, self.day, self.calendar, self.isLeapMonth)
        return self


class EventUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    day: Optional[int] = Field(default=None, ge=1, le=30)
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
