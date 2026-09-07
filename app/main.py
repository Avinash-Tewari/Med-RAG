"""FastAPI application entry point — Medical RAG Advisor."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pathlib import Path

from app.routers.api import router as api_router

app = FastAPI(
    title="MedAdvisor — Doctor's Personal RAG Advisor",
    description="Medical RAG platform for document retrieval and grounded reasoning",
    version="1.0.0",
)

# ── CORS ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes ──────────────────────────────────────────────────────────
app.include_router(api_router)

# ── Favicon ─────────────────────────────────────────────────────────────
_FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 28 28">'
    '<defs><linearGradient id="g" x1="0" y1="0" x2="28" y2="28">'
    '<stop stop-color="#34d399"/><stop offset="1" stop-color="#06b6d4"/>'
    '</linearGradient></defs>'
    '<rect x="3" y="11" width="22" height="6" rx="1.5" fill="url(#g)"/>'
    '<rect x="11" y="3" width="6" height="22" rx="1.5" fill="url(#g)"/>'
    '</svg>'
)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(content=_FAVICON_SVG, media_type="image/svg+xml")


# ── Static frontend ────────────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="static"
)

@app.get("/")
async def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")
