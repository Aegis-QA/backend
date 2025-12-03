import json
import os
import sys
import time
from kafka import KafkaConsumer
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

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/testcase_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def main():
    print("🚀 Starting Kafka worker...")
    print(f"📡 Connecting to Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"📬 Topic: {KAFKA_TOPIC}")
    print(f"👥 Consumer Group: {KAFKA_GROUP_ID}")
    
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
            
            try:
                # Check if job was cancelled before processing
                job = db.query(Job).filter(Job.id == job_id).first()
                if job and job.status == "CANCELLED":
                    print(f"🚫 Job {job_id} was cancelled. Skipping processing.")
                    continue
                
                # Process the job
                process_job(db, job_data)
                print(f"✅ Successfully processed job {job_id}")
            except Exception as e:
                print(f"❌ Error processing job {job_id}: {e}")
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Error handling message: {e}")

if __name__ == "__main__":
    main()
