from typing import Any, Dict

import requests

from app.config import settings


def deliver_to_routebinder(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not settings.routebinder_inbox_url:
        return {"status": "not_configured"}

    response = requests.post(settings.routebinder_inbox_url, json=payload, timeout=10)
    return {
        "status": "delivered" if response.ok else "failed",
        "status_code": response.status_code,
        "response_text": response.text,
    }
