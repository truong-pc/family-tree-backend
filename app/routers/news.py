from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from app.models.news_model import NewsCreate, NewsUpdate, NewsOut, NewsCardOut, NewsFeedOut, NewsTagOut
from app.utils.deps import get_current_user, get_chart_or_404, can_write, can_modify_news
from app.services.news_service import (
    list_public_feed, list_public_tags, get_public_post,
    list_chart_news, create_news, get_chart_post, get_post_raw,
    update_news, delete_news,
)

router = APIRouter(prefix="/api/v1", tags=["News"])


# --- Public news feed (no authentication required) ---

@router.get("/news", response_model=NewsFeedOut)
async def public_feed_route(
    limit: int = Query(20, ge=1, le=50),
    cursor: Optional[str] = None,
    chartId: Optional[str] = None,
    tag: Optional[str] = None,
):
    return await list_public_feed(limit, cursor, chartId, tag)


@router.get("/news/tags", response_model=list[NewsTagOut])
async def public_tags_route():
    return await list_public_tags()


@router.get("/news/{postId}", response_model=NewsOut)
async def public_post_route(postId: str):
    return await get_public_post(postId)


# --- Chart-scoped news management (requires login, owner or editor role) ---

@router.get("/charts/{chartId}/news", response_model=list[NewsCardOut])
async def list_chart_news_route(
    chartId: str,
    mine: bool = False,
    public: Optional[bool] = None,
    tag: Optional[str] = None,
    user=Depends(get_current_user),
):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    author_id = user["_id"] if mine else None
    return await list_chart_news(chartId, author_id, public, tag)


@router.post("/charts/{chartId}/news", response_model=NewsOut)
async def create_news_route(chartId: str, body: NewsCreate, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    return await create_news(chartId, user["_id"], body)


@router.get("/charts/{chartId}/news/{postId}", response_model=NewsOut)
async def get_chart_news_route(chartId: str, postId: str, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    return await get_chart_post(chartId, postId)


@router.patch("/charts/{chartId}/news/{postId}", response_model=NewsOut)
async def update_news_route(chartId: str, postId: str, body: NewsUpdate, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    post = await get_post_raw(chartId, postId)
    if not can_modify_news(chart, post, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    patch = body.model_dump(exclude_unset=True)
    return await update_news(chartId, postId, patch)


@router.delete("/charts/{chartId}/news/{postId}")
async def delete_news_route(chartId: str, postId: str, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    post = await get_post_raw(chartId, postId)
    if not can_modify_news(chart, post, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    await delete_news(chartId, postId)
    return {"message": "News post deleted"}
