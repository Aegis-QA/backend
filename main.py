from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Gauge
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import func
from app.database import engine, Base, SessionLocal
from app.models import Job, TestCase
from app.routers import upload, jobs, n8n_storage
import threading
import time
from fastapi import Request

app = FastAPI(title="AI Test Case Generator API", version="1.0.0")

# Prometheus instrumentation
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

# Custom metrics
jobs_total = Counter('jobs_total', 'Total number of jobs processed', ['status'])
jobs_processing = Gauge('jobs_processing', 'Number of jobs currently being processed')
test_cases_generated = Counter('test_cases_generated_total', 'Total number of test cases generated')
llm_calls_total = Counter('llm_calls_total', 'Total number of LLM API calls', ['status'])

# DB-derived metrics for both Python and n8n flows.
jobs_db_total = Gauge('jobs_db_total', 'Total jobs currently in database')
jobs_db_by_status = Gauge('jobs_db_by_status', 'Current jobs in database by status', ['status'])
test_cases_db_total = Gauge('test_cases_db_total', 'Total test cases currently in database')

# Make metrics available to other modules
app.state.metrics = {
    'jobs_total': jobs_total,
    'jobs_processing': jobs_processing,
    'test_cases_generated': test_cases_generated,
    'llm_calls_total': llm_calls_total,
}

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
app.include_router(n8n_storage.router, prefix="/api/v1", tags=["n8n-storage"])

_METRIC_REFRESH_INTERVAL_SECONDS = 1
_last_metric_refresh = 0.0
_metric_refresh_lock = threading.Lock()


def refresh_db_metrics_once() -> None:
    tracked_statuses = ["PENDING", "PROCESSING", "COMPLETED", "FAILED", "CANCELLED"]
    db = SessionLocal()
    try:
        jobs_total_count = db.query(func.count(Job.id)).scalar() or 0
        test_cases_total_count = db.query(func.count(TestCase.id)).scalar() or 0

        jobs_db_total.set(float(jobs_total_count))
        test_cases_db_total.set(float(test_cases_total_count))

        status_rows = db.query(Job.status, func.count(Job.id)).group_by(Job.status).all()
        status_counts = {status: count for status, count in status_rows}

        for status in tracked_statuses:
            jobs_db_by_status.labels(status=status).set(float(status_counts.get(status, 0)))
    finally:
        db.close()


@app.middleware("http")
async def maybe_refresh_metrics(request: Request, call_next):
    global _last_metric_refresh
    now = time.time()
    if now - _last_metric_refresh >= _METRIC_REFRESH_INTERVAL_SECONDS:
        with _metric_refresh_lock:
            if now - _last_metric_refresh >= _METRIC_REFRESH_INTERVAL_SECONDS:
                try:
                    refresh_db_metrics_once()
                    _last_metric_refresh = now
                except Exception:
                    pass
    return await call_next(request)


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
