from fastapi import HTTPException
from app.db.neo4j import neo4j
from datetime import date
from app.utils.lunar_converter import solar_to_lunar
try:  # neo4j driver date type
    from neo4j.time import Date as Neo4jDate  # type: ignore
except Exception:  # pragma: no cover
    class Neo4jDate:  # fallback stub
        pass

ALLOWED_FIELDS = {
    "personId", "ownerId", "chartId", "name", "gender", "level",
    "dob", "dod", "description", "photoUrl",
    "lunarDeathDay", "lunarDeathMonth", "lunarDeathYear", "lunarIsLeap",
}

def _node_to_dict(node) -> dict:
    data = dict(node)
    out = {}
    for k in ALLOWED_FIELDS:
        v = data.get(k)
        if isinstance(v, Neo4jDate):
            # Convert neo4j.time.Date to native date
            try:
                v = v.to_native()
            except AttributeError:
                # Fallback manual construction
                v = date(v.year, v.month, v.day)
        # If stored as ISO string, Pydantic can parse it -> leave as is
        out[k] = v
    return out

async def create_person(chartId: str, ownerId: str, name: str, gender: str, level: int,
                        dob=None, dod=None, description=None, photoUrl=None):
    # Compute lunar death date fields
    lunar = solar_to_lunar(dod)
    lunar_day = lunar["lunarDeathDay"] if lunar else None
    lunar_month = lunar["lunarDeathMonth"] if lunar else None
    lunar_year = lunar["lunarDeathYear"] if lunar else None
    lunar_is_leap = lunar["lunarIsLeap"] if lunar else None

    async with neo4j.driver.session() as session:
        # Generate auto-increment personId per chart
        resId = await session.run(
            """
            MATCH (x:Person {chartId:$cid})
            WITH coalesce(max(x.personId), 0) AS mx
            MERGE (c:Counter {chartId:$cid, type:'PERSON'})
            ON CREATE SET c.value = mx
            WITH c
            SET c.value = c.value + 1
            RETURN c.value AS nextId
            """,
            cid=chartId,
        )
        personIdRec = await resId.single()
        if not personIdRec:
            raise HTTPException(status_code=500, detail="Failed to generate personId")
        personId: int = personIdRec["nextId"]

        # Create node with lunar fields
        await session.run("""
            CREATE (n:Person {
                personId:$pid, chartId:$cid, ownerId:$oid,
                name:$name, gender:$gender, level:$level,
                dob:$dob, dod:$dod, description:$desc, photoUrl:$photo,
                lunarDeathDay:$lunarDay, lunarDeathMonth:$lunarMonth,
                lunarDeathYear:$lunarYear, lunarIsLeap:$lunarIsLeap
            })
        """, pid=personId, cid=chartId, oid=ownerId, name=name, gender=gender, level=level,
           dob=dob if dob else None, dod=dod if dod else None,
           desc=description, photo=photoUrl,
           lunarDay=lunar_day, lunarMonth=lunar_month,
           lunarYear=lunar_year, lunarIsLeap=lunar_is_leap)

        # Return created
        res = await session.run("""
            MATCH (n:Person {personId:$pid, chartId:$cid})
            RETURN n
        """, pid=personId, cid=chartId)
        node = (await res.single())["n"]
        return _node_to_dict(node)

