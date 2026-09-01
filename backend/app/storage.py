import io
import boto3
from botocore.client import Config
from .config import settings

def client():
    return boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        region_name="us-east-1",
        config=Config(signature_version="s3v4"),
    )

def ensure_bucket():
    s3 = client()
    try:
        s3.head_bucket(Bucket=settings.minio_bucket)
    except Exception:
        s3.create_bucket(Bucket=settings.minio_bucket)

def put_bytes(key: str, data: bytes, content_type: str):
    client().put_object(
        Bucket=settings.minio_bucket,
        Key=key,
        Body=io.BytesIO(data),
        ContentType=content_type or "application/octet-stream",
    )

def get_bytes(key: str) -> bytes:
    obj = client().get_object(Bucket=settings.minio_bucket, Key=key)
    return obj["Body"].read()
