from app.db.neo4j import neo4j

def convert_neo4j_date(value):
    """Convert Neo4j Date object to Python date, or return as-is if already native"""
    if value is None:
        return None
    if hasattr(value, 'to_native'):
        return value.to_native()
    return value

async def get_tree(chart_id: str):
    async with neo4j.driver.session() as session:
        res = await session.run(
            """
            MATCH (n:Person {chartId:$cid})
            OPTIONAL MATCH (p:Person {chartId:$cid})-[:PARENT_OF]->(c:Person {chartId:$cid})
            WITH collect(distinct {
                personId: n.personId,
                name: n.name,
                gender: n.gender,
                level: n.level,
                dob: toString(n.dob),
                dod: toString(n.dod),
                description: n.description
            }) AS nodes, 
            collect(distinct {source:p.personId, target:c.personId}) AS links
            RETURN nodes, links
            """,
            cid=chart_id,
        )

        rec = await res.single()
        nodes = rec["nodes"] or []
        links = rec["links"] or []

        return {"nodes": nodes, "links": links}
