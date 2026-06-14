from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


def _normalize_tags(v):
    """Strip whitespace, drop empty strings, deduplicate while preserving order, and enforce a 50-character limit per tag."""
    if v is None:
        return v
    cleaned: list[str] = []
    for t in v:
        t = t.strip()
        if not t or t in cleaned:
            continue
        if len(t) > 50:
            raise ValueError("Each tag must be at most 50 characters")
        cleaned.append(t)
    return cleaned


class NewsCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    contentHtml: str = Field(min_length=1)
    coverImageUrl: Optional[str] = Field(default=None, max_length=2000)
    tags: list[str] = Field(default_factory=list, max_length=20)
    public: bool = False

    _clean_tags = field_validator("tags")(_normalize_tags)


class NewsUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    contentHtml: Optional[str] = Field(default=None, min_length=1)
    coverImageUrl: Optional[str] = Field(default=None, max_length=2000)
    tags: Optional[list[str]] = Field(default=None, max_length=20)
    public: Optional[bool] = None

    _clean_tags = field_validator("tags")(_normalize_tags)


class NewsOut(BaseModel):
    postId: str
    chartId: str
    authorId: str
    title: str
    contentHtml: str
    coverImageUrl: Optional[str] = None
    tags: list[str] = []
    public: bool
    publishedAt: Optional[datetime] = None
    createdAt: datetime
    updatedAt: datetime


class NewsCardOut(BaseModel):
    """Lightweight card for list/feed views — excludes contentHtml to keep the payload small."""
    postId: str
    chartId: str
    chartName: Optional[str] = None
    authorId: str
    authorName: Optional[str] = None
    title: str
    coverImageUrl: Optional[str] = None
    tags: list[str] = []
    public: bool
    publishedAt: Optional[datetime] = None
    createdAt: datetime
    updatedAt: datetime


class NewsFeedOut(BaseModel):
    items: list[NewsCardOut]
    nextCursor: Optional[str] = None
