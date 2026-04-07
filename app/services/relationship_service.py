from fastapi import HTTPException
from app.db.neo4j import neo4j

async def add_parent_of(chart_id: str, parent_id: int, child_id: int, child_order: int = None):
    async with neo4j.driver.session() as session:

        # 1. Check existence and get level
        check = await session.run("""
            MATCH (parent:Person {personId: $parentId, chartId: $cid})
            MATCH (child:Person {personId: $childId, chartId: $cid})
            RETURN parent.level as parentLevel, child.level as childLevel
        """, parentId=parent_id, childId=child_id, cid=chart_id)
        
        result = await check.single()
        if not result:
            raise HTTPException(status_code=404, detail="Parent or child not found")
        
        # 2. Validation: parent level must be lower than child level
        parent_level = result["parentLevel"]
        child_level = result["childLevel"]
        
        if parent_level >= child_level:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid relationship: parent (level {parent_level}) must have lower level than child (level {child_level})"
            )

        # 3. Prevent cycles: ensure no path child -> ... -> parent already exists
        cyc = await session.run("""
            MATCH (parent:Person {personId:$parentId, chartId:$cid}),
                  (child:Person {personId:$childId, chartId:$cid})
            OPTIONAL MATCH path = (child)-[:PARENT_OF*]->(parent)
            RETURN path IS NOT NULL AS cycle
        """, parentId=parent_id, childId=child_id, cid=chart_id)
        if (await cyc.single())["cycle"]:
            raise HTTPException(status_code=400, detail="Cycle detected")

        # 4. Create relationship with properties
        await session.run("""
            MATCH (p:Person {personId:$parentId, chartId:$cid}),
                  (c:Person {personId:$childId, chartId:$cid})
            MERGE (p)-[r:PARENT_OF]->(c)
            SET r.childOrder = $childOrder
        """, parentId=parent_id, childId=child_id, cid=chart_id, childOrder=child_order)

    return True

async def remove_parent_of(chart_id: str, parent_id: int, child_id: int):
    async with neo4j.driver.session() as session:
        await session.run("""
            MATCH (p:Person {personId:$parentId, chartId:$cid})-[r:PARENT_OF]->(c:Person {personId:$childId, chartId:$cid})
            DELETE r
        """, parentId=parent_id, childId=child_id, cid=chart_id)
    return True

async def add_spouse_of(chart_id: str, person1_id: int, person2_id: int, order: int = None):
    async with neo4j.driver.session() as session:
        # 1. Check existence, gender, and existing incoming SPOUSE_OF of each person
        check = await session.run("""
            MATCH (p1:Person {personId: $p1Id, chartId: $cid})
            MATCH (p2:Person {personId: $p2Id, chartId: $cid})
            // Count INCOMING edges (someone already married this person as target/female)
            OPTIONAL MATCH ()-[:SPOUSE_OF]->(p1)
            WITH p1, p2, count(*) AS p1InCount
            OPTIONAL MATCH ()-[:SPOUSE_OF]->(p2)
            RETURN p1.personId AS id1, p2.personId AS id2,
                   p1.gender AS g1, p2.gender AS g2,
                   p1InCount AS p1InCount,
                   count(*) AS p2InCount
        """, p1Id=person1_id, p2Id=person2_id, cid=chart_id)

        result = await check.single()
        if not result:
            raise HTTPException(status_code=404, detail="One or both persons not found")

        # 2. Gender validation: must be different genders
        g1, g2 = result["g1"], result["g2"]
        if g1 == g2 and g1 in ["M", "F"]:
            raise HTTPException(status_code=400, detail="Spouses must be of different genders")

        # 3. The female person must not already be the target of a SPOUSE_OF edge
        female_already_has_husband = (
            (g1 == "F" and result["p1InCount"] > 0) or
            (g2 == "F" and result["p2InCount"] > 0)
        )
        if female_already_has_husband:
            raise HTTPException(
                status_code=400,
                detail="The female person already has a spouse."
            )

        # 4. Always MERGE as (male)-[:SPOUSE_OF]->(female), regardless of input order
        male_id = person1_id if g1 == "M" else person2_id
        female_id = person2_id if g1 == "M" else person1_id

        await session.run("""
            MATCH (male:Person {personId:$maleId, chartId:$cid}),
                  (female:Person {personId:$femaleId, chartId:$cid})
            MERGE (male)-[r:SPOUSE_OF]->(female)
            SET r.order = $order
        """, maleId=male_id, femaleId=female_id, cid=chart_id, order=order)
    return True

async def remove_spouse_of(chart_id: str, person1_id: int, person2_id: int):
    async with neo4j.driver.session() as session:
        await session.run("""
            MATCH (p1:Person {personId:$p1Id, chartId:$cid})-[r:SPOUSE_OF]->(p2:Person {personId:$p2Id, chartId:$cid})
            DELETE r
        """, p1Id=person1_id, p2Id=person2_id, cid=chart_id)
    return True
