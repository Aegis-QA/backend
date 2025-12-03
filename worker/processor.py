from sqlalchemy.orm import Session
from app.models import Job, TestCase
import worker.llm  # Import module first
import importlib
importlib.reload(worker.llm)  # Force reload to get latest changes
from worker.llm import generate_test_cases
from worker.storage import download_file_from_minio
import os
import json

def process_job(db: Session, job_data: dict, metrics: dict = None):
    job_id = job_data["job_id"]
    file_path = job_data.get("file_path", "")
    
    try:
        # Update job status to processing
        job = db.query(Job).filter(Job.id == job_id).first()
        job.status = "PROCESSING"
        db.commit()
        
        text_content = ""
        
        # Download and extract text from document if provided
        if file_path:
            # Generate local path for downloaded file
            filename = os.path.basename(file_path)
            local_path = f"/tmp/{filename}"
            download_file_from_minio(file_path, local_path)
            
            # Extract text based on file type
            if local_path.endswith('.txt'):
                with open(local_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
            elif local_path.endswith('.pdf'):
                # TODO: Implement PDF parsing with PyPDF2
                text_content = "PDF parsing not yet implemented"
            elif local_path.endswith('.docx'):
                # TODO: Implement DOCX parsing with python-docx
                text_content = "DOCX parsing not yet implemented"
        
        # If no document, create context from images
        if not text_content and job.image_paths:
            text_content = f"Generate UI test cases for {len(job.image_paths)} user interface screenshot(s). " \
                          f"Focus on visual elements, user interactions, layout validation, and responsive design testing."
        
        # If still no content, use generic
        if not text_content:
            text_content = "Generate generic test cases for the system"
        
        # Generate test cases using LLM - force reload module to get latest code
        import worker.llm
        import importlib
        importlib.reload(worker.llm)
        test_cases = worker.llm.generate_test_cases(text_content, job.image_paths or [], metrics)
        
        # Save test cases to database
        for tc_data in test_cases:
            test_case = TestCase(
                job_id=job_id,
                test_id=tc_data["test_id"],
                description=tc_data["description"],
                preconditions=tc_data["preconditions"],
                steps=json.dumps(tc_data["steps"]),
                expected_output=tc_data["expected_output"]
            )
            db.add(test_case)
            
            # Record metrics
            if metrics:
                metrics['test_cases_generated'].inc()
        
        job.status = "COMPLETED"
        db.commit()
        
    except Exception as e:
        print(f"Error in job processing: {e}")
        job = db.query(Job).filter(Job.id == job_id).first()
        job.status = "FAILED"
        db.commit()
        raise
