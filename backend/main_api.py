"""FastAPI entry point. Run from project root: uvicorn backend.main_api:app --reload"""

import os
from pathlib import Path

# Ensure cwd = project root so runtime paths (profiles/, data/, logs/) resolve correctly
_ROOT = Path(__file__).resolve().parent.parent
os.chdir(_ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import profiles, resume, jobs, email as email_router

app = FastAPI(title="Job Seeker API", version="1.0.0", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profiles.router, prefix="/api")
app.include_router(resume.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(email_router.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config/status")
def config_status():
    """Check which API keys are configured (without exposing values)."""
    import os as _os
    return {
        "adzuna": bool(_os.getenv("ADZUNA_APP_ID") and _os.getenv("ADZUNA_APP_KEY")),
        "openai": bool(_os.getenv("OPENAI_API_KEY")),
        "gmail": bool(_os.getenv("GMAIL_EMAIL") and _os.getenv("GMAIL_APP_PASSWORD")),
    }
