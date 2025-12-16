from fastapi import HTTPException
from app.db.neo4j import neo4j

async def add_parent_of(chart_id: str, parent_id: int, child_id: int):
    async with neo4j.driver.session() as session:

        # 1. Kiểm tra tồn tại và lấy level
        check = await session.run("""
            MATCH (parent:Person {personId: $parentId, chartId: $cid})
            MATCH (child:Person {personId: $childId, chartId: $cid})
            RETURN parent.level as parentLevel, child.level as childLevel
        """, parentId=parent_id, childId=child_id, cid=chart_id)
        
        result = await check.single()
        if not result:
            raise HTTPException(status_code=404, detail="Parent or child not found")
        
        # 2. Validation: parent level phải NHỎ HƠN child level
        parent_level = result["parentLevel"]
        child_level = result["childLevel"]
        
        if parent_level >= child_level:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid relationship: parent (level {parent_level}) must have lower level than child (level {child_level})"
            )

        # prevent cycles: ensure no path child -> ... -> parent already exists
        cyc = await session.run("""
            MATCH (parent:Person {personId:$parentId, chartId:$cid}),
                  (child:Person {personId:$childId, chartId:$cid})
            OPTIONAL MATCH path = (child)-[:PARENT_OF*]->(parent)
            RETURN path IS NOT NULL AS cycle
        """, parentId=parent_id, childId=child_id, cid=chart_id)
        if (await cyc.single())["cycle"]:
            raise HTTPException(status_code=400, detail="Cycle detected")

        await session.run("""
            MATCH (p:Person {personId:$parentId, chartId:$cid}),
                  (c:Person {personId:$childId, chartId:$cid})
            MERGE (p)-[:PARENT_OF]->(c)
        """, parentId=parent_id, childId=child_id, cid=chart_id)

        # optional: update child's level = min(parents)+1
        # await session.run("""
        #     MATCH (c:Person {personId:$childId, chartId:$cid})
        #     OPTIONAL MATCH (p:Person {chartId:$cid})-[:PARENT_OF]->(c)
        #     WITH c, min(p.level) AS minlvl
        #     SET c.level = coalesce(minlvl, 0) + 1
        # """, childId=child_id, cid=chart_id)
    return True

async def remove_parent_of(chart_id: str, parent_id: int, child_id: int):
    async with neo4j.driver.session() as session:
        await session.run("""
            MATCH (p:Person {personId:$parentId, chartId:$cid})-[r:PARENT_OF]->(c:Person {personId:$childId, chartId:$cid})
            DELETE r
        """, parentId=parent_id, childId=child_id, cid=chart_id)
    return True
