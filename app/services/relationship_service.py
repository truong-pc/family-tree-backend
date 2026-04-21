from fastapi import HTTPException
from app.db.neo4j import neo4j

async def add_father_of(chart_id: str, father_id: int, child_id: int, child_order: int = None):
    """Create a FATHER_OF relationship. Validates father is male, level order, no cycles, and no existing father."""
    async with neo4j.driver.session() as session:

        # 1. Check existence, gender and level
        check = await session.run("""
            MATCH (father:Person {personId: $fatherId, chartId: $cid})
            MATCH (child:Person {personId: $childId, chartId: $cid})
            OPTIONAL MATCH ()-[existing:FATHER_OF]->(child)
            RETURN father.level as fatherLevel, child.level as childLevel,
                   father.gender as fatherGender,
                   existing IS NOT NULL AS alreadyHasFather
        """, fatherId=father_id, childId=child_id, cid=chart_id)

        result = await check.single()
        if not result:
            raise HTTPException(status_code=404, detail="Father or child not found")

        # 2. Gender validation
        if result["fatherGender"] != "M":
            raise HTTPException(status_code=400, detail="Father must be male (gender='M')")

        # 3. Level validation
        if result["fatherLevel"] >= result["childLevel"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid relationship: father (level {result['fatherLevel']}) must have lower level than child (level {result['childLevel']})"
            )

        # 4. Check child doesn't already have a father
        if result["alreadyHasFather"]:
            raise HTTPException(status_code=400, detail="Child already has a father")

        # 5. Prevent cycles
        cyc = await session.run("""
            MATCH (father:Person {personId:$fatherId, chartId:$cid}),
                  (child:Person {personId:$childId, chartId:$cid})
            OPTIONAL MATCH path = (child)-[:FATHER_OF|MOTHER_OF*]->(father)
            RETURN path IS NOT NULL AS cycle
        """, fatherId=father_id, childId=child_id, cid=chart_id)
        if (await cyc.single())["cycle"]:
            raise HTTPException(status_code=400, detail="Cycle detected")

        # 6. Create relationship
        await session.run("""
            MATCH (f:Person {personId:$fatherId, chartId:$cid}),
                  (c:Person {personId:$childId, chartId:$cid})
            MERGE (f)-[r:FATHER_OF]->(c)
            SET r.childOrder = $childOrder
        """, fatherId=father_id, childId=child_id, cid=chart_id, childOrder=child_order)

    return True

async def remove_father_of(chart_id: str, father_id: int, child_id: int):
    async with neo4j.driver.session() as session:
        await session.run("""
            MATCH (f:Person {personId:$fatherId, chartId:$cid})-[r:FATHER_OF]->(c:Person {personId:$childId, chartId:$cid})
            DELETE r
        """, fatherId=father_id, childId=child_id, cid=chart_id)
    return True

async def add_mother_of(chart_id: str, mother_id: int, child_id: int, child_order: int = None):
    """Create a MOTHER_OF relationship. Validates mother is female, level order, no cycles, and no existing mother."""
    async with neo4j.driver.session() as session:

        # 1. Check existence, gender and level
        check = await session.run("""
            MATCH (mother:Person {personId: $motherId, chartId: $cid})
            MATCH (child:Person {personId: $childId, chartId: $cid})
            OPTIONAL MATCH ()-[existing:MOTHER_OF]->(child)
            RETURN mother.level as motherLevel, child.level as childLevel,
                   mother.gender as motherGender,
                   existing IS NOT NULL AS alreadyHasMother
        """, motherId=mother_id, childId=child_id, cid=chart_id)

        result = await check.single()
        if not result:
            raise HTTPException(status_code=404, detail="Mother or child not found")

        # 2. Gender validation
        if result["motherGender"] != "F":
            raise HTTPException(status_code=400, detail="Mother must be female (gender='F')")

        # 3. Level validation
        if result["motherLevel"] >= result["childLevel"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid relationship: mother (level {result['motherLevel']}) must have lower level than child (level {result['childLevel']})"
            )

        # 4. Check child doesn't already have a mother
        if result["alreadyHasMother"]:
            raise HTTPException(status_code=400, detail="Child already has a mother")

        # 5. Prevent cycles
        cyc = await session.run("""
            MATCH (mother:Person {personId:$motherId, chartId:$cid}),
                  (child:Person {personId:$childId, chartId:$cid})
            OPTIONAL MATCH path = (child)-[:FATHER_OF|MOTHER_OF*]->(mother)
            RETURN path IS NOT NULL AS cycle
        """, motherId=mother_id, childId=child_id, cid=chart_id)
        if (await cyc.single())["cycle"]:
            raise HTTPException(status_code=400, detail="Cycle detected")

        # 6. Create relationship
        await session.run("""
            MATCH (m:Person {personId:$motherId, chartId:$cid}),
                  (c:Person {personId:$childId, chartId:$cid})
            MERGE (m)-[r:MOTHER_OF]->(c)
            SET r.childOrder = $childOrder
        """, motherId=mother_id, childId=child_id, cid=chart_id, childOrder=child_order)

    return True

async def remove_mother_of(chart_id: str, mother_id: int, child_id: int):
    async with neo4j.driver.session() as session:
        await session.run("""
            MATCH (m:Person {personId:$motherId, chartId:$cid})-[r:MOTHER_OF]->(c:Person {personId:$childId, chartId:$cid})
            DELETE r
        """, motherId=mother_id, childId=child_id, cid=chart_id)
    return True

async def add_spouse_of(chart_id: str, person1_id: int, person2_id: int, spouse_order: int = None):
    async with neo4j.driver.session() as session:
        # 1. Check existence, gender, and existing incoming SPOUSE_OF of each person
        check = await session.run("""
            MATCH (p1:Person {personId: $p1Id, chartId: $cid})
            MATCH (p2:Person {personId: $p2Id, chartId: $cid})
            // Count INCOMING edges (someone already married this person as target/female)
            OPTIONAL MATCH ()-[r1:SPOUSE_OF]->(p1)
            WITH p1, p2, count(r1) AS p1InCount
            OPTIONAL MATCH ()-[r2:SPOUSE_OF]->(p2)
            RETURN p1.personId AS id1, p2.personId AS id2,
                   p1.gender AS g1, p2.gender AS g2,
                   p1InCount AS p1InCount,
                   count(r2) AS p2InCount
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
            SET r.spouseOrder = $spouseOrder
        """, maleId=male_id, femaleId=female_id, cid=chart_id, spouseOrder=spouse_order)
    return True

async def remove_spouse_of(chart_id: str, person1_id: int, person2_id: int):
    async with neo4j.driver.session() as session:
        await session.run("""
            MATCH (p1:Person {personId:$p1Id, chartId:$cid})-[r:SPOUSE_OF]->(p2:Person {personId:$p2Id, chartId:$cid})
            DELETE r
        """, p1Id=person1_id, p2Id=person2_id, cid=chart_id)
    return True

async def check_spouse_couple(chart_id: str, father_id: int, mother_id: int) -> bool:
    """Check if two persons are connected by a SPOUSE_OF relationship."""
    async with neo4j.driver.session() as session:
        res = await session.run("""
            MATCH (a:Person {personId:$fId, chartId:$cid})-[:SPOUSE_OF]-(b:Person {personId:$mId, chartId:$cid})
            RETURN count(*) > 0 AS isCouple
        """, fId=father_id, mId=mother_id, cid=chart_id)
        record = await res.single()
        return record["isCouple"] if record else False
