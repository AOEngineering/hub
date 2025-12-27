from fastapi import FastAPI

from app.api.routes import router as ingest_router

app = FastAPI(title="Lantern")


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


app.include_router(ingest_router)
