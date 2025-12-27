from __future__ import annotations

import importlib.util
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from app.services.ingest import update_job_status


@dataclass
class ExtractedFields:
    route: str | None = None
    site_name: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    service_days: str | None = None
    time_open: str | None = None
    time_closed: str | None = None
    notes: str | None = None


FIELD_PATTERNS = {
    "route": re.compile(r"route[:\\s]+(\\S+)", re.IGNORECASE),
    "site_name": re.compile(r"slang name[:\\s]+(.+)", re.IGNORECASE),
    "address": re.compile(r"address[:\\s]+(.+)", re.IGNORECASE),
    "city": re.compile(r"city[:\\s]+(.+)", re.IGNORECASE),
    "postal_code": re.compile(r"zip code[:\\s]+(.+)", re.IGNORECASE),
    "service_days": re.compile(r"service days[:\\s]+(.+)", re.IGNORECASE),
    "time_open": re.compile(r"time open[:\\s]+(.+)", re.IGNORECASE),
    "time_closed": re.compile(r"time closed[:\\s]+(.+)", re.IGNORECASE),
    "notes": re.compile(r"special notes[:\\s]+(.+)", re.IGNORECASE),
}


def extract_fields(job_record: Dict[str, Any]) -> Dict[str, Any]:
    job_id = job_record.get("id")
    update_job_status(job_id, "processing")
    image_path = job_record.get("image_path")
    if not image_path:
        update_job_status(job_id, "failed", error="missing image_path")
        return {"status": "failed", "job_id": job_id, "error": "missing image_path"}

    missing_deps = _missing_dependencies()
    if missing_deps:
        error = f"Missing dependencies: {', '.join(missing_deps)}"
        update_job_status(job_id, "failed", error=error)
        return {"status": "failed", "job_id": job_id, "error": error}

    from PIL import Image
    import pytesseract

    try:
        image = Image.open(Path(image_path))
        extracted_text = pytesseract.image_to_string(image)
    except Exception as exc:
        update_job_status(job_id, "failed", error=str(exc))
        return {"status": "failed", "job_id": job_id, "error": str(exc)}

    fields = _extract_fields_from_text(extracted_text)
    payload = {
        "status": "done",
        "job_id": job_id,
        "fields": fields.__dict__,
        "raw_text": extracted_text,
    }
    update_job_status(job_id, "done", extraction=payload)
    return payload


def _extract_fields_from_text(text: str) -> ExtractedFields:
    fields = ExtractedFields()
    normalized = " ".join(text.split())
    for key, pattern in FIELD_PATTERNS.items():
        match = pattern.search(normalized)
        if match:
            setattr(fields, key, match.group(1).strip())
    return fields


def _missing_dependencies() -> list[str]:
    missing = []
    if importlib.util.find_spec("PIL") is None:
        missing.append("pillow")
    if importlib.util.find_spec("pytesseract") is None:
        missing.append("pytesseract")
    return missing
