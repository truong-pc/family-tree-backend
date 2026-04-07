from app.db.neo4j import neo4j


async def get_tree(chart_id: str):
    """
    Fetch all nodes and relationships for a given chartId.
    Returns { nodes: [...], links: [...] } where:
      - nodes have `id` (mapped from personId), name, gender, level, dob, dod, description, photoUrl
      - links have source, target, type ("PARENT_OF" or "SPOUSE_OF"), and relationship-specific properties
    """
    async with neo4j.driver.session() as session:
        res = await session.run(
            """
            // Step 1: Collect all nodes for this chart
            MATCH (n:Person {chartId: $cid})
            WITH collect(n {
                id: n.personId,
                .name,
                .gender,
                .level,
                .description,
                .photoUrl,
                dob: toString(n.dob),
                dod: toString(n.dod)
            }) AS nodes

            // Step 2: Collect PARENT_OF relationships
            OPTIONAL MATCH (p:Person {chartId: $cid})-[r1:PARENT_OF]->(c:Person {chartId: $cid})
            WITH nodes,
                 collect(
                    CASE WHEN r1 IS NOT NULL THEN {
                        source: p.personId,
                        target: c.personId,
                        type: "PARENT_OF",
                        childOrder: r1.childOrder
                    } END
                 ) AS parent_links

            // Step 3: Collect SPOUSE_OF relationships (directed match)
            OPTIONAL MATCH (s1:Person {chartId: $cid})-[r2:SPOUSE_OF]->(s2:Person {chartId: $cid})
            WITH nodes, parent_links,
                 collect(
                    CASE WHEN r2 IS NOT NULL THEN {
                        source: s1.personId,
                        target: s2.personId,
                        type: "SPOUSE_OF",
                        order: r2.order
                    } END
                 ) AS spouse_links

            RETURN nodes, parent_links, spouse_links
            """,
            cid=chart_id,
        )

        rec = await res.single()

        nodes = rec["nodes"] or []
        # Filter out nulls that arise from CASE WHEN ... END on OPTIONAL MATCH with no results
        parent_links = [link for link in (rec["parent_links"] or []) if link is not None]
        spouse_links = [link for link in (rec["spouse_links"] or []) if link is not None]

        links = parent_links + spouse_links

        return {"nodes": nodes, "links": links}