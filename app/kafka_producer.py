import threading
import queue
import os

# In-memory job queue (replacing Kafka for simplicity)
job_queue = queue.Queue()

def send_job_to_kafka(job_id: int, file_path: str):
    """Add job to queue for processing"""
    message = {"job_id": job_id, "file_path": file_path}
    job_queue.put(message)
    print(f"Job {job_id} added to queue")
