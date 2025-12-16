from neo4j import AsyncGraphDatabase, AsyncDriver
from app.core.config import settings

class Neo4j:
    driver: AsyncDriver | None = None

neo4j = Neo4j()

async def connect_to_neo4j():
    neo4j.driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )
    async with neo4j.driver.session() as session:
        # Constraints: ensure composite uniqueness on (chartId, personId)
        await session.run(
            "CREATE CONSTRAINT person_chart_unique IF NOT EXISTS FOR (p:Person) REQUIRE (p.chartId, p.personId) IS UNIQUE"
        )
    return neo4j.driver

async def close_neo4j():
    if neo4j.driver:
        await neo4j.driver.close()
