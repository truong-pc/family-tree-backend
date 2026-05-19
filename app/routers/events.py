from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from app.models.event_model import (
    EventCreate, EventUpdate, EventOut, MasterEventOut, UpcomingEventOut,
)
from app.utils.deps import get_current_user, get_chart_or_404, can_read, can_write
from app.services.event_service import (
    create_event, update_event, delete_event,
    list_master, list_upcoming,
)

router = APIRouter(prefix="/api/v1/charts/{chartId}/events", tags=["Events"])


@router.get("", response_model=List[MasterEventOut])
async def list_events_route(chartId: str, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_read(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    return await list_master(chartId)


@router.get("/upcoming", response_model=List[UpcomingEventOut])
async def list_upcoming_route(
    chartId: str,
    days: int = Query(7, ge=0, le=366),
    user=Depends(get_current_user),
):
    chart = await get_chart_or_404(chartId)
    if not can_read(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    return await list_upcoming(chartId, days)


@router.post("", response_model=EventOut)
async def create_event_route(chartId: str, body: EventCreate, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    return await create_event(chartId, user["_id"], body)


@router.patch("/{eventId}", response_model=EventOut)
async def update_event_route(chartId: str, eventId: str, body: EventUpdate, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    patch = body.model_dump(exclude_unset=True)
    return await update_event(chartId, eventId, patch)


@router.delete("/{eventId}")
async def delete_event_route(chartId: str, eventId: str, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    await delete_event(chartId, eventId)
    return {"message": "Event deleted"}
