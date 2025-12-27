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
    "route": re.compile(r"route[:\s]*(.*)", re.IGNORECASE),
    "site_name": re.compile(r"slang name[:\s]*(.*)", re.IGNORECASE),
    "address": re.compile(r"address[:\s]*(.*)", re.IGNORECASE),
    "city": re.compile(r"city[:\s]*(.*)", re.IGNORECASE),
    "postal_code": re.compile(r"(zip code|zip)[:\s]*(.*)", re.IGNORECASE),
    "service_days": re.compile(r"service days[:\s]*(.*)", re.IGNORECASE),
    "time_open": re.compile(r"time open[:\s]*(.*)", re.IGNORECASE),
    "time_closed": re.compile(r"time closed[:\s]*(.*)", re.IGNORECASE),
    "notes": re.compile(r"special notes[:\s]*(.*)", re.IGNORECASE),
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
        message = f"OCR unavailable; missing dependencies: {', '.join(missing_deps)}"
        payload = {
            "status": "queued",
            "job_id": job_id,
            "fields": ExtractedFields().__dict__,
            "ocr_status": "unavailable",
            "message": message,
        }
        update_job_status(job_id, "queued", extraction=payload, error=message)
        return payload

    from PIL import Image
    import pytesseract
    from pytesseract import TesseractNotFoundError

    try:
        try:
            pytesseract.get_tesseract_version()
        except TesseractNotFoundError as exc:
            message = str(exc)
            payload = {
                "status": "queued",
                "job_id": job_id,
                "fields": ExtractedFields().__dict__,
                "ocr_status": "unavailable",
                "message": message,
            }
            update_job_status(job_id, "queued", extraction=payload, error=message)
            return payload
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
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    address, city, postal_code = _extract_address_block(lines)
    fields.address = address
    fields.city = city
    fields.postal_code = postal_code

    for key in ("route", "site_name", "notes"):
        value = _extract_field_from_lines(lines, key)
        if value:
            setattr(fields, key, value)

    fields.service_days = _extract_service_days(lines)
    fields.time_open = _extract_field_from_lines(lines, "time_open")
    fields.time_closed = _extract_field_from_lines(lines, "time_closed")

    if fields.postal_code:
        fields.postal_code = fields.postal_code.replace(" ", "").upper()

    return fields


def _extract_field_from_lines(lines: list[str], key: str) -> str | None:
    pattern = FIELD_PATTERNS[key]
    for index, line in enumerate(lines):
        match = pattern.search(line)
        if match:
            if key == "postal_code":
                value = match.group(2)
            else:
                value = match.group(1)
            if value.strip():
                return value.strip()
            return _collect_following_lines(lines, index + 1, stop_keys=FIELD_PATTERNS)
    return None


def _collect_following_lines(
    lines: list[str], start_index: int, *, stop_keys: dict[str, re.Pattern]
) -> str | None:
    collected: list[str] = []
    for line in lines[start_index:]:
        if any(pattern.search(line) for pattern in stop_keys.values()):
            break
        collected.append(line)
    value = " ".join(collected).strip()
    return value or None


def _extract_address_block(
    lines: list[str],
) -> tuple[str | None, str | None, str | None]:
    address = None
    city = None
    postal_code = None

    for index, line in enumerate(lines):
        if FIELD_PATTERNS["address"].search(line):
            block = _collect_block_lines(lines, index + 1, stop_keys=FIELD_PATTERNS)
            if block:
                address = block[0]
            if len(block) > 1:
                city = block[1]
            if len(block) > 2:
                postal_line = block[2]
                postal_match = re.search(r"([A-Z]{2})\s+(\d{5})", postal_line)
                if postal_match:
                    postal_code = f"{postal_match.group(1)} {postal_match.group(2)}"
            break

    return address, city, postal_code


def _extract_service_days(lines: list[str]) -> str | None:
    for index, line in enumerate(lines):
        if FIELD_PATTERNS["service_days"].search(line):
            if index + 1 < len(lines):
                candidate = lines[index + 1]
                match = re.search(
                    r"(mon|tue|wed|thu|fri|sat|sun)(?:\s*-\s*(mon|tue|wed|thu|fri|sat|sun))?",
                    candidate,
                    re.I,
                )
                if match:
                    if match.group(2):
                        return f"{match.group(1)}-{match.group(2)}".title()
                    return match.group(1).title()
    return None


def _collect_block_lines(
    lines: list[str], start_index: int, *, stop_keys: dict[str, re.Pattern]
) -> list[str]:
    collected: list[str] = []
    for line in lines[start_index:]:
        if any(pattern.search(line) for pattern in stop_keys.values()):
            break
        collected.append(line)
    return collected


def _missing_dependencies() -> list[str]:
    missing = []
    if importlib.util.find_spec("PIL") is None:
        missing.append("pillow")
    if importlib.util.find_spec("pytesseract") is None:
        missing.append("pytesseract")
    return missing
