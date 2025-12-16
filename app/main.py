from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.db.mongo import connect_to_mongo, close_mongo
from app.db.neo4j import connect_to_neo4j, close_neo4j
from app.routers import auth, charts, persons, relationships, tree

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    await connect_to_neo4j()
    yield
    await close_neo4j()
    await close_mongo()

# Expose the Swagger UI at the root URL so visiting http://127.0.0.1:8000 opens the docs
app = FastAPI(title=settings.APP_NAME, lifespan=lifespan, docs_url="/")

# CORS
app.add_middleware(
    CORSMiddleware,
    # allow_origins=settings.CORS_ORIGINS,
    allow_origins=["*"],# For development only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(charts.router)
app.include_router(persons.router)
app.include_router(relationships.router)
app.include_router(tree.router)

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/version")
async def version():
    return {"name": settings.APP_NAME, "env": settings.APP_ENV}

if __name__ == "__main__":
    import uvicorn
    from app.core.config import settings
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST, 
        port=settings.APP_PORT,
        reload=True,
    )