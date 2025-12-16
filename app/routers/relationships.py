from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.utils.deps import get_current_user, get_chart_or_404, can_write
from app.services.relationship_service import add_parent_of, remove_parent_of

router = APIRouter(prefix="/api/v1/charts/{chartId}/relationships", tags=["Relationships"])

class ParentOfIn(BaseModel):
    parentId: int
    childId: int

@router.post("/parent-of")
async def create_parent_of(chartId: str, body: ParentOfIn, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    await add_parent_of(chartId, body.parentId, body.childId)
    return {"message": "Relationship created"}

@router.delete("/parent-of")
async def delete_parent_of(chartId: str, body: ParentOfIn, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    await remove_parent_of(chartId, body.parentId, body.childId)
    return {"message": "Relationship removed"}
