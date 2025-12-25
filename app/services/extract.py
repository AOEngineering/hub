from typing import Any, Dict


def extract_fields(job_record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "status": "not_implemented",
        "job_id": job_record.get("id"),
    }
