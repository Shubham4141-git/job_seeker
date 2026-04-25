"""Job matching: GPT-powered (preferred) with keyword-based fallback."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from .utils import setup_logging

logger = setup_logging(__name__)

_GPT_MODEL = "gpt-4o-mini"  # cheapest capable model


# ──────────────────────────────────────────────
#  GPT Matching
# ──────────────────────────────────────────────

_MATCH_PROMPT = """\
You are an expert job matching assistant for Indian job seekers.
Given a candidate profile and a job listing, return ONLY a JSON object — no markdown, no extra text.

JSON shape:
{{
  "match_score": <integer 0-100>,
  "matching_reasons": [<string>, ...],
  "missing_skills": [<string>, ...],
  "salary_fit": "<Good|Okay|Poor> - <brief reason>",
  "location_fit": "<Perfect|Acceptable|Mismatch> - <brief reason>",
  "experience_fit": "<Excellent|Good|Overqualified|Underqualified>",
  "overall_recommendation": "<1-line recommendation>",
  "application_tips": [<string>, ...]
}}

Scoring guide:
- 90-100: Near-perfect match on title, skills, experience, location, salary
- 75-89 : Strong match, minor gaps
- 60-74 : Moderate match, worth applying
- Below 60: Weak match

Key profile fields to consider:
- total_years_experience & career_level for experience fit
- technical_skills for skills overlap
- target_job_titles / current_job_title for role fit
- preferred_locations & preferred_work_arrangement for location fit
- salary_min_lpa / salary_max_lpa for salary fit

Candidate Profile:
{profile}

