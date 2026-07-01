from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from app.utils.deps import get_current_user, get_chart_or_404, can_write
from app.models.person_model import FatherOfIn, MotherOfIn, SpouseOfIn
from app.services.relationship_service import (
    add_father_of, remove_father_of,
    add_mother_of, remove_mother_of,
    add_spouse_of, remove_spouse_of,
)
from app.realtime.publish import publish_tree_change
from app.realtime import events

router = APIRouter(prefix="/api/v1/charts/{chartId}/relationships", tags=["Relationships"])

@router.post("/father-of")
async def create_father_of(chartId: str, body: FatherOfIn, user=Depends(get_current_user),
                           x_client_id: Optional[str] = Header(default=None, alias="X-Client-Id")):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    await add_father_of(chartId, body.fatherId, body.childId, body.childOrder)
    await publish_tree_change(chartId, events.RELATIONSHIP_CREATED, user, x_client_id,
                              {"relType": "FATHER_OF", "source": body.fatherId, "target": body.childId,
                               "affectedPersonIds": [body.fatherId, body.childId]})
    return {"message": "FATHER_OF relationship created"}

@router.delete("/father-of")
async def delete_father_of(chartId: str, body: FatherOfIn, user=Depends(get_current_user),
                           x_client_id: Optional[str] = Header(default=None, alias="X-Client-Id")):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    await remove_father_of(chartId, body.fatherId, body.childId)
    await publish_tree_change(chartId, events.RELATIONSHIP_DELETED, user, x_client_id,
                              {"relType": "FATHER_OF", "source": body.fatherId, "target": body.childId,
                               "affectedPersonIds": [body.fatherId, body.childId]})
    return {"message": "FATHER_OF relationship removed"}

@router.post("/mother-of")
async def create_mother_of(chartId: str, body: MotherOfIn, user=Depends(get_current_user),
                           x_client_id: Optional[str] = Header(default=None, alias="X-Client-Id")):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    await add_mother_of(chartId, body.motherId, body.childId, body.childOrder)
    await publish_tree_change(chartId, events.RELATIONSHIP_CREATED, user, x_client_id,
                              {"relType": "MOTHER_OF", "source": body.motherId, "target": body.childId,
                               "affectedPersonIds": [body.motherId, body.childId]})
    return {"message": "MOTHER_OF relationship created"}

@router.delete("/mother-of")
async def delete_mother_of(chartId: str, body: MotherOfIn, user=Depends(get_current_user),
                           x_client_id: Optional[str] = Header(default=None, alias="X-Client-Id")):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    await remove_mother_of(chartId, body.motherId, body.childId)
    await publish_tree_change(chartId, events.RELATIONSHIP_DELETED, user, x_client_id,
                              {"relType": "MOTHER_OF", "source": body.motherId, "target": body.childId,
                               "affectedPersonIds": [body.motherId, body.childId]})
    return {"message": "MOTHER_OF relationship removed"}

@router.post("/spouse-of")
async def create_spouse_of(chartId: str, body: SpouseOfIn, user=Depends(get_current_user),
                           x_client_id: Optional[str] = Header(default=None, alias="X-Client-Id")):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    await add_spouse_of(chartId, body.person1Id, body.person2Id, body.spouseOrder)
    await publish_tree_change(chartId, events.RELATIONSHIP_CREATED, user, x_client_id,
                              {"relType": "SPOUSE_OF", "source": body.person1Id, "target": body.person2Id,
                               "affectedPersonIds": [body.person1Id, body.person2Id]})
    return {"message": "SPOUSE_OF relationship created"}

@router.delete("/spouse-of")
async def delete_spouse_of(chartId: str, body: SpouseOfIn, user=Depends(get_current_user),
                           x_client_id: Optional[str] = Header(default=None, alias="X-Client-Id")):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    await remove_spouse_of(chartId, body.person1Id, body.person2Id)
    await publish_tree_change(chartId, events.RELATIONSHIP_DELETED, user, x_client_id,
                              {"relType": "SPOUSE_OF", "source": body.person1Id, "target": body.person2Id,
                               "affectedPersonIds": [body.person1Id, body.person2Id]})
    return {"message": "SPOUSE_OF relationship removed"}
