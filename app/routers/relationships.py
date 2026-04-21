from fastapi import APIRouter, Depends, HTTPException
from app.utils.deps import get_current_user, get_chart_or_404, can_write
from app.models.person_model import FatherOfIn, MotherOfIn, SpouseOfIn
from app.services.relationship_service import (
    add_father_of, remove_father_of,
    add_mother_of, remove_mother_of,
    add_spouse_of, remove_spouse_of,
)

router = APIRouter(prefix="/api/v1/charts/{chartId}/relationships", tags=["Relationships"])

@router.post("/father-of")
async def create_father_of(chartId: str, body: FatherOfIn, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    await add_father_of(chartId, body.fatherId, body.childId, body.childOrder)
    return {"message": "FATHER_OF relationship created"}

@router.delete("/father-of")
async def delete_father_of(chartId: str, body: FatherOfIn, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    await remove_father_of(chartId, body.fatherId, body.childId)
    return {"message": "FATHER_OF relationship removed"}

@router.post("/mother-of")
async def create_mother_of(chartId: str, body: MotherOfIn, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    await add_mother_of(chartId, body.motherId, body.childId, body.childOrder)
    return {"message": "MOTHER_OF relationship created"}

@router.delete("/mother-of")
async def delete_mother_of(chartId: str, body: MotherOfIn, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    await remove_mother_of(chartId, body.motherId, body.childId)
    return {"message": "MOTHER_OF relationship removed"}

@router.post("/spouse-of")
async def create_spouse_of(chartId: str, body: SpouseOfIn, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    await add_spouse_of(chartId, body.person1Id, body.person2Id, body.spouseOrder)
    return {"message": "SPOUSE_OF relationship created"}

@router.delete("/spouse-of")
async def delete_spouse_of(chartId: str, body: SpouseOfIn, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    await remove_spouse_of(chartId, body.person1Id, body.person2Id)
    return {"message": "SPOUSE_OF relationship removed"}
