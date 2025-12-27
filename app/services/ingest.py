import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from app.config import settings

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / settings.data_dir
INBOX_RAW_DIR = DATA_DIR / "inbox_raw"
INBOX_JOBS_DIR = DATA_DIR / "inbox_jobs"


def _ensure_dirs() -> None:
    INBOX_RAW_DIR.mkdir(parents=True, exist_ok=True)
    INBOX_JOBS_DIR.mkdir(parents=True, exist_ok=True)


def save_ingest_event(
    *,
    image_bytes: bytes,
    filename: str,
    metadata: Optional[Dict[str, Any]],
    source: str,
) -> Dict[str, Any]:
    _ensure_dirs()
    job_id = uuid4().hex
    timestamp = datetime.now(timezone.utc).isoformat()
    image_path = INBOX_RAW_DIR / f"{job_id}_{filename}"
    image_path.write_bytes(image_bytes)

    job_record = {
        "id": job_id,
        "received_at": timestamp,
        "source": source,
        "metadata": metadata or {},
        "image_path": str(image_path),
        "status": "queued",
    }
    job_path = INBOX_JOBS_DIR / f"{job_id}.json"
    job_path.write_text(json.dumps(job_record, indent=2), encoding="utf-8")

    return job_record
