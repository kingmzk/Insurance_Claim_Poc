try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from .core.config import API_HOST, API_PORT, CORS_ORIGINS
from .core.telemetry import telemetry_manager, CONTENT_TYPE_LATEST
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

# OpenTelemetry correlation header middleware
@app.middleware("http")
async def add_telemetry_headers(request: Request, call_next):
    response = await call_next(request)
    trace_id = telemetry_manager.get_current_trace_id()
    span_id = telemetry_manager.get_current_span_id()
    if trace_id:
        response.headers["X-Trace-Id"] = trace_id
    if span_id:
        response.headers["X-Span-Id"] = span_id
    return response

# Enable CORS for frontend UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenTelemetry FastAPI Auto-Instrumentation
FastAPIInstrumentor.instrument_app(
    app,
    tracer_provider=telemetry_manager.tracer_provider,
    excluded_urls="docs,openapi.json,metrics"
)

app.include_router(router)

@app.get("/metrics", tags=["Observability"])
def prometheus_metrics():
    """Official Prometheus metrics scraping endpoint in standard exposition text format."""
    return Response(content=telemetry_manager.get_prometheus_metrics(), media_type=CONTENT_TYPE_LATEST)

@app.get("/")
def root():
    return {
        "status": "online",
        "system": "Autonomous Multi-Agent Insurance Claims Processing PoC",
        "version": "1.0.0",
        "telemetry": {
            "opentelemetry": "active",
            "prometheus_metrics": "/metrics",
            "langfuse": "active",
            "service_name": telemetry_manager.service_name,
        },
        "docs_url": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=API_HOST, port=API_PORT, reload=True)

