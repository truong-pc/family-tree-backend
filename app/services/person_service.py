from fastapi import HTTPException
from app.db.neo4j import neo4j
from datetime import date
try:  # neo4j driver date type
    from neo4j.time import Date as Neo4jDate  # type: ignore
except Exception:  # pragma: no cover
    class Neo4jDate:  # fallback stub
        pass

ALLOWED_FIELDS = {"personId", "ownerId", "chartId", "name", "gender", "level", "dob", "dod", "description", "photoUrl"}

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

        # Create node (birthOrder removed)
        await session.run("""
            CREATE (n:Person {
                personId:$pid, chartId:$cid, ownerId:$oid,
                name:$name, gender:$gender, level:$level,
                dob:$dob, dod:$dod, description:$desc, photoUrl:$photo
            })
        """, pid=personId, cid=chartId, oid=ownerId, name=name, gender=gender, level=level,
           dob=str(dob) if dob else None, dod=str(dod) if dod else None,
           desc=description, photo=photoUrl)

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
