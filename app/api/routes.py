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
        <script src="https://cdn.tailwindcss.com"></script>
      </head>
      <body class="bg-slate-950 text-slate-100 min-h-screen">
        <div class="max-w-5xl mx-auto px-6 py-10">
          <h1 class="text-3xl font-semibold mb-6">Lantern Ingest</h1>
          <div class="grid gap-6 md:grid-cols-2">
            <div class="bg-slate-900 rounded-xl p-6 shadow-lg">
              <form id="upload-form" class="space-y-4">
                <div>
                  <label for="file" class="block text-sm font-medium text-slate-300">
                    Route sheet image
                  </label>
                  <input type="file" id="file" name="file" accept="image/*" required
                    class="mt-2 block w-full text-sm text-slate-200 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-500 file:text-white hover:file:bg-indigo-400" />
                </div>
                <button type="submit"
                  class="inline-flex items-center justify-center rounded-lg bg-indigo-500 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-400">
                  Upload
                </button>
              </form>
              <div id="status" class="mt-4 text-sm text-slate-300"></div>
              <div class="mt-3 h-2 w-full rounded-full bg-slate-800">
                <div id="progress-bar" class="h-2 w-0 rounded-full bg-emerald-400 transition-all"></div>
              </div>
            </div>
            <div class="bg-slate-900 rounded-xl p-6 shadow-lg">
              <div class="text-sm font-semibold text-slate-300 mb-2">Preview</div>
              <div class="aspect-video bg-slate-800 rounded-lg flex items-center justify-center overflow-hidden">
                <img id="preview" src="" alt="Preview" class="hidden w-full h-full object-contain" />
                <span id="preview-placeholder" class="text-slate-500 text-sm">No image uploaded yet</span>
              </div>
            </div>
          </div>
          <div class="mt-6 bg-slate-900 rounded-xl p-6 shadow-lg">
            <div class="text-sm font-semibold text-slate-300 mb-2">Extraction output</div>
            <pre id="output" class="text-xs text-slate-100 whitespace-pre-wrap"></pre>
          </div>
        </div>
        <script>
          const form = document.getElementById('upload-form');
          const status = document.getElementById('status');
          const output = document.getElementById('output');
          const preview = document.getElementById('preview');
          const previewPlaceholder = document.getElementById('preview-placeholder');
          const progressBar = document.getElementById('progress-bar');

          function setStatus(text) {
            status.textContent = text;
          }

          function setProgress(percent) {
            progressBar.style.width = `${percent}%`;
          }

          function showPreview(file) {
            const url = URL.createObjectURL(file);
            preview.src = url;
            preview.classList.remove('hidden');
            previewPlaceholder.classList.add('hidden');
          }

          async function pollJob(jobId) {
            while (true) {
              const response = await fetch(`/jobs/${jobId}`);
              if (!response.ok) {
                setStatus('Failed to fetch job status');
                setProgress(0);
                return;
              }
              const data = await response.json();
              output.textContent = JSON.stringify(data, null, 2);
              if (['done', 'failed'].includes(data.status)) {
                setStatus(`Job ${data.status}`);
                setProgress(data.status === 'done' ? 100 : 100);
                return;
              }
              if (data.status === 'queued') {
                setProgress(30);
              } else if (data.status === 'processing') {
                setProgress(70);
              }
              setStatus(`Job ${data.status}...`);
              await new Promise(resolve => setTimeout(resolve, 1500));
            }
          }

          async function uploadFile(file) {
            showPreview(file);
            setStatus('Uploading...');
            setProgress(10);
            const formData = new FormData();
            formData.append('file', file);
            const response = await fetch('/ingest/image', {
              method: 'POST',
              body: formData
            });
            if (!response.ok) {
              setStatus('Upload failed.');
              output.textContent = await response.text();
              setProgress(0);
              return;
            }
            const data = await response.json();
            output.textContent = JSON.stringify(data, null, 2);
            setStatus('Queued. Polling for status...');
            setProgress(30);
            await pollJob(data.job.id);
          }

          form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const fileInput = document.getElementById('file');
            if (!fileInput.files.length) {
              setStatus('Select a file first.');
              return;
            }
            await uploadFile(fileInput.files[0]);
          });

          document.getElementById('file').addEventListener('change', async (event) => {
            const file = event.target.files[0];
            if (file) {
              await uploadFile(file);
            }
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
