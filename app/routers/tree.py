from fastapi import APIRouter, Depends, HTTPException
from app.utils.deps import get_current_user, get_chart_or_404, can_read
from app.services.tree_service import get_tree
from app.models.person_model import TreeOut

router = APIRouter(prefix="/api/v1/charts/{chartId}/tree", tags=["Tree"])

@router.get("", response_model=TreeOut)
async def get_tree_route(
    chartId: str,
    user = Depends(get_current_user),
):
    chart = await get_chart_or_404(chartId)
    if not can_read(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    data = await get_tree(chartId)
    # Output đúng format {"nodes": [...], "links": [...]}
    return data

@router.get("/published", response_model=TreeOut)
async def get_published_tree_route(chartId: str):
    # Public endpoint: only allow if chart is published
    chart = await get_chart_or_404(chartId)
    if not can_read(chart, None):
        raise HTTPException(status_code=403, detail="Forbidden")
    data = await get_tree(chartId)
    return data
