from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List

from ..profile_manager import get_paths, load_recipient_email
from ..preference_extractor import load_preferences
from ..email_generator import send_digest
from ..job_fetcher import mark_jobs_sent
from ..utils import load_json
from ..config import load_config

router = APIRouter(tags=["email"])


class SendEmailRequest(BaseModel):
    jobs: List[Dict[str, Any]]


@router.post("/profiles/{name}/email/send")
def send_email(name: str, req: SendEmailRequest):
    """Send matched jobs digest to the profile's recipient email."""
    paths = get_paths(name)
    if not paths.dir.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{name}' not found")

    recipient = load_recipient_email(name)
    if not recipient:
        raise HTTPException(status_code=400, detail="No recipient email configured for this profile")

    profile = load_json(paths.parsed_resume_path) or {}
    prefs = load_preferences(str(paths.preferences_path)) or {}
    config = load_config(recipient)

    success = send_digest(
        gmail_email=config.gmail_email,
        gmail_app_password=config.gmail_app_password,
        recipient_email=recipient,
        jobs=req.jobs,
        profile=profile,
        preferences=prefs,
        total_fetched=len(req.jobs),
    )

    if success:
        mark_jobs_sent(req.jobs, str(paths.job_history_path))
        return {"ok": True, "message": f"Digest sent to {recipient}"}
    return {"ok": False, "message": "Failed to send email. Check Gmail credentials in .env"}


@router.post("/profiles/{name}/email/test")
def test_email(name: str):
    """Send a test email to verify Gmail setup."""
    paths = get_paths(name)
    if not paths.dir.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{name}' not found")

    recipient = load_recipient_email(name)
    if not recipient:
        raise HTTPException(status_code=400, detail="No recipient email configured for this profile")

    config = load_config(recipient)

    dummy = [{
        "id": "test-001",
        "title": "Test Role — Email Verification",
        "company": "Test Company",
        "location": "India",
        "description": "Test email to verify SMTP setup.",
        "salary_min_lpa": 10.0,
        "salary_max_lpa": 20.0,
        "apply_url": "https://example.com",
        "created": "2026-04-25",
        "salary_display": "10–20 LPA",
        "match_result": {
            "match_score": 95,
            "matching_reasons": ["Email is working correctly"],
            "missing_skills": [],
            "salary_fit": "Good",
            "location_fit": "Good",
            "experience_fit": "Good",
            "overall_recommendation": "This is a test — your email is configured correctly!",
            "application_tips": [],
        },
    }]

    success = send_digest(
        gmail_email=config.gmail_email,
        gmail_app_password=config.gmail_app_password,
        recipient_email=recipient,
        jobs=dummy,
        profile={},
        preferences={},
        total_fetched=1,
    )

    if success:
        return {"ok": True, "message": f"Test email sent to {recipient}"}
    return {"ok": False, "message": "Failed. Check GMAIL_EMAIL and GMAIL_APP_PASSWORD in .env"}
