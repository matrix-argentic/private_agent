"""RAG HTTP server — upload documents via browser or API."""

from fastapi import FastAPI
from app.server.lifespan import lifespan
from app.server.router import api_router, protected_router

app = FastAPI(title="RAG Document Server", lifespan=lifespan)
app.include_router(router=api_router)
app.include_router(router=protected_router)
