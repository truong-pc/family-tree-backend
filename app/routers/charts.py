from fastapi import APIRouter, Depends, HTTPException
from app.models.chart_model import ChartCreate, ChartUpdate, ChartOut, EditorIn, ChartPublicOut, EditorBasicOut
from app.utils.deps import get_current_user, get_chart_or_404, can_read, is_owner
from app.db.mongo import mongo
from app.core.config import settings
from app.services.chart_service import create_chart_for_owner, delete_chart_hard, add_editor, get_editor_basic_by_id, list_edited_charts, remove_editor, list_published_charts_public

router = APIRouter(prefix="/api/v1", tags=["Charts"])

@router.post("/charts", response_model=ChartOut)
async def create_chart(data: ChartCreate, user=Depends(get_current_user)):
    doc = await create_chart_for_owner(user["_id"], data.name, data.description)
    return doc

@router.get("/charts/editor-name", response_model=EditorBasicOut)
async def get_editor_name(userId: str, _: dict = Depends(get_current_user)):
    doc = await get_editor_basic_by_id(userId)
    return doc

@router.get("/published-charts", response_model=list[ChartPublicOut])
async def list_published_charts():
    charts = await list_published_charts_public()
    if not charts:
        raise HTTPException(status_code=404, detail="No published charts")
    return charts

@router.get("/charts/mine", response_model=ChartOut)
async def my_chart(user=Depends(get_current_user)):
    chart = await mongo.client[settings.MONGODB_DB].charts_meta.find_one({"ownerId": user["_id"]})
    if not chart:
        raise HTTPException(status_code=404, detail="No chart for this user")
    return {**chart, "ownerName": user.get("full_name")}

@router.get("/charts/edited", response_model=list[ChartOut])
async def edited_charts(user=Depends(get_current_user)):
    """Return charts where the current user is an editor."""
    charts = await list_edited_charts(
        {"editors": user["_id"]},
        projection={
            "_id": 1,
            "ownerId": 1,
            "editors": 1,
            "ownerName": 1,
            "name": 1,
            "description": 1,
            "published": 1,
            "createdAt": 1,
        },
    )
    if not charts:
        raise HTTPException(status_code=404, detail="No invited edited charts for this user")
    return charts

@router.get("/charts/{chartId}", response_model=ChartOut)
async def get_chart(chartId: str, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_read(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    return chart

@router.patch("/charts/{chartId}", response_model=ChartOut)
async def update_my_chart(chartId: str, data: ChartUpdate, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not is_owner(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Only owner can update chart")
    patch = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    await mongo.client[settings.MONGODB_DB].charts_meta.update_one({"_id": chartId}, {"$set": patch})
    return await get_chart_or_404(chartId)

@router.delete("/charts/{chartId}")
async def delete_my_chart(chartId: str, user=Depends(get_current_user)):
    await delete_chart_hard(chartId, user["_id"])
    return {"message": "Chart deleted"}

@router.post("/charts/{chartId}/editors", response_model=ChartOut)
async def add_editor_route(chartId: str, body: EditorIn, user=Depends(get_current_user)):
    doc = await add_editor(chartId, user["_id"], body.email)
    return doc

@router.delete("/charts/{chartId}/editors/{email}", response_model=ChartOut)
async def remove_editor_route(chartId: str, email: str, user=Depends(get_current_user)):
    doc = await remove_editor(chartId, user["_id"], email)
    return doc
