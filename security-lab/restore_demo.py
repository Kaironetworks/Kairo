"""Restore the exact evidence bytes saved by tamper_demo.py."""

import io
import os
import re
from pathlib import Path

from minio import Minio

BACKUP = Path(__file__).with_name(".kairo_tamper_backup.bin")
PREFIX = "cases/CASE-KR-2026-001/documents/1/"
VERSION_RE = re.compile(r"/v(\d+)/")


def env(name, default=None):
    return os.getenv(name, default)


def main():
    if not BACKUP.exists():
        raise SystemExit("No tamper backup found. Run tamper_demo.py first.")

    client = Minio(
        env("MINIO_ENDPOINT", "127.0.0.1:9000"),
        access_key=env("MINIO_ACCESS_KEY", "kairo"),
        secret_key=env("MINIO_SECRET_KEY", "kairo-secret"),
        secure=False,
    )
    bucket = env("MINIO_BUCKET", "kairo-documents")

    objects = list(client.list_objects(bucket, prefix=PREFIX, recursive=True))
    candidates = []
    for obj in objects:
        match = VERSION_RE.search(obj.object_name)
        if match:
            candidates.append((int(match.group(1)), obj.object_name))
    if not candidates:
        raise SystemExit("No versioned evidence object found.")

    version, object_name = max(candidates, key=lambda item: item[0])
    clean = BACKUP.read_bytes()
    client.put_object(
        bucket,
        object_name,
        io.BytesIO(clean),
        length=len(clean),
        content_type="application/octet-stream",
    )
    BACKUP.unlink(missing_ok=True)
    print(f"Restored exact pre-tamper bytes for v{version}: {object_name}")
    print("Run KAIRO verification again. Expected: VERIFIED / CONTROLLED.")


if __name__ == "__main__":
    main()
