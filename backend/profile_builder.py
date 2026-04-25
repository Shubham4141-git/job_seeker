"""
Interactive profile builder — verifies LLM-extracted fields with the user
and derives search preferences from the confirmed profile.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .utils import setup_logging

logger = setup_logging(__name__)

# Fields shown to user for verification, in order
# (field_key, display_label, type)
_VERIFY_FIELDS = [
    ("full_name",              "Full name",                   "str"),
    ("current_job_title",      "Current / most recent title", "str"),
    ("total_years_experience", "Total years of experience",   "float"),
    ("career_level",           "Career level",                "choice:fresher,junior,mid,senior,lead,manager,director"),
    ("current_location",       "Current location / city",     "str"),
    ("industry_domain",        "Industry / domain",           "str"),
    ("technical_skills",       "Technical skills",            "list"),
    ("education",              "Highest education",           "education"),
]


def _print_header(title: str) -> None:
    print(f"\n{'═'*55}")
    print(f"  {title}")
    print(f"{'═'*55}\n")


def _ask(label: str, current: Any, field_type: str) -> Any:
    """
    Show the extracted value and ask user to confirm or correct.
    Returns the confirmed/corrected value, or the original if user presses Enter.
    Returns None if user types 'skip'.
    """
    if field_type == "list":
        display = ", ".join(current) if current else "none found"
    elif field_type == "education":
        if current:
            e = current[0] if isinstance(current, list) else current
            display = f"{e.get('degree','')} {e.get('field','')} — {e.get('institution','')} {e.get('year','') or ''}".strip()
        else:
            display = "not found"
    else:
        display = str(current) if current is not None else "not found"

    print(f"  {label}:")
    print(f"    Extracted : {display}")
    raw = input(f"    Confirm (Enter = keep, type to correct, 'skip' = leave blank): ").strip()

    if raw.lower() == "skip":
        return None
    if not raw:
        return current  # keep extracted value

    # Parse user input based on type
    if field_type == "float":
        try:
            return float(raw)
        except ValueError:
            print("    Invalid number, keeping extracted value.")
            return current

    if field_type.startswith("choice:"):
        choices = field_type.split(":")[1].split(",")
        if raw.lower() in choices:
            return raw.lower()
        print(f"    Must be one of: {', '.join(choices)}. Keeping extracted value.")
        return current

    if field_type == "list":
        return [v.strip() for v in raw.split(",") if v.strip()]

    if field_type == "education":
        # Accept free text like "B.Tech Computer Science — IIT Delhi 2022"
        return [{"degree": raw, "field": None, "institution": None, "year": None}]

    return raw  # str


def _ask_missing(label: str, field_type: str) -> Any:
    """Ask for a field that couldn't be extracted at all."""
    print(f"  {label}:")
    print(f"    Could not extract this from your resume.")
    raw = input(f"    Enter value (or press Enter to skip): ").strip()

    if not raw:
        return None

    if field_type == "float":
        try:
            return float(raw)
        except ValueError:
            return None

    if field_type.startswith("choice:"):
        choices = field_type.split(":")[1].split(",")
        if raw.lower() in choices:
            return raw.lower()
        return None

    if field_type == "list":
        return [v.strip() for v in raw.split(",") if v.strip()]

    return raw


def verify_profile(extracted: Dict[str, Any]) -> Dict[str, Any]:
    """
    Walk through extracted fields, confirm with user, fill gaps.
    Returns a clean verified profile dict.
    """
    _print_header("RESUME EXTRACTION — PLEASE VERIFY")
    print("  We extracted the following from your resume.")
    print("  Press Enter to confirm each field, or type a correction.\n")

    method = extracted.get("_extraction_method", "unknown")
    if method == "regex":
        print("  ⚠  Note: LLM extraction was unavailable. Regex was used — accuracy may be lower.\n")

    verified: Dict[str, Any] = {}

    for key, label, field_type in _VERIFY_FIELDS:
        value = extracted.get(key)
        print()
        if value is not None and value != [] and value != "":
            verified[key] = _ask(label, value, field_type)
        else:
            verified[key] = _ask_missing(label, field_type)

    # Keep remaining fields from extraction without asking (work_experiences, email, etc.)
    for k, v in extracted.items():
        if k not in verified and k != "_extraction_method":
            verified[k] = v

    # Ask for search preferences (job targets + salary) — the few things resume can't tell us
    print()
    print(f"{'─'*55}")
    print("  A few quick questions for job searching:\n")

    verified["target_job_titles"] = _ask_search_titles(verified.get("current_job_title"))
    verified["salary_min_lpa"] = _ask_salary_min()
    verified["salary_max_lpa"] = _ask_salary_max()
    verified["preferred_locations"] = _ask_locations(verified.get("current_location"))
    verified["preferred_work_arrangement"] = _ask_work_arrangement()

    return verified


def _ask_search_titles(current_title: Optional[str]) -> List[str]:
    suggestion = current_title or ""
    print(f"  What job titles are you targeting?")
    print(f"    Suggestion : {suggestion}")
    raw = input("    Enter titles (comma-separated, or Enter to use suggestion): ").strip()
    if not raw:
        return [suggestion] if suggestion else []
    return [v.strip() for v in raw.split(",") if v.strip()]


def _ask_salary_min() -> Optional[int]:
    raw = input("  Minimum expected salary (LPA)? (Enter to skip): ").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _ask_salary_max() -> Optional[int]:
    raw = input("  Maximum expected salary (LPA)? (Enter to skip): ").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _ask_locations(current_location: Optional[str]) -> List[str]:
    suggestion = current_location or "India"
    print(f"  Preferred job locations?")
    print(f"    Suggestion : {suggestion}, Remote")
    raw = input("    Enter cities (comma-separated, or Enter to use suggestion): ").strip()
    if not raw:
        locs = [suggestion] if suggestion else []
        if "Remote" not in locs:
            locs.append("Remote")
        return locs
    return [v.strip() for v in raw.split(",") if v.strip()]


def _ask_work_arrangement() -> List[str]:
    print("  Preferred work arrangement?")
    print("    Options: Remote, Hybrid, On-site")
    raw = input("    Enter (comma-separated, or Enter to skip): ").strip()
    if not raw:
        return []
    return [v.strip() for v in raw.split(",") if v.strip()]


# ──────────────────────────────────────────────
#  Build search preferences from verified profile
# ──────────────────────────────────────────────

def build_search_preferences(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Derive Adzuna search params + GPT matching context from verified profile."""
    titles = profile.get("target_job_titles") or []
    if not titles and profile.get("current_job_title"):
        titles = [profile["current_job_title"]]

    locations = profile.get("preferred_locations") or ["India"]

    return {
        "preferred_job_titles": titles,
        "preferred_locations": locations,
        "salary_min_lpa": profile.get("salary_min_lpa") or 0,
        "salary_max_lpa": profile.get("salary_max_lpa") or 999,
        "preferred_work_arrangement": profile.get("preferred_work_arrangement") or [],
        "excluded_companies": [],
        "skills_for_search": (profile.get("technical_skills") or [])[:8],
        "digest_time": "08:00",
        "digest_timezone": "IST",
        "employment_type": ["Full-time"],
    }
