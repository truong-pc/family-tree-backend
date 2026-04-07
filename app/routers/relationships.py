from fastapi import APIRouter, Depends, HTTPException
from app.utils.deps import get_current_user, get_chart_or_404, can_write
from app.models.person_model import ParentOfIn, SpouseOfIn
from app.services.relationship_service import add_parent_of, remove_parent_of, add_spouse_of, remove_spouse_of

router = APIRouter(prefix="/api/v1/charts/{chartId}/relationships", tags=["Relationships"])

@router.post("/parent-of")
async def create_parent_of(chartId: str, body: ParentOfIn, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    await add_parent_of(chartId, body.parentId, body.childId, body.childOrder)
    return {"message": "Relationship created"}

@router.delete("/parent-of")
async def delete_parent_of(chartId: str, body: ParentOfIn, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    await remove_parent_of(chartId, body.parentId, body.childId)
    return {"message": "Relationship removed"}

@router.post("/spouse-of")
async def create_spouse_of(chartId: str, body: SpouseOfIn, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    await add_spouse_of(chartId, body.person1Id, body.person2Id, body.order)
    return {"message": "Relationship created"}

@router.delete("/spouse-of")
async def delete_spouse_of(chartId: str, body: SpouseOfIn, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    await remove_spouse_of(chartId, body.person1Id, body.person2Id)
    return {"message": "Relationship removed"}
