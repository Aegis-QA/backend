import json
import os
import sys
import time
from kafka import KafkaConsumer
from prometheus_client import Counter, Gauge, start_http_server
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db
from app.models import Job
from worker.processor import process_job

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
KAFKA_TOPIC = "job-processing"
KAFKA_GROUP_ID = "test-case-workers"
WORKER_METRICS_PORT = int(os.getenv("WORKER_METRICS_PORT", "8010"))

# Worker metrics are exposed from this process and scraped by Prometheus.
jobs_total = Counter('jobs_total', 'Total number of jobs processed', ['status'])
jobs_processing = Gauge('jobs_processing', 'Number of jobs currently being processed')
test_cases_generated = Counter('test_cases_generated_total', 'Total number of test cases generated')
llm_calls_total = Counter('llm_calls_total', 'Total number of LLM API calls', ['status'])

metrics = {
    'jobs_total': jobs_total,
    'jobs_processing': jobs_processing,
    'test_cases_generated': test_cases_generated,
    'llm_calls_total': llm_calls_total,
}

# Database configuration
_raw_db_url = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/testcase_db")
DATABASE_URL = _raw_db_url.replace("postgresql://", "postgresql+psycopg://", 1) if _raw_db_url.startswith("postgresql://") else _raw_db_url
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def main():
    print("🚀 Starting Kafka worker...")
    print(f"📡 Connecting to Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"📬 Topic: {KAFKA_TOPIC}")
    print(f"👥 Consumer Group: {KAFKA_GROUP_ID}")
    print(f"📈 Worker metrics: http://0.0.0.0:{WORKER_METRICS_PORT}/metrics")

    start_http_server(WORKER_METRICS_PORT)
    
    # Create Kafka consumer
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_GROUP_ID,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='earliest',
        enable_auto_commit=True
    )
    
    print("✅ Worker ready. Waiting for jobs...")
    
    # Process messages
    for message in consumer:
        try:
            job_data = message.value
            job_id = job_data.get('job_id')
            
            print(f"\n📨 Received job: {job_id}")
            
            # Get database session
            db = SessionLocal()
            processing_incremented = False
            
            try:
                # Check if job was cancelled before processing
                job = db.query(Job).filter(Job.id == job_id).first()
                if job and job.status == "CANCELLED":
                    print(f"🚫 Job {job_id} was cancelled. Skipping processing.")
                    continue
                
                # Process the job
                jobs_processing.inc()
                processing_incremented = True
                process_job(db, job_data, metrics)
                jobs_total.labels(status='success').inc()
                print(f"✅ Successfully processed job {job_id}")
            except Exception as e:
                jobs_total.labels(status='failed').inc()
                print(f"❌ Error processing job {job_id}: {e}")
            finally:
                if processing_incremented:
                    jobs_processing.dec()
                db.close()
                
        except Exception as e:
            print(f"❌ Error handling message: {e}")

if __name__ == "__main__":
    main()
