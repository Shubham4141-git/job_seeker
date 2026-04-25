from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..profile_manager import get_paths, create_profile, list_profiles, save_recipient_email
from ..resume_parser import parse_resume
from ..profile_builder import build_search_preferences
from ..preference_extractor import save_preferences
from ..utils import save_json
from ..config import load_config

router = APIRouter(tags=["resume"])


@router.post("/profiles/{name}/resume/upload")
async def upload_and_extract(name: str, file: UploadFile = File(...)):
    """Upload resume file → extract profile via LLM. Returns extracted fields, does NOT save yet."""
    if name not in list_profiles():
        create_profile(name)

    paths = get_paths(name)
    suffix = Path(file.filename).suffix.lower() if file.filename else ".pdf"
    if suffix not in (".pdf", ".docx", ".doc"):
        raise HTTPException(status_code=400, detail="Only PDF or DOCX files are supported")

    resume_path = paths.dir / f"resume{suffix}"
    content = await file.read()
    with open(resume_path, "wb") as f:
        f.write(content)

    try:
        config = load_config()
        extracted = parse_resume(str(resume_path), openai_api_key=config.openai_api_key)
        return {
            "extracted": extracted,
            "extraction_method": extracted.get("_extraction_method", "unknown"),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Resume parsing failed: {exc}")


class ConfirmRequest(BaseModel):
    profile: Dict[str, Any]
    target_job_titles: List[str]
    preferred_locations: List[str]
    salary_min_lpa: Optional[int] = None
    salary_max_lpa: Optional[int] = None
    preferred_work_arrangement: List[str] = []
    recipient_email: str


@router.post("/profiles/{name}/resume/confirm")
def confirm_and_save(name: str, req: ConfirmRequest):
    """Save the verified profile + derived search preferences + recipient email."""
    paths = get_paths(name)
    if not paths.dir.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{name}' not found")

    full_profile = {
        **req.profile,
        "target_job_titles": req.target_job_titles,
        "preferred_locations": req.preferred_locations,
        "salary_min_lpa": req.salary_min_lpa,
        "salary_max_lpa": req.salary_max_lpa,
        "preferred_work_arrangement": req.preferred_work_arrangement,
    }

    prefs = build_search_preferences(full_profile)

    save_json(full_profile, paths.parsed_resume_path)
    save_preferences(prefs, str(paths.preferences_path))
    save_recipient_email(name, req.recipient_email)

    return {"ok": True}
