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

def upload_file_to_minio(file_obj, object_name):
    try:
        s3_client.upload_fileobj(file_obj, BUCKET_NAME, object_name)
        return f"{BUCKET_NAME}/{object_name}"
    except NoCredentialsError:
        return None
