"""Controlled KAIRO evidence-tamper demonstration.

The script intentionally bypasses the KAIRO version-creation workflow and changes
only the latest object belonging to KAIRO-DOC-00001 in the local MinIO bucket.
It first saves the clean bytes locally so restore_demo.py can put the exact
original object back. No exploit is used and no other object is touched.

Run from the KAIRO backend environment:
    python security-lab/tamper_demo.py

Then:
    1. Open KAIRO -> Investigations -> CASE-KR-2026-001.
    2. Inspect KAIRO-DOC-00001.
    3. Click Verify current bytes.
    4. Expected: FAILED + INTEGRITY INCIDENT.

Restore the exact pre-tamper bytes with:
    python security-lab/restore_demo.py
"""

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
    endpoint = env("MINIO_ENDPOINT", "http://127.0.0.1:9000")
    access = env("MINIO_ACCESS_KEY", "kairoadmin")
    secret = env("MINIO_SECRET_KEY", "kairo_minio_password")
    bucket = env("MINIO_BUCKET", "kairo-documents")

    client = boto3.client("s3", endpoint_url=endpoint, aws_access_key_id=access, aws_secret_access_key=secret, region_name="us-east-1", config=Config(signature_version="s3v4", connect_timeout=3, read_timeout=5, retries={"max_attempts": 1}))
    objects = [{"object_name": x["Key"]} for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=PREFIX) for x in page.get("Contents", [])]

    candidates = []
    for obj in objects:
        match = VERSION_RE.search(obj["object_name"])
        if match:
            candidates.append((int(match.group(1)), obj["object_name"]))

    if not candidates:
        raise SystemExit(f"No versioned evidence objects found under {bucket}/{PREFIX}")

    version, object_name = max(candidates, key=lambda item: item[0])
    clean = client.get_object(Bucket=bucket, Key=object_name)["Body"].read()
    BACKUP.write_bytes(clean)

    payload = (
        b"KAIRO-TAMPER-LAB\n"
        b"This payload intentionally replaces the stored evidence bytes.\n"
        b"It was written outside the authorized KAIRO version workflow.\n"
    )

    print("KAIRO TAMPER LAB")
    print("----------------")
    print(f"Target: {bucket}/{object_name}")
    print(f"Target version: v{version}")
    print(f"Clean bytes backed up to: {BACKUP}")
    print("Writing controlled altered bytes outside KAIRO...")

    client.put_object(Bucket=bucket, Key=object_name, Body=payload, ContentType="application/octet-stream")

    print("DONE: stored evidence bytes changed without creating a KAIRO version.")
    print("Now open KAIRO and run Verify current bytes.")
    print("Expected: FAILED / INTEGRITY INCIDENT.")


if __name__ == "__main__":
    main()
