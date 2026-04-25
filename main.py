"""
Daily Job Matcher — Entry Point

Usage:
  python main.py --create-profile <name>     # Step 1: create a new user profile
  python main.py --setup --profile <name>    # Step 2: parse resume + auto-setup
  python main.py --dry-run --profile <name>  # Test: run without sending email
  python main.py --profile <name>            # Run: fetch jobs + send email
  python main.py --list-profiles             # See all profiles and their status
  python main.py --test-email --profile <name>  # Verify email is working

  # Default (no --profile) uses data/ folder
  python main.py --setup
  python main.py --dry-run
  python main.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from backend.config import load_config
from backend.email_generator import send_digest
from backend.job_fetcher import fetch_jobs, mark_jobs_sent
from backend.job_matcher import match_and_rank_jobs
from backend.preference_extractor import load_preferences, merge_with_env_overrides, save_preferences
from backend.profile_builder import build_search_preferences, verify_profile
from backend.profile_manager import (
    create_profile,
    get_paths,
    list_profiles,
    load_recipient_email,
    print_profiles,
    save_recipient_email,
)
from backend.resume_parser import parse_resume
from backend.utils import load_json, now_ist, save_json, setup_logging

logger = setup_logging("job_matcher")

_DEFAULT_RESUME_DATA = "data/parsed_resume.json"
_DEFAULT_PREFERENCES = "data/user_preferences.json"
_DEFAULT_JOB_HISTORY = "data/job_history.json"
_DEFAULT_RESUME_PATH = "data/user_resume.pdf"


def _resolve_paths(profile_name: Optional[str]) -> Dict[str, str]:
    if profile_name:
        pp = get_paths(profile_name)
        return {
            "parsed_resume": str(pp.parsed_resume_path),
            "preferences": str(pp.preferences_path),
            "job_history": str(pp.job_history_path),
            "resume": str(pp.resume_path) if pp.resume_path else str(pp.dir / "resume.pdf"),
        }
    return {
        "parsed_resume": _DEFAULT_RESUME_DATA,
        "preferences": _DEFAULT_PREFERENCES,
        "job_history": _DEFAULT_JOB_HISTORY,
        "resume": _DEFAULT_RESUME_PATH,
    }


# ──────────────────────────────────────────────
#  Create profile
# ──────────────────────────────────────────────

def run_create_profile(name: str) -> None:
    if name in list_profiles():
        print(f"\n  Profile '{name}' already exists.")
        print_profiles()
        return

    paths = create_profile(name)
    print(f"\n{'═'*55}")
    print(f"  Profile '{name}' created!")
    print(f"{'═'*55}")
    print(f"\n  1. Copy your resume into:  {paths.dir}/")
    print(f"     Name it:                 resume.pdf  (or resume.docx)")
    print(f"\n  2. Run setup:")
    print(f"     python main.py --setup --profile {name}\n")


# ──────────────────────────────────────────────
#  Setup — fully automatic, asks only recipient email
# ──────────────────────────────────────────────

def run_setup(config: Any, profile_name: Optional[str] = None) -> None:
    paths = _resolve_paths(profile_name)
    label = f"profile '{profile_name}'" if profile_name else "default"

    print(f"\n{'═'*55}")
    print(f"  SETUP — {label}")
    print(f"{'═'*55}")

    # Locate resume
    resume_path = paths["resume"]
    if not Path(resume_path).exists():
        print(f"\n  Resume not found at: {resume_path}")
        resume_path = input("  Enter the full path to your resume (PDF or DOCX): ").strip()
        if not resume_path or not Path(resume_path).exists():
            print("  File not found. Please check the path and try again.")
            sys.exit(1)

    # Parse resume using LLM if available, else regex fallback
    print(f"\n  Parsing resume …")
    try:
        extracted = parse_resume(resume_path, openai_api_key=config.openai_api_key)
    except Exception as exc:
        print(f"  Resume parsing failed: {exc}")
        sys.exit(1)

    # Verify extracted fields with user + fill any gaps
    verified_profile = verify_profile(extracted)
    save_json(verified_profile, paths["parsed_resume"])

    # Build search preferences from verified profile
    prefs = build_search_preferences(verified_profile)
    if not profile_name:
        prefs = merge_with_env_overrides(prefs, config)
    save_preferences(prefs, paths["preferences"])

    # Recipient email — only thing we ask for profiles
    if profile_name:
        print()
        recipient = input("  Send job digest TO (email address): ").strip()
        if not recipient:
            print("  No email entered. You can re-run --setup to set it later.")
        else:
            save_recipient_email(profile_name, recipient)

    print(f"\n  Setup complete!")
    cmd = f"python main.py --dry-run --profile {profile_name}" if profile_name else "python main.py --dry-run"
    print(f"  Test it: {cmd}\n")


# ──────────────────────────────────────────────
#  Main job search flow
# ──────────────────────────────────────────────

def run_job_search(config: Any, dry_run: bool = False, profile_name: Optional[str] = None) -> int:
    paths = _resolve_paths(profile_name)
    label = f"profile='{profile_name}'" if profile_name else "default"

    logger.info("═" * 50)
    logger.info("Daily Job Matcher starting — %s  [%s]",
                now_ist().strftime("%Y-%m-%d %H:%M IST"), label)
    logger.info("═" * 50)

    profile = load_json(paths["parsed_resume"])
    if not profile:
        logger.error("No parsed resume found. Run: python main.py --setup%s",
                     f" --profile {profile_name}" if profile_name else "")
        return 1

    prefs = load_preferences(paths["preferences"])
    if not prefs:
        logger.error("No preferences found. Run: python main.py --setup%s",
                     f" --profile {profile_name}" if profile_name else "")
        return 1

    # .env overrides only apply to the default (non-profile) flow
    if not profile_name:
        prefs = merge_with_env_overrides(prefs, config)

    logger.info("Fetching jobs from Adzuna …")
    try:
        jobs = fetch_jobs(
            app_id=config.adzuna_app_id,
            app_key=config.adzuna_app_key,
            preferences=prefs,
            max_jobs=100,
            history_path=paths["job_history"],
        )
    except Exception as exc:
        logger.error("Job fetch failed: %s", exc)
        jobs = []

    total_fetched = len(jobs)
    logger.info("Fetched %d jobs", total_fetched)

    if jobs:
        logger.info("Matching jobs against resume …")
        top_jobs = match_and_rank_jobs(
            profile=profile,
            jobs=jobs,
            api_key=config.openai_api_key if config.use_gpt_matching else None,
            use_gpt=config.use_gpt_matching,
            threshold=config.match_score_threshold,
            top_n=config.top_jobs_count,
        )
    else:
        top_jobs = []

    logger.info("%d top-matched jobs selected", len(top_jobs))

    if dry_run:
        logger.info("[DRY RUN] Skipping email send.")
        _print_summary(top_jobs, profile_name)
        return 0

    success = send_digest(
        gmail_email=config.gmail_email,
        gmail_app_password=config.gmail_app_password,
        recipient_email=config.recipient_email,
        jobs=top_jobs,
        profile=profile,
        preferences=prefs,
        total_fetched=total_fetched,
    )

    if success:
        mark_jobs_sent(top_jobs, paths["job_history"])
        logger.info("Digest sent to %s", config.recipient_email)
        return 0
    else:
        logger.error("Failed to send digest email")
        return 1


# ──────────────────────────────────────────────
#  Test email
# ──────────────────────────────────────────────

def run_test_email(config: Any, profile_name: Optional[str] = None) -> int:
    paths = _resolve_paths(profile_name)
    dummy_jobs = [
        {
            "id": "test-001",
            "title": "Test Job — Email Verification",
            "company": "Test Company",
            "location": "India",
            "description": "This is a test job to verify your email setup.",
            "salary_min_lpa": 10.0,
            "salary_max_lpa": 20.0,
            "apply_url": "https://example.com/apply",
            "created": "2026-04-25",
            "salary_display": "10-20 LPA",
            "match_result": {
                "match_score": 95,
                "matching_reasons": ["Test email working correctly"],
                "missing_skills": [],
                "salary_fit": "Good",
                "location_fit": "Good",
                "experience_fit": "Good",
                "overall_recommendation": "Email is set up correctly!",
                "application_tips": [],
            },
        }
    ]
    profile = load_json(paths["parsed_resume"]) or {"current_job_title": "Professional", "years_of_experience": 1, "technical_skills": [], "location": "India"}
    prefs = load_preferences(paths["preferences"]) or {"preferred_job_titles": [], "salary_min_lpa": 10, "salary_max_lpa": 30, "digest_time": "08:00"}

    logger.info("Sending test email to %s …", config.recipient_email)
    success = send_digest(
        gmail_email=config.gmail_email,
        gmail_app_password=config.gmail_app_password,
        recipient_email=config.recipient_email,
        jobs=dummy_jobs,
        profile=profile,
        preferences=prefs,
        total_fetched=1,
    )
    if success:
        print(f"  Test email sent to {config.recipient_email}")
        return 0
    print("  Test email failed. Check your Gmail app password in .env")
    return 1


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────

def _print_summary(jobs: list, profile_name: Optional[str] = None) -> None:
    label = f" (profile: {profile_name})" if profile_name else ""
    print(f"\n{'─'*50}")
    print(f"  Top {len(jobs)} matched jobs — dry run{label}")
    print(f"{'─'*50}")
    for i, job in enumerate(jobs, 1):
        score = job.get("match_result", {}).get("match_score", 0)
        print(f"  #{i:2d}  [{score:3d}%]  {job.get('title','')}  —  "
              f"{job.get('company','')}  |  {job.get('salary_display','N/A')}")
    print()


# ──────────────────────────────────────────────
#  CLI
# ──────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Daily Job Matcher")
    parser.add_argument("--profile", metavar="NAME", help="Use a named profile")
    parser.add_argument("--list-profiles", action="store_true", help="List all profiles")
    parser.add_argument("--create-profile", metavar="NAME", help="Create a new profile")
    parser.add_argument("--setup", action="store_true", help="Parse resume and auto-setup")
    parser.add_argument("--test-email", action="store_true", help="Send a test email")
    parser.add_argument("--dry-run", action="store_true", help="Run without sending email")
    args = parser.parse_args()

    if args.list_profiles:
        print_profiles()
        return

    if args.create_profile:
        run_create_profile(args.create_profile)
        return

    # Load recipient email from profile if given
    recipient_email = None
    if args.profile:
        if args.profile not in list_profiles():
            print(f"\n  Profile '{args.profile}' not found.")
            print(f"  Create it: python main.py --create-profile {args.profile}\n")
            sys.exit(1)
        recipient_email = load_recipient_email(args.profile)

    try:
        config = load_config(recipient_email)
        if not args.setup:
            config.validate()
    except ValueError as exc:
        print(f"\n  Configuration error:\n{exc}\n")
        sys.exit(1)
    except KeyError as exc:
        print(f"\n  Missing environment variable: {exc}")
        print("  Copy .env.example to .env and fill in the values.\n")
        sys.exit(1)

    if args.setup:
        run_setup(config, args.profile)
    elif args.test_email:
        sys.exit(run_test_email(config, args.profile))
    else:
        sys.exit(run_job_search(config, dry_run=args.dry_run, profile_name=args.profile))


if __name__ == "__main__":
    main()
