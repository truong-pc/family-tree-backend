from datetime import date, datetime, timedelta, timezone
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException
from app.utils.amlichcalendar import Solar

from app.core.config import settings
from app.db.mongo import mongo
from app.db.neo4j import neo4j
from app.models.event_model import EventCreate, _validate_date_combo
from app.utils.lunar_converter import lunar_to_solar, get_leap_month


def _events_coll():
    return mongo.client[settings.MONGODB_DB].events


def _doc_to_out(doc) -> dict:
    return {
        "eventId": str(doc["_id"]),
        "chartId": doc["chartId"],
        "createdBy": doc["createdBy"],
        "title": doc["title"],
        "description": doc.get("description"),
        "day": doc["day"],
        "month": doc["month"],
        "year": doc["year"],
        "calendar": doc["calendar"],
        "repeat": doc["repeat"],
        "isLeapMonth": doc.get("isLeapMonth", False),
        "createdAt": doc["createdAt"],
        "updatedAt": doc["updatedAt"],
    }


def _parse_object_id(eventId: str) -> ObjectId:
    try:
        return ObjectId(eventId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid eventId")


# --- CRUD custom event ---

async def create_event(chartId: str, createdBy: str, body: EventCreate) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        "chartId": chartId,
        "createdBy": createdBy,
        "title": body.title,
        "description": body.description,
        "day": body.day,
        "month": body.month,
        "year": body.year,
        "calendar": body.calendar,
        "repeat": body.repeat,
        "isLeapMonth": body.isLeapMonth,
        "createdAt": now,
        "updatedAt": now,
    }
    res = await _events_coll().insert_one(doc)
    doc["_id"] = res.inserted_id
    return _doc_to_out(doc)


async def get_event(chartId: str, eventId: str) -> dict:
    oid = _parse_object_id(eventId)
    doc = await _events_coll().find_one({"_id": oid, "chartId": chartId})
    if not doc:
        raise HTTPException(status_code=404, detail="Event not found")
    return _doc_to_out(doc)


