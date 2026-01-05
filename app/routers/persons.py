from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.models.person_model import PersonCreate, PersonUpdate, PersonOut
from app.utils.deps import get_current_user, get_chart_or_404, can_write, can_read
from app.services.person_service import create_person, update_person, delete_person
from app.db.neo4j import neo4j

router = APIRouter(prefix="/api/v1/charts/{chartId}/persons", tags=["Persons"])

@router.post("", response_model=PersonOut)
async def create_person_route(chartId: str, body: PersonCreate, user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    if not can_write(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    node = await create_person(chartId, chart["ownerId"], body.name, body.gender, body.level, body.dob, body.dod, body.description, body.photoUrl, body.parentIds)
    return node

@router.get("")
async def list_persons(chartId: str, q: Optional[str] = Query(None), gender: Optional[str] = None, level: Optional[int] = None,
                       user=Depends(get_current_user)):
    chart = await get_chart_or_404(chartId)
    # Check read permissions only owner/editors or published
    if not can_read(chart, user["_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    where = "n.chartId = $cid"
    params = {"cid": chartId}
    if q:
        where += " AND toLower(n.name) CONTAINS toLower($q)"
        params["q"] = q
    if gender:
        where += " AND n.gender = $g"
        params["g"] = gender
    if level is not None:
        where += " AND n.level = $lvl"
        params["lvl"] = level

    async with neo4j.driver.session() as session:
        res = await session.run(
            f"""MATCH (n:Person) WHERE {where} 
            RETURN {{
                personId: n.personId,
                ownerId: n.ownerId,
                chartId: n.chartId,
                name: n.name,
                gender: n.gender,
                level: n.level,
                dob: toString(n.dob),
                dod: toString(n.dod),
                description: n.description,
                photoUrl: n.photoUrl
            }} AS n 
            ORDER BY n.level ASC, n.name ASC""", 
            **params
        )
        records = await res.data()
        nodes = [r["n"] for r in records]
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
