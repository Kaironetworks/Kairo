"""Restore the exact evidence bytes saved by tamper_demo.py."""

import io
import os
import re
from pathlib import Path

import boto3
from botocore.client import Config

BACKUP = Path(__file__).with_name(".kairo_tamper_backup.bin")
PREFIX = "cases/CASE-KR-2026-001/documents/1/"
VERSION_RE = re.compile(r"/v(\d+)/")


def env(name, default=None):
    return os.getenv(name, default)


def main():
    if not BACKUP.exists():
        raise SystemExit("No tamper backup found. Run tamper_demo.py first.")

    client = boto3.client("s3", endpoint_url=env("MINIO_ENDPOINT", "http://127.0.0.1:9000"), aws_access_key_id=env("MINIO_ACCESS_KEY", "kairoadmin"), aws_secret_access_key=env("MINIO_SECRET_KEY", "kairo_minio_password"), region_name="us-east-1", config=Config(signature_version="s3v4", connect_timeout=3, read_timeout=5, retries={"max_attempts": 1}))
    bucket = env("MINIO_BUCKET", "kairo-documents")

    objects = [{"object_name": x["Key"]} for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=PREFIX) for x in page.get("Contents", [])]
    candidates = []
    for obj in objects:
        match = VERSION_RE.search(obj["object_name"])
        if match:
            candidates.append((int(match.group(1)), obj["object_name"]))
    if not candidates:
        raise SystemExit("No versioned evidence object found.")

    version, object_name = max(candidates, key=lambda item: item[0])
    clean = BACKUP.read_bytes()
    client.put_object(Bucket=bucket, Key=object_name, Body=clean, ContentType="application/pdf")
    BACKUP.unlink(missing_ok=True)
    print(f"Restored exact pre-tamper bytes for v{version}: {object_name}")
    print("Run KAIRO verification again. Expected: VERIFIED / CONTROLLED.")


if __name__ == "__main__":
    main()
