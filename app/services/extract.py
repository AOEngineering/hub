from typing import Any, Dict


def extract_fields(job_record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "status": "queued",
        "job_id": job_record.get("id"),
        "fields": {
            "route": None,
            "site_name": None,
            "address": None,
            "city": None,
            "postal_code": None,
            "service_days": None,
            "time_open": None,
            "time_closed": None,
            "notes": None,
        },
    }
