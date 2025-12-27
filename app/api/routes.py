import base64
from typing import Any, Dict, Optional

import json

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
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
      <head>
        <title>Lantern Upload</title>
        <style>
          body { font-family: Arial, sans-serif; padding: 2rem; }
          #status { margin-top: 1rem; }
          pre { background: #f5f5f5; padding: 1rem; }
        </style>
      </head>
      <body>
        <h1>Lantern Ingest</h1>
        <form id="upload-form">
          <label for="file">Route sheet image:</label>
          <input type="file" id="file" name="file" accept="image/*" required />
          <button type="submit">Upload</button>
        </form>
        <div id="status"></div>
        <pre id="output"></pre>
        <script>
          const form = document.getElementById('upload-form');
          const status = document.getElementById('status');
          const output = document.getElementById('output');

          function setStatus(text) {
            status.textContent = text;
          }

          async function pollJob(jobId) {
            while (true) {
              const response = await fetch(`/jobs/${jobId}`);
              if (!response.ok) {
                setStatus('Failed to fetch job status');
                return;
              }
              const data = await response.json();
              output.textContent = JSON.stringify(data, null, 2);
              if (['done', 'failed'].includes(data.status)) {
                setStatus(`Job ${data.status}`);
                return;
              }
              setStatus(`Job ${data.status}...`);
              await new Promise(resolve => setTimeout(resolve, 1500));
            }
          }

          form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const fileInput = document.getElementById('file');
            if (!fileInput.files.length) {
              setStatus('Select a file first.');
              return;
            }
            setStatus('Uploading...');
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            const response = await fetch('/ingest/image', {
              method: 'POST',
              body: formData
            });
            if (!response.ok) {
              setStatus('Upload failed.');
              output.textContent = await response.text();
              return;
            }
            const data = await response.json();
            output.textContent = JSON.stringify(data, null, 2);
            setStatus('Queued. Polling for status...');
            await pollJob(data.job.id);
          });
        </script>
      </body>
    </html>
    """


class EmailIngestPayload(BaseModel):
    image_base64: str = Field(..., description="Base64-encoded image data or data URL")
    filename: str = Field("route-sheet.jpg", description="Original filename")
    metadata: Optional[Dict[str, Any]] = None


@router.post("/ingest/email")
async def ingest_email(
    payload: EmailIngestPayload, background_tasks: BackgroundTasks
) -> Dict[str, Any]:
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
    background_tasks.add_task(_process_job, job_record)

    return {
        "status": "ok",
        "job": job_record,
    }


@router.post("/ingest/image")
async def ingest_image(
    background_tasks: BackgroundTasks,
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
    background_tasks.add_task(_process_job, job_record)

    return {
        "status": "ok",
        "job": job_record,
    }


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> Dict[str, Any]:
    job_record = _load_job(job_id)
    if not job_record:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_record


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


def _load_job(job_id: str) -> Dict[str, Any] | None:
    from app.services.ingest import INBOX_JOBS_DIR

    job_path = INBOX_JOBS_DIR / f"{job_id}.json"
    if not job_path.exists():
        return None
    return json.loads(job_path.read_text(encoding="utf-8"))


def _process_job(job_record: Dict[str, Any]) -> None:
    extraction = extract_fields(job_record)
    if extraction.get("status") == "done":
        deliver_to_routebinder(extraction)
