from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.models.person_model import PersonCreate, PersonCreateWithParent, PersonCreateWithSpouse, PersonUpdate, PersonOut, PersonDetailOut
from app.utils.deps import get_current_user, get_chart_or_404, can_write, can_read
from app.services.person_service import create_person, update_person, delete_person, get_person_detail, list_persons as list_persons_service
from app.services.relationship_service import add_father_of, add_mother_of, add_spouse_of, check_spouse_couple

router = APIRouter(prefix="/api/v1/charts/{chartId}/persons", tags=["Persons"])

@router.post("", response_model=PersonOut)
async def create_person_route(chartId: str, body: PersonCreate, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    node = await create_person(chartId, chart["ownerId"], body.name, body.gender, body.level, body.dob, body.dod, body.description, body.photoUrl)
    return node

@router.post("/add-child", response_model=PersonOut)
async def add_child_person_route(chartId: str, body: PersonCreateWithParent, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")

    # If both fatherId and motherId provided, validate they are a SPOUSE_OF couple
    if body.fatherId is not None and body.motherId is not None:
        is_couple = await check_spouse_couple(chartId, body.fatherId, body.motherId)
        if not is_couple:
            raise HTTPException(
                status_code=400,
                detail="Father and mother must be a married couple (SPOUSE_OF relationship required)"
            )

    # Create the child person
    node = await create_person(
        chartId, chart["ownerId"], body.name, body.gender, body.level,
        body.dob, body.dod, body.description, body.photoUrl
    )

    try:
        # Create FATHER_OF relationship if fatherId provided
        if body.fatherId is not None:
            await add_father_of(chartId, body.fatherId, node["personId"], body.childOrder)

        # Create MOTHER_OF relationship if motherId provided
        if body.motherId is not None:
            await add_mother_of(chartId, body.motherId, node["personId"], body.childOrder)
    except HTTPException:
        # Rollback: delete the orphan person node
        await delete_person(chartId, node["personId"])
        raise

    return node

@router.post("/add-spouse", response_model=PersonOut)
async def add_spouse_person_route(chartId: str, body: PersonCreateWithSpouse, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")

    node = await create_person(
        chartId, chart["ownerId"], body.name, body.gender, body.level,
        body.dob, body.dod, body.description, body.photoUrl
    )

    try:
        await add_spouse_of(chartId, body.spouseId, node["personId"], body.spouseOrder)
    except HTTPException:
        # Rollback: delete the orphan person node
        await delete_person(chartId, node["personId"])
        raise

    return node

@router.get("/{personId}", response_model=PersonDetailOut)
async def get_person_detail_route(chartId: str, personId: int, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_read(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    detail = await get_person_detail(chartId, personId)
    return detail

@router.get("")
async def list_persons_route(chartId: str, q: Optional[str] = Query(None), gender: Optional[str] = None, level: Optional[int] = None,
                             user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_read(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    nodes = await list_persons_service(chartId, q=q, gender=gender, level=level)
    return {"data": nodes}

@router.patch("/{personId}", response_model=PersonOut)
async def update_person_route(chartId: str, personId: int, body: PersonUpdate, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    node = await update_person(chartId, personId, body.model_dump(exclude_none=True))
    return node

@router.delete("/{personId}")
async def delete_person_route(chartId: str, personId: int, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    await delete_person(chartId, personId)
    return {"message": "Person deleted"}
