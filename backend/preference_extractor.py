"""Load, save, and apply .env overrides to search preferences."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .utils import load_json, save_json, setup_logging

logger = setup_logging(__name__)

PREFERENCES_PATH = "data/user_preferences.json"


def load_preferences(path: str = PREFERENCES_PATH) -> Optional[Dict[str, Any]]:
    data = load_json(path)
    return data if data else None


def save_preferences(prefs: Dict[str, Any], path: str = PREFERENCES_PATH) -> None:
    save_json(prefs, path)
    logger.info("Preferences saved to %s", path)


def merge_with_env_overrides(prefs: Dict[str, Any], config: Any) -> Dict[str, Any]:
    """Apply .env / GitHub Secrets overrides on top of saved preferences.
    Only used for the default (no --profile) flow.
    """
    updated = dict(prefs)
    if config.preferred_job_titles:
        updated["preferred_job_titles"] = config.preferred_job_titles
    if config.preferred_locations:
        updated["preferred_locations"] = config.preferred_locations
    if config.salary_min_lpa:
        updated["salary_min_lpa"] = config.salary_min_lpa
    if config.salary_max_lpa:
        updated["salary_max_lpa"] = config.salary_max_lpa
    if config.preferred_work_arrangement:
        updated["preferred_work_arrangement"] = config.preferred_work_arrangement
    if config.excluded_companies:
        updated["excluded_companies"] = config.excluded_companies
    updated["digest_time"] = config.digest_time
    updated["digest_timezone"] = config.digest_timezone
    return updated
