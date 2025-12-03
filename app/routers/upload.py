from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Job
from app.storage import upload_file_to_minio
from kafka import KafkaProducer
from dotenv import load_dotenv
import json
import uuid
import os

# Load environment variables
load_dotenv()

router = APIRouter()

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")

# Lazy initialize Kafka producer
_producer = None

def get_kafka_producer():
    global _producer
    if _producer is None:
        try:
            print(f"🔌 Connecting to Kafka at {KAFKA_BOOTSTRAP_SERVERS}...")
            # Convert to list if string
            servers = [KAFKA_BOOTSTRAP_SERVERS] if isinstance(KAFKA_BOOTSTRAP_SERVERS, str) else KAFKA_BOOTSTRAP_SERVERS
            
            _producer = KafkaProducer(
                bootstrap_servers=servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                api_version=(0, 10, 1),  # Explicit API version
                retries=3
            )
            print(f"✅ Kafka producer connected successfully")
        except Exception as e:
            print(f"❌ Failed to create Kafka producer: {e}")
            import traceback
            traceback.print_exc()
            raise
    return _producer

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(None),  # Made optional
    images: list[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    # Handle document upload
    unique_filename = None
    original_filename = None
    
    if file and file.filename:
        # Store original filename
        original_filename = file.filename
        file_extension = file.filename.split(".")[-1]
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        
        # Upload to MinIO
        try:
            upload_file_to_minio(file.file, unique_filename)
            print(f"Successfully uploaded file: {unique_filename}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"File upload failed: {e}")

    # Upload images if provided
    image_paths = []
    if images and images != [None]:  # Check if images were actually provided
        print(f"Processing {len(images)} images")
        for img in images:
            if img is None:
                continue
            print(f"Processing image: {img.filename}")
            img_extension = img.filename.split(".")[-1]
            if img_extension.lower() not in ["jpg", "jpeg", "png", "gif", "bmp", "webp"]:
                print(f"Skipping invalid image type: {img_extension}")
                continue  # Skip invalid image types
            
            unique_img_name = f"{uuid.uuid4()}.{img_extension}"
            try:
                upload_file_to_minio(img.file, unique_img_name)
                image_paths.append(unique_img_name)
                print(f"Successfully uploaded image: {unique_img_name}")
            except Exception as e:
                print(f"Failed to upload image {img.filename}: {e}")
    
    print(f"Final image_paths list: {image_paths}")
    
    # Set a meaningful filename if no document was provided
    if not original_filename:
        if image_paths:
            original_filename = f"📸 {len(image_paths)} image{'s' if len(image_paths) > 1 else ''}"
        else:
            original_filename = "No file"

    # Create Job in DB - ensure image_paths is always a list, never None
    new_job = Job(
        filename=original_filename, 
        file_path=unique_filename,  # Can be None for image-only jobs
        image_paths=image_paths if image_paths else [],  # Ensure it's a list, not None
        status="PENDING"
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    # Send job to Kafka queue
    try:
        producer = get_kafka_producer()
        message = {"job_id": new_job.id}
        producer.send('job-processing', value=message)
        producer.flush()  # Ensure message is sent
        print(f"✅ Sent job {new_job.id} to Kafka queue")
    except Exception as e:
        print(f"⚠️ Failed to send to Kafka: {e}")
        # Job is still in DB with PENDING status

    return {
        "job_id": new_job.id, 
        "status": "PENDING", 
        "filename": new_job.filename, 
        "images_uploaded": len(image_paths),
        "has_document": file is not None
    }
