"""Configuration management — loads .env and provides typed access."""

from __future__ import annotations

import dataclasses
import json
import os
from dataclasses import dataclass, field
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()


def _json_list(key: str, default: List[str]) -> List[str]:
    raw = os.getenv(key, "")
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return [v.strip() for v in raw.split(",") if v.strip()]


@dataclass(frozen=True)
class Config:
    # Adzuna
    adzuna_app_id: str = field(default_factory=lambda: os.environ["ADZUNA_APP_ID"])
    adzuna_app_key: str = field(default_factory=lambda: os.environ["ADZUNA_APP_KEY"])

    # OpenAI
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    use_gpt_matching: bool = field(
        default_factory=lambda: os.getenv("USE_GPT_MATCHING", "true").lower() == "true"
    )

    # Gmail
    gmail_email: str = field(default_factory=lambda: os.environ["GMAIL_EMAIL"])
    gmail_app_password: str = field(default_factory=lambda: os.environ["GMAIL_APP_PASSWORD"])
    recipient_email: str = field(default_factory=lambda: os.environ["RECIPIENT_EMAIL"])

    # Preferences
    preferred_job_titles: List[str] = field(
        default_factory=lambda: _json_list("PREFERRED_JOB_TITLES", [])
    )
    preferred_locations: List[str] = field(
        default_factory=lambda: _json_list("PREFERRED_LOCATIONS", ["India"])
    )
    salary_min_lpa: int = field(
        default_factory=lambda: int(os.getenv("SALARY_MIN_LPA", "0"))
    )
    salary_max_lpa: int = field(
        default_factory=lambda: int(os.getenv("SALARY_MAX_LPA", "999"))
    )
    preferred_work_arrangement: List[str] = field(
        default_factory=lambda: _json_list("PREFERRED_WORK_ARRANGEMENT", [])
    )
    excluded_companies: List[str] = field(
        default_factory=lambda: _json_list("EXCLUDED_COMPANIES", [])
    )

    # Digest
    digest_time: str = field(default_factory=lambda: os.getenv("DIGEST_TIME", "08:00"))
    digest_timezone: str = field(default_factory=lambda: os.getenv("DIGEST_TIMEZONE", "IST"))
    match_score_threshold: int = field(
        default_factory=lambda: int(os.getenv("MATCH_SCORE_THRESHOLD", "70"))
    )
    top_jobs_count: int = field(
        default_factory=lambda: int(os.getenv("TOP_JOBS_COUNT", "8"))
    )

    # Resume
    resume_path: str = field(
        default_factory=lambda: os.getenv("RESUME_PATH", "data/user_resume.pdf")
    )

    def validate(self) -> None:
        """Raise ValueError with a descriptive message if required fields are missing."""
        missing = []
        if not self.adzuna_app_id or self.adzuna_app_id == "your_adzuna_app_id_here":
            missing.append("ADZUNA_APP_ID")
        if not self.adzuna_app_key or self.adzuna_app_key == "your_adzuna_app_key_here":
            missing.append("ADZUNA_APP_KEY")
        if not self.gmail_email or self.gmail_email == "your_email@gmail.com":
            missing.append("GMAIL_EMAIL")
        if not self.gmail_app_password or self.gmail_app_password == "your_16_char_app_password":
            missing.append("GMAIL_APP_PASSWORD")
        if not self.recipient_email:
            missing.append("RECIPIENT_EMAIL")
        if self.use_gpt_matching and (
            not self.openai_api_key or self.openai_api_key == "your_openai_api_key_here"
        ):
            missing.append(
                "OPENAI_API_KEY (or set USE_GPT_MATCHING=false to use keyword matching)"
            )
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                "Copy .env.example to .env and fill in the values."
            )


def load_config(recipient_email: Optional[str] = None) -> "Config":
    cfg = Config()
    if recipient_email:
        cfg = dataclasses.replace(cfg, recipient_email=recipient_email)
    return cfg
