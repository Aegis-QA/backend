from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Job, TestCase
from app.schemas import JobResponse, TestCaseResponse
import json

router = APIRouter()

@router.get("/jobs", response_model=List[JobResponse])
def list_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.id.desc()).offset(skip).limit(limit).all()
    return jobs

@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job_status(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: int, db: Session = Depends(get_db)):
    """Cancel a job that is PENDING or PROCESSING"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Only allow cancelling jobs that are PENDING or PROCESSING
    if job.status not in ["PENDING", "PROCESSING"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot cancel job with status {job.status}. Only PENDING or PROCESSING jobs can be cancelled."
        )
    
    # Update status to CANCELLED
    job.status = "CANCELLED"
    db.commit()
    db.refresh(job)
    
    return {"message": f"Job {job_id} has been cancelled", "status": "CANCELLED"}

@router.get("/jobs/{job_id}/testcases")
def get_test_cases(job_id: int, db: Session = Depends(get_db)):
    test_cases = db.query(TestCase).filter(TestCase.job_id == job_id).all()
    
    # Convert to dict and parse JSON steps
    result = []
    for tc in test_cases:
        tc_dict = {
            "test_id": tc.test_id,
            "description": tc.description,
            "preconditions": tc.preconditions,
            "steps": json.loads(tc.steps) if isinstance(tc.steps, str) else tc.steps,
            "expected_output": tc.expected_output
        }
        result.append(tc_dict)
    
    return result
