from app.db.neo4j import neo4j

# async def get_tree(chart_id: str):
#     async with neo4j.driver.session() as session:
#         res = await session.run(
#             """
#             MATCH (n:Person {chartId:$cid})
#             OPTIONAL MATCH (p:Person {chartId:$cid})-[:PARENT_OF]->(c:Person {chartId:$cid})
#             WITH collect(distinct {
#                 personId: n.personId,
#                 name: n.name,
#                 gender: n.gender,
#                 level: n.level,
#                 dob: toString(n.dob),
#                 dod: toString(n.dod),
#                 description: n.description
#             }) AS nodes, 
#             collect(distinct {source:p.personId, target:c.personId}) AS links
#             RETURN nodes, links
#             """,
#             cid=chart_id,
#         )

#         rec = await res.single()
#         nodes = rec["nodes"] or []
#         links = rec["links"] or []

#         return {"nodes": nodes, "links": links}


async def get_tree(chart_id: str):
    async with neo4j.driver.session() as session:
        res = await session.run(
            """
            MATCH (n:Person {chartId: $cid})
            RETURN 
                collect(n {
                    .personId,
                    .name, 
                    .gender, 
                    .level, 
                    .description,
                    .photoUrl,
                    dob: toString(n.dob),
                    dod: toString(n.dod)
                }) AS nodes,
                
                // Sử dụng Pattern Comprehension để lấy links ngay tại dòng của Node
                // Nó trả về mảng lồng nhau: [[link1], [], [link2, link3]...]
                collect([(n)-[:PARENT_OF]->(c:Person {chartId: $cid}) | {source: n.personId, target: c.personId}]) AS nested_links
            """,
            cid=chart_id,
        )

        rec = await res.single()
        
        nodes = rec["nodes"] or []
        # Làm phẳng mảng links (Flatten) ở phía Python vì Python xử lý việc này nhanh hơn DB
        nested_links = rec["nested_links"] or []
        links = [link for group in nested_links for link in group]

        return {"nodes": nodes, "links": links}


# import asyncio

# async def get_tree(chart_id: str):
#     async with neo4j.driver.session() as session:
#         # Query 1: Chỉ lấy Nodes
#         query_nodes = """
#             MATCH (n:Person {chartId: $cid})
#             RETURN n {
#                 .personId, .name, .gender, .level, .description,
#                 dob: toString(n.dob), dod: toString(n.dod)
#             } as node
#         """
        
#         # Query 2: Chỉ lấy Links
#         query_links = """
#             MATCH (p:Person {chartId: $cid})-[:PARENT_OF]->(c:Person {chartId: $cid})
#             RETURN {source: p.personId, target: c.personId} as link
#         """

#         # Chạy song song bằng asyncio.gather
#         task_nodes = session.run(query_nodes, cid=chart_id)
#         task_links = session.run(query_links, cid=chart_id)
        
#         res_nodes, res_links = await asyncio.gather(task_nodes, task_links)

#         # Lấy dữ liệu
#         nodes = [record["node"] async for record in res_nodes]
#         links = [record["link"] async for record in res_links]

#         return {"nodes": nodes, "links": links}
    