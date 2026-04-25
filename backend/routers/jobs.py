from fastapi import APIRouter, HTTPException

from ..profile_manager import get_paths
from ..preference_extractor import load_preferences
from ..job_fetcher import fetch_jobs
from ..job_matcher import match_and_rank_jobs
from ..utils import load_json
from ..config import load_config

router = APIRouter(tags=["jobs"])


@router.post("/profiles/{name}/jobs/fetch")
def fetch_and_match(name: str):
    """Fetch jobs from Adzuna and match against the profile. Returns ranked job list."""
    paths = get_paths(name)
    if not paths.dir.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{name}' not found")

    profile = load_json(paths.parsed_resume_path)
    if not profile:
        raise HTTPException(status_code=400, detail="Profile not set up. Complete setup first.")

    prefs = load_preferences(str(paths.preferences_path))
    if not prefs:
        raise HTTPException(status_code=400, detail="Preferences not found. Complete setup first.")

    config = load_config()

    try:
        jobs = fetch_jobs(
            app_id=config.adzuna_app_id,
            app_key=config.adzuna_app_key,
            preferences=prefs,
            max_jobs=50,
            history_path=str(paths.job_history_path),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Job fetch failed: {exc}")

    total_fetched = len(jobs)

    matched = match_and_rank_jobs(
        profile=profile,
        jobs=jobs,
        api_key=config.openai_api_key if config.use_gpt_matching else None,
        use_gpt=config.use_gpt_matching,
        threshold=config.match_score_threshold,
        top_n=config.top_jobs_count,
    ) if jobs else []

    return {"jobs": matched, "total_fetched": total_fetched}
