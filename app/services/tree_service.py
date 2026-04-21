from app.db.neo4j import neo4j


async def get_tree(chart_id: str):
    """
    Fetch all nodes and relationships for a given chartId.
    Returns { nodes: [...], links: [...] } where:
      - nodes have id, name, gender, level, photoUrl
      - links contain:
          * PARENT_OF (1 per child, source = father if exists, else mother)
          * SPOUSE_OF (kept as-is)
    """
    async with neo4j.driver.session() as session:
        res = await session.run(
            """
            // Step 1: Collect all nodes for this chart (minimal fields for tree rendering)
            MATCH (n:Person {chartId: $cid})
            WITH collect(n {
                id: n.personId,
                .name,
                .gender,
                .level,
                .photoUrl
            }) AS nodes

            // Step 2: Collect FATHER_OF relationships
            OPTIONAL MATCH (f:Person {chartId: $cid})-[r1:FATHER_OF]->(c:Person {chartId: $cid})
            WITH nodes,
                 collect(
                    CASE WHEN r1 IS NOT NULL THEN {
                        source: f.personId,
                        target: c.personId,
                        type: "FATHER_OF"
                    } END
                 ) AS father_links

            // Step 3: Collect MOTHER_OF relationships
            OPTIONAL MATCH (m:Person {chartId: $cid})-[r3:MOTHER_OF]->(c2:Person {chartId: $cid})
            WITH nodes, father_links,
                 collect(
                    CASE WHEN r3 IS NOT NULL THEN {
                        source: m.personId,
                        target: c2.personId,
                        type: "MOTHER_OF"
                    } END
                 ) AS mother_links

            // Step 4: Collect SPOUSE_OF relationships (directed match)
            OPTIONAL MATCH (s1:Person {chartId: $cid})-[r2:SPOUSE_OF]->(s2:Person {chartId: $cid})
            WITH nodes, father_links, mother_links,
                 collect(
                    CASE WHEN r2 IS NOT NULL THEN {
                        source: s1.personId,
                        target: s2.personId,
                        type: "SPOUSE_OF"
                    } END
                 ) AS spouse_links

            RETURN nodes, father_links, mother_links, spouse_links
            """,
            cid=chart_id,
        )

        rec = await res.single()

        nodes = rec["nodes"] or []
        # Filter out nulls that arise from CASE WHEN ... END on OPTIONAL MATCH with no results
        father_links = [link for link in (rec["father_links"] or []) if link is not None]
        mother_links = [link for link in (rec["mother_links"] or []) if link is not None]
        spouse_links = [link for link in (rec["spouse_links"] or []) if link is not None]

        # Build lookup dicts: child_id -> link
        father_by_child: dict[int, dict] = {}
        for link in father_links:
            father_by_child[link["target"]] = link

        mother_by_child: dict[int, dict] = {}
        for link in mother_links:
            mother_by_child[link["target"]] = link

        # All unique child ids
        all_children = set(father_by_child.keys()) | set(mother_by_child.keys())

        final_links: list[dict] = []

        # 1. Keep all SPOUSE_OF links as-is
        for link in spouse_links:
            final_links.append(link)

        # 2. Create exactly 1 PARENT_OF link per child
        #    Rule: prefer father as source; fallback to mother (single mother)
        for child_id in all_children:
            father_link = father_by_child.get(child_id)
            mother_link = mother_by_child.get(child_id)

            if father_link:
                final_links.append({
                    "source": father_link["source"],
                    "target": child_id,
                    "type": "PARENT_OF",
                })
            elif mother_link:
                # Single mother case
                final_links.append({
                    "source": mother_link["source"],
                    "target": child_id,
                    "type": "PARENT_OF",
                })

        return {"nodes": nodes, "links": final_links}