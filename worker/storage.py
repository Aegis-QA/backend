import boto3
from botocore.exceptions import NoCredentialsError
import os

MINIO_URL = os.getenv("MINIO_URL", "http://localhost:9000")
ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
BUCKET_NAME = "documents"

s3_client = boto3.client(
    "s3",
    endpoint_url=MINIO_URL,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    config=boto3.session.Config(signature_version='s3v4')
)

def download_file_from_minio(object_name, local_path):
    # object_name might include bucket name prefix if stored that way, 
    # but our upload logic stored it as "documents/filename" in the DB? 
    # Wait, upload logic returned "BUCKET_NAME/object_name".
    
    # Let's parse it correctly.
    # If object_name is "documents/uuid.pdf", we need to split.
    
    parts = object_name.split('/')
    if len(parts) > 1:
        bucket = parts[0]
        key = '/'.join(parts[1:])
    else:
        bucket = BUCKET_NAME
        key = object_name

    try:
        s3_client.download_file(bucket, key, local_path)
        return True
    except Exception as e:
        print(f"Download failed: {e}")
        raise e