async def update_event(chartId: str, eventId: str, patch: dict) -> dict:
    if not patch:
        raise HTTPException(status_code=400, detail="Nothing to update")
    oid = _parse_object_id(eventId)
    existing = await _events_coll().find_one({"_id": oid, "chartId": chartId})
    if not existing:
        raise HTTPException(status_code=404, detail="Event not found")

    merged = {**existing, **patch}
    try:
        _validate_date_combo(
            merged["year"], merged["month"], merged["day"],
            merged["calendar"], merged.get("isLeapMonth", False),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    patch["updatedAt"] = datetime.now(timezone.utc)
    await _events_coll().update_one({"_id": oid}, {"$set": patch})
    doc = await _events_coll().find_one({"_id": oid})
    return _doc_to_out(doc)


async def delete_event(chartId: str, eventId: str) -> bool:
    oid = _parse_object_id(eventId)
    res = await _events_coll().delete_one({"_id": oid, "chartId": chartId})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return True


async def list_custom(chartId: str) -> list[dict]:
    cursor = _events_coll().find({"chartId": chartId})
    return [_doc_to_out(doc) async for doc in cursor]


# --- Master list (3 sources merged) ---

async def _list_person_events(chartId: str) -> tuple[list[dict], list[dict]]:
    """Return (birthdays, deaths) extracted from Neo4j persons in the chart.
    Birthday is omitted for deceased persons (per Vietnamese tradition)."""
    async with neo4j.driver.session() as session:
        res = await session.run(
            """
            MATCH (n:Person {chartId:$cid})
            RETURN n.personId AS personId, n.name AS name,
                   toString(n.dob) AS dob, toString(n.dod) AS dod,
                   n.lunarDeathDay AS ld, n.lunarDeathMonth AS lm,
                   n.lunarDeathYear AS ly, n.lunarIsLeap AS leap
            """,
            cid=chartId,
        )
        records = await res.data()

    births, deaths = [], []
    for r in records:
        pid = r["personId"]
        name = r["name"]
        dob, dod = r["dob"], r["dod"]
        # Birthday: only living persons
        if dob and not dod:
            try:
                d = date.fromisoformat(dob)
                births.append({
                    "type": "birthday",
                    "sourceId": f"birthday-{pid}",
                    "title": f"Sinh nhật {name}",
                    "day": d.day,
                    "month": d.month,
                    "year": d.year,
                    "calendar": "solar",
                    "repeat": "yearly",
                    "isLeapMonth": False,
                    "personId": pid,
                    "description": None,
                })
            except (ValueError, TypeError):
                pass
        # Death anniversary: lunar fields are auto-computed when dod is set
        if dod and r["ld"] is not None and r["lm"] is not None and r["ly"] is not None:
            deaths.append({
                "type": "death",
                "sourceId": f"death-{pid}",
                "title": f"Giỗ {name}",
                "day": int(r["ld"]),
                "month": int(r["lm"]),
                "year": int(r["ly"]),
                "calendar": "lunar",
                "repeat": "yearly",
                "isLeapMonth": bool(r["leap"]) if r["leap"] is not None else False,
                "personId": pid,
                "description": None,
            })
    return births, deaths


async def list_master(chartId: str) -> list[dict]:
    births, deaths = await _list_person_events(chartId)
    custom_docs = await list_custom(chartId)
    customs = []
    for c in custom_docs:
        customs.append({
            "type": "custom",
            "sourceId": c["eventId"],
            "title": c["title"],
            "day": c["day"],
            "month": c["month"],
            "year": c["year"],
            "calendar": c["calendar"],
            "repeat": c["repeat"],
            "isLeapMonth": c.get("isLeapMonth", False),
            "personId": None,
            "description": c.get("description"),
        })
    return births + deaths + customs


# --- Upcoming expansion ---

def _solar_candidate(year: int, month: int, day: int) -> Optional[date]:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _lunar_candidate(lunar_year: int, month: int, day: int, is_leap: bool) -> Optional[date]:
    """Convert a yearly lunar anchor to a solar date.
    Fallback rule: if is_leap=True but the year lacks that leap month, use the regular month.
    Returns None when the lunar date does not exist that year (e.g. day 30 in 29-day month)."""
    try:
        if is_leap and get_leap_month(lunar_year) != month:
            return lunar_to_solar(lunar_year, month, day, False)
        return lunar_to_solar(lunar_year, month, day, is_leap)
    except ValueError:
        return None


def _expand(ev: dict, today: date, end: date) -> Optional[dict]:
    cal, repeat = ev["calendar"], ev["repeat"]

    if repeat == "once":
        if cal == "solar":
            occ = _solar_candidate(ev["year"], ev["month"], ev["day"])
        else:
            occ = _lunar_candidate(ev["year"], ev["month"], ev["day"], ev["isLeapMonth"])
        if occ and today <= occ <= end:
            return {**ev, "occurrenceDate": occ, "daysUntil": (occ - today).days}
        return None

    # yearly
    if cal == "solar":
        for year in (today.year, today.year + 1):
            occ = _solar_candidate(year, ev["month"], ev["day"])
            if occ and today <= occ <= end:
                return {**ev, "occurrenceDate": occ, "daysUntil": (occ - today).days}
        return None

    # lunar yearly: scan lunar years that could land in the solar window
    today_ly = Solar.fromYmd(today.year, today.month, today.day).getLunar().getYear()
    end_ly = Solar.fromYmd(end.year, end.month, end.day).getLunar().getYear()
    for ly in range(today_ly, end_ly + 2):
        occ = _lunar_candidate(ly, ev["month"], ev["day"], ev["isLeapMonth"])
        if occ and today <= occ <= end:
            return {**ev, "occurrenceDate": occ, "daysUntil": (occ - today).days}
    return None


async def list_upcoming(chartId: str, days: int) -> list[dict]:
    today = date.today()
    end = today + timedelta(days=days)
    master = await list_master(chartId)
    expanded = [out for ev in master if (out := _expand(ev, today, end))]
    expanded.sort(key=lambda e: (e["occurrenceDate"], e["title"]))
    return expanded
