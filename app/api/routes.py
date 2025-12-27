import base64
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.services.deliver import deliver_to_routebinder
from app.services.extract import extract_fields
from app.services.ingest import save_ingest_event

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def upload_form() -> str:
    return """
    <html>
      <head><title>Lantern Upload</title></head>
      <body>
        <h1>Lantern Ingest</h1>
        <form action="/ingest/image" method="post" enctype="multipart/form-data">
          <label for="file">Route sheet image:</label>
          <input type="file" id="file" name="file" accept="image/*" required />
          <button type="submit">Upload</button>
        </form>
      </body>
    </html>
    """


class EmailIngestPayload(BaseModel):
    image_base64: str = Field(..., description="Base64-encoded image data or data URL")
    filename: str = Field("route-sheet.jpg", description="Original filename")
    metadata: Optional[Dict[str, Any]] = None


@router.post("/ingest/email")
async def ingest_email(payload: EmailIngestPayload) -> Dict[str, Any]:
    try:
        image_bytes = _decode_image(payload.image_base64)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job_record = save_ingest_event(
        image_bytes=image_bytes,
        filename=payload.filename,
        metadata=payload.metadata,
        source="email",
    )
    extraction = extract_fields(job_record)
    delivery = deliver_to_routebinder(extraction)

    return {
        "status": "ok",
        "job": job_record,
        "extraction": extraction,
        "delivery": delivery,
    }


@router.post("/ingest/image")
async def ingest_image(
    file: UploadFile = File(...),
) -> Dict[str, Any]:
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty upload")

    job_record = save_ingest_event(
        image_bytes=image_bytes,
        filename=file.filename or "route-sheet.jpg",
        metadata=None,
        source="upload",
    )
    extraction = extract_fields(job_record)
    delivery = deliver_to_routebinder(extraction)

    return {
        "status": "ok",
        "job": job_record,
        "extraction": extraction,
        "delivery": delivery,
    }


def _decode_image(image_base64: str) -> bytes:
    data = image_base64
    if image_base64.startswith("data:"):
        try:
            data = image_base64.split(",", 1)[1]
        except IndexError as exc:
            raise ValueError("Invalid data URL") from exc

    try:
        return base64.b64decode(data, validate=True)
    except ValueError as exc:
        raise ValueError("Invalid base64 image") from exc
