from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="AI Test Case Generator API", version="1.0.0")

# Prometheus instrumentation
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

# Custom metrics
jobs_total = Counter('jobs_total', 'Total number of jobs processed', ['status'])
jobs_processing = Gauge('jobs_processing', 'Number of jobs currently being processed')
test_cases_generated = Counter('test_cases_generated_total', 'Total number of test cases generated')
llm_calls_total = Counter('llm_calls_total', 'Total number of LLM API calls', ['status'])

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

from app.routers import upload, jobs
from app.database import engine, Base
from app.kafka_producer import job_queue
import threading
import time

Base.metadata.create_all(bind=engine)

app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])

# Background worker
def process_jobs():
    from worker.processor import process_job
# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