async def update_person(chartId: str, personId: int, patch: dict):
    if not patch:
        raise HTTPException(status_code=400, detail="Nothing to update")
    # Do not allow changing identity fields
    patch.pop("personId", None)
    patch.pop("chartId", None)

    # If dod is being updated, recompute lunar fields
    if "dod" in patch:
        dod_val = patch["dod"]
        lunar = solar_to_lunar(dod_val)
        if lunar:
            patch["lunarDeathDay"] = lunar["lunarDeathDay"]
            patch["lunarDeathMonth"] = lunar["lunarDeathMonth"]
            patch["lunarDeathYear"] = lunar["lunarDeathYear"]
            patch["lunarIsLeap"] = lunar["lunarIsLeap"]
        else:
            patch["lunarDeathDay"] = None
            patch["lunarDeathMonth"] = None
            patch["lunarDeathYear"] = None
            patch["lunarIsLeap"] = None

    setters = ", ".join([f"n.{k} = ${k}" for k in patch.keys()])
    async with neo4j.driver.session() as session:
        res = await session.run(f"""
            MATCH (n:Person {{personId:$pid, chartId:$cid}})
            SET {setters}
            RETURN n
        """, pid=personId, cid=chartId, **patch)
        rec = await res.single()
        if not rec:
            raise HTTPException(status_code=404, detail="Person not found")
        return _node_to_dict(rec["n"])

async def delete_person(chartId: str, personId: int):
    async with neo4j.driver.session() as session:
        res = await session.run("""
            MATCH (n:Person {personId:$pid, chartId:$cid})
            DETACH DELETE n
            RETURN count(*) as c
        """, pid=personId, cid=chartId)
        c = (await res.single())["c"]
        if c == 0:
            raise HTTPException(status_code=404, detail="Person not found")
        return True

async def get_person_detail(chartId: str, personId: int):
    """Get person details including all relationships (parents, spouses, children)."""
    async with neo4j.driver.session() as session:
        res = await session.run("""
            MATCH (n:Person {personId:$pid, chartId:$cid})

            // Parents (people who have FATHER_OF or MOTHER_OF edges pointing to this person)
            OPTIONAL MATCH (parent)-[rp:FATHER_OF|MOTHER_OF]->(n)
            WITH n, collect(
                CASE WHEN parent IS NOT NULL THEN {
                    personId: parent.personId,
                    name: parent.name,
                    gender: parent.gender,
                    relationship: type(rp)
                } END
            ) AS parents

            // Spouses (undirected SPOUSE_OF)
            OPTIONAL MATCH (n)-[rs:SPOUSE_OF]-(spouse:Person)
            WITH n, parents, collect(
                CASE WHEN spouse IS NOT NULL THEN {
                    personId: spouse.personId,
                    name: spouse.name,
                    gender: spouse.gender,
                    relationship: "SPOUSE_OF"
                } END
            ) AS spouses

            // Children (people this person has FATHER_OF or MOTHER_OF edges pointing to)
            OPTIONAL MATCH (n)-[rc:FATHER_OF|MOTHER_OF]->(child:Person)
            WITH n, parents, spouses, collect(
                CASE WHEN child IS NOT NULL THEN {
                    personId: child.personId,
                    name: child.name,
                    gender: child.gender,
                    relationship: type(rc)
                } END
            ) AS children

            RETURN n, parents, spouses, children
        """, pid=personId, cid=chartId)

        rec = await res.single()
        if not rec:
            raise HTTPException(status_code=404, detail="Person not found")

        person = _node_to_dict(rec["n"])
        person["parents"] = [p for p in (rec["parents"] or []) if p is not None]
        person["spouses"] = [s for s in (rec["spouses"] or []) if s is not None]
        person["children"] = [c for c in (rec["children"] or []) if c is not None]

        return person


async def list_persons(chartId: str, q: str = None, gender: str = None, level: int = None):
    """List persons in a chart with optional filters, including lunar death date fields."""
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
                name: n.name,
                gender: n.gender,
                level: n.level,
                dob: toString(n.dob),
                dod: toString(n.dod),
                description: n.description,
                photoUrl: n.photoUrl,
                lunarDeathDay: n.lunarDeathDay,
                lunarDeathMonth: n.lunarDeathMonth,
                lunarDeathYear: n.lunarDeathYear,
                lunarIsLeap: n.lunarIsLeap
            }} AS n
            ORDER BY n.level ASC, n.name ASC""",
            **params
        )
        records = await res.data()
        return [r["n"] for r in records]