Job:
Title: {title}
Company: {company}
Location: {location}
Salary: {salary}
Description: {description}
"""


def _call_gpt(api_key: str, profile: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)

    salary_str = _format_salary(job)
    prompt = _MATCH_PROMPT.format(
        profile=json.dumps(profile, indent=2),
        title=job.get("title", ""),
        company=job.get("company", ""),
        location=job.get("location", ""),
        salary=salary_str,
        description=job.get("description", "")[:600],
    )

    response = client.chat.completions.create(
        model=_GPT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600,
        temperature=0.2,
    )
    raw = response.choices[0].message.content or ""
    # Strip any accidental markdown fences
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    return json.loads(raw)


# ──────────────────────────────────────────────
#  Keyword Fallback Matching
# ──────────────────────────────────────────────

def _keyword_match(profile: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
    """Rule-based scoring when GPT is unavailable."""
    user_skills = {s.lower() for s in profile.get("technical_skills", [])}
    user_title = (profile.get("current_job_title") or "").lower()
    user_years = profile.get("total_years_experience", 0) or 0
    user_loc = (profile.get("current_location") or "").lower()
    salary_min = profile.get("salary_min_lpa") or 0
    salary_max = profile.get("salary_max_lpa") or 999

    job_text = f"{job.get('title','')} {job.get('description','')}".lower()
    job_title = (job.get("title") or "").lower()
    job_loc = (job.get("location") or "").lower()
    job_sal_min = job.get("salary_min_lpa") or 0
    job_sal_max = job.get("salary_max_lpa") or 999

    score = 0
    reasons: List[str] = []
    missing: List[str] = []

    # Title match (30 pts)
    title_words = set(re.findall(r"\w+", user_title))
    job_title_words = set(re.findall(r"\w+", job_title))
    title_overlap = title_words & job_title_words
    title_score = min(30, int(len(title_overlap) / max(len(title_words), 1) * 30))
    score += title_score
    if title_overlap:
        reasons.append(f"Title overlap: {', '.join(title_overlap)}")

    # Skills match (40 pts)
    skill_hits = [s for s in user_skills if s in job_text]
    if user_skills:
        skill_score = min(40, int(len(skill_hits) / len(user_skills) * 40))
    else:
        skill_score = 0
    score += skill_score
    if skill_hits:
        reasons.append(f"{len(skill_hits)} skills matched")

    # Check for skills mentioned in job but not in user profile
    all_job_tokens = set(re.findall(r"\b[a-z]+\b", job_text))
    for skill in ["kubernetes", "terraform", "kafka", "spark", "golang", "rust"]:
        if skill in all_job_tokens and skill not in user_skills:
            missing.append(skill.title())

    # Location match (15 pts)
    if "remote" in job_text or user_loc in job_loc or "india" in job_loc:
        score += 15
        reasons.append("Location matches")
    else:
        loc_score = 5 if any(c in job_loc for c in user_loc.split()) else 0
        score += loc_score

    # Salary fit (15 pts)
    if job_sal_min and job_sal_max:
        overlap = min(salary_max, job_sal_max) - max(salary_min, job_sal_min)
        if overlap > 0:
            score += 15
            reasons.append(f"Salary ₹{job_sal_min}-{job_sal_max} LPA fits range")
        else:
            reasons.append(f"Salary ₹{job_sal_min}-{job_sal_max} LPA outside range")
    else:
        score += 8  # partial credit when salary not listed

    recommendation = (
        "Strong match — apply immediately" if score >= 80
        else "Good match — worth applying" if score >= 65
        else "Partial match — apply if interested"
    )

    return {
        "match_score": min(score, 100),
        "matching_reasons": reasons,
        "missing_skills": missing[:3],
        "salary_fit": "Matched" if score >= 70 else "Not ideal",
        "location_fit": "Matched" if "remote" in job_text or user_loc in job_loc else "Check details",
        "experience_fit": "Matched",
        "overall_recommendation": recommendation,
        "application_tips": [
            "Highlight key skills in your cover letter",
            "Mention relevant projects from your resume",
        ],
    }


# ──────────────────────────────────────────────
#  Public API
# ──────────────────────────────────────────────

def _format_salary(job: Dict[str, Any]) -> str:
    lo = job.get("salary_min_lpa")
    hi = job.get("salary_max_lpa")
    if lo and hi:
        return f"₹{lo}-{hi} LPA"
    if lo:
        return f"₹{lo}+ LPA"
    return "Not specified"


def match_job(
    profile: Dict[str, Any],
    job: Dict[str, Any],
    api_key: Optional[str] = None,
    use_gpt: bool = True,
) -> Dict[str, Any]:
    """
    Return a match result dict for a single job.
    Falls back to keyword matching if GPT is unavailable or disabled.
    """
    if use_gpt and api_key:
        try:
            result = _call_gpt(api_key, profile, job)
            result.setdefault("match_score", 0)
            logger.debug("GPT match for %r: %d%%", job.get("title"), result["match_score"])
            return result
        except Exception as exc:
            logger.warning("GPT matching failed (%s), using keyword fallback", exc)

    return _keyword_match(profile, job)


def match_and_rank_jobs(
    profile: Dict[str, Any],
    jobs: List[Dict[str, Any]],
    api_key: Optional[str] = None,
    use_gpt: bool = True,
    threshold: int = 70,
    top_n: int = 8,
) -> List[Dict[str, Any]]:
    """
    Match all jobs, filter by threshold, sort by score, return top N.
    Attaches 'match_result' and 'salary_display' keys to each job dict.
    """
    results: List[Dict[str, Any]] = []

    for job in jobs:
        match = match_job(profile, job, api_key=api_key, use_gpt=use_gpt)
        score = match.get("match_score", 0)
        if score >= threshold:
            enriched = {
                **job,
                "match_result": match,
                "salary_display": _format_salary(job),
            }
            results.append(enriched)

    # Sort: match score DESC, then salary DESC
    results.sort(
        key=lambda j: (
            j["match_result"]["match_score"],
            j.get("salary_max_lpa") or 0,
        ),
        reverse=True,
    )

    logger.info(
        "%d/%d jobs above threshold=%d%%; returning top %d",
        len(results), len(jobs), threshold, min(top_n, len(results)),
    )
    return results[:top_n]
