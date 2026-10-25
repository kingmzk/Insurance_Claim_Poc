from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .core.config import API_HOST, API_PORT
from .db.database import init_db
from .api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite tables and FTS5 index on startup
    init_db()
    yield

app = FastAPI(
    title="Autonomous Multi-Agent Insurance Claims Processing",
    description="Multi-Agent Motor Claims Adjudication PoC using LangGraph, SQLite FTS5 RAG, and Human-in-the-Loop review gates.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
def root():
    return {
        "status": "online",
        "system": "Autonomous Multi-Agent Insurance Claims Processing PoC",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=API_HOST, port=API_PORT, reload=True)
