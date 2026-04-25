"""Fetch jobs from Adzuna API for India."""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List, Optional

import requests

from .utils import load_json, save_json, setup_logging

logger = setup_logging(__name__)

ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs/in/search/{page}"
JOB_HISTORY_PATH = "data/job_history.json"
MAX_RESULTS_PER_QUERY = 50
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF = 5  # seconds


def _job_id(job: Dict[str, Any]) -> str:
    """Stable de-duplication key based on title + company + redirect_url."""
    key = f"{job.get('title','')}{job.get('company',{}).get('display_name','')}{job.get('redirect_url','')}"
    return hashlib.md5(key.encode()).hexdigest()


def _parse_salary_lpa(raw: Optional[float]) -> Optional[float]:
    """Adzuna salaries for India are in INR/year. Convert to LPA."""
    if raw is None:
        return None
    return round(raw / 100_000, 1)


def _parse_job(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": _job_id(raw),
        "title": raw.get("title", ""),
        "company": raw.get("company", {}).get("display_name", ""),
        "location": raw.get("location", {}).get("display_name", "India"),
        "description": (raw.get("description") or "")[:1000],
        "salary_min_lpa": _parse_salary_lpa(raw.get("salary_min")),
        "salary_max_lpa": _parse_salary_lpa(raw.get("salary_max")),
        "contract_type": raw.get("contract_type", ""),
        "contract_time": raw.get("contract_time", ""),
        "category": raw.get("category", {}).get("label", ""),
        "apply_url": raw.get("redirect_url", ""),
        "created": raw.get("created", ""),
    }


def _adzuna_request(
    app_id: str,
    app_key: str,
    query: str,
    location: str,
    page: int = 1,
    results_per_page: int = MAX_RESULTS_PER_QUERY,
    salary_min: Optional[int] = None,
    max_days_old: int = 3,
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": results_per_page,
        "what": query,
        "where": location,
        "sort_by": "date",
        "max_days_old": max_days_old,
        "content-type": "application/json",
    }
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(ADZUNA_BASE.format(page=page), params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            logger.info(
                "Adzuna: query=%r location=%r page=%d → %d results",
                query, location, page, len(results),
            )
            return results
        except requests.exceptions.HTTPError as exc:
            logger.warning("Adzuna HTTP error (attempt %d/%d): %s", attempt, MAX_RETRIES, exc)
            if attempt == MAX_RETRIES:
                raise
        except requests.exceptions.RequestException as exc:
            logger.warning("Adzuna request error (attempt %d/%d): %s", attempt, MAX_RETRIES, exc)
            if attempt == MAX_RETRIES:
                raise
        time.sleep(RETRY_BACKOFF * attempt)
    return []


def fetch_jobs(
    app_id: str,
    app_key: str,
    preferences: Dict[str, Any],
    max_jobs: int = 100,
    history_path: str = JOB_HISTORY_PATH,
) -> List[Dict[str, Any]]:
    """
    Fetch jobs from Adzuna that match the user's preferences.
    Returns a deduplicated list of parsed job dicts.
    """
    job_titles: List[str] = preferences.get("preferred_job_titles", ["Software Engineer"])
    locations: List[str] = preferences.get("preferred_locations", ["India"])
    salary_min: int = preferences.get("salary_min_lpa", 0)
    skills: List[str] = preferences.get("skills_for_search", [])[:5]

    # Build search queries: titles + optional skill keywords
    queries: List[str] = []
    for title in job_titles[:3]:  # cap to avoid hitting rate limits
        queries.append(title)
        if skills:
            queries.append(f"{title} {skills[0]}")

    # Deduplicate query list
    seen_queries: set = set()
    unique_queries: List[str] = []
    for q in queries:
        if q not in seen_queries:
            seen_queries.add(q)
            unique_queries.append(q)

    # Decide locations to query
    # Map small/unrecognized cities to nearest Adzuna-supported city
    _CITY_MAP = {
        "zirakhpur": "Chandigarh",
        "zirakpur": "Chandigarh",
        "mohali": "Chandigarh",
        "panchkula": "Chandigarh",
    }
    search_locations: List[str] = []
    for loc in locations:
        if loc.lower() in ("remote", "hybrid"):
            search_locations.append("India")
        else:
            search_locations.append(_CITY_MAP.get(loc.lower(), loc))
    search_locations = list(dict.fromkeys(search_locations)) or ["India"]

    all_jobs: Dict[str, Dict[str, Any]] = {}
    loaded = False

    for query in unique_queries:
        for loc in search_locations[:2]:  # cap locations
            if len(all_jobs) >= max_jobs:
                break
            try:
                raw_jobs = _adzuna_request(
                    app_id=app_id,
                    app_key=app_key,
                    query=query,
                    location=loc,
                    salary_min=salary_min if salary_min > 0 else None,
                )
                for raw in raw_jobs:
                    job = _parse_job(raw)
                    if job["id"] not in all_jobs:
                        all_jobs[job["id"]] = job
            except Exception as exc:
                logger.error("Failed to fetch jobs (query=%r, loc=%r): %s", query, loc, exc)

    jobs = list(all_jobs.values())

    # Filter out previously sent jobs
    history = _load_job_history(history_path)
    seen_ids = set(history.get("sent_ids", []))
    new_jobs = [j for j in jobs if j["id"] not in seen_ids]

    logger.info("Fetched %d total, %d new (after history filter)", len(jobs), len(new_jobs))
    return new_jobs[:max_jobs]


def mark_jobs_sent(jobs: List[Dict[str, Any]], path: str = JOB_HISTORY_PATH) -> None:
    """Record sent job IDs to avoid resending in future runs."""
    history = _load_job_history(path)
    sent_ids: List[str] = history.get("sent_ids", [])
    new_ids = [j["id"] for j in jobs]
    updated = list(dict.fromkeys(sent_ids + new_ids))[-500:]
    save_json({"sent_ids": updated}, path)


def _load_job_history(path: str = JOB_HISTORY_PATH) -> Dict[str, Any]:
    return load_json(path)
