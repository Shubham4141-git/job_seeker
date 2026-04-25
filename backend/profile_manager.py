"""Manage named profiles — each profile has its own resume, preferences, and recipient email."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .utils import setup_logging

logger = setup_logging(__name__)

PROFILES_DIR = Path("profiles")


@dataclass(frozen=True)
class ProfilePaths:
    name: str
    dir: Path
    parsed_resume_path: Path
    preferences_path: Path
    config_path: Path
    job_history_path: Path

    @property
    def resume_path(self) -> Optional[Path]:
        for ext in ("pdf", "docx", "PDF", "DOCX"):
            p = self.dir / f"resume.{ext}"
            if p.exists():
                return p
        return None


def list_profiles() -> List[str]:
    if not PROFILES_DIR.exists():
        return []
    return sorted(p.name for p in PROFILES_DIR.iterdir() if p.is_dir())


def get_paths(name: str) -> ProfilePaths:
    d = PROFILES_DIR / name
    return ProfilePaths(
        name=name,
        dir=d,
        parsed_resume_path=d / "parsed_resume.json",
        preferences_path=d / "preferences.json",
        config_path=d / "config.json",
        job_history_path=d / "job_history.json",
    )


def create_profile(name: str) -> ProfilePaths:
    paths = get_paths(name)
    paths.dir.mkdir(parents=True, exist_ok=True)
    logger.info("Created profile directory: %s", paths.dir)
    return paths


def load_recipient_email(name: str) -> Optional[str]:
    paths = get_paths(name)
    if not paths.config_path.exists():
        return None
    with open(paths.config_path) as f:
        data = json.load(f)
    return data.get("recipient_email") or None


def save_recipient_email(name: str, recipient_email: str) -> None:
    paths = get_paths(name)
    paths.dir.mkdir(parents=True, exist_ok=True)
    with open(paths.config_path, "w") as f:
        json.dump({"recipient_email": recipient_email}, f, indent=2)
    logger.info("Profile config saved: %s", paths.config_path)


def print_profiles() -> None:
    profiles = list_profiles()
    if not profiles:
        print("\n  No profiles found. Create one with: python main.py --create-profile <name>\n")
        return
    print(f"\n{'─'*50}")
    print(f"  Available profiles:")
    print(f"{'─'*50}")
    for name in profiles:
        paths = get_paths(name)
        resume   = "✅ resume" if paths.resume_path else "❌ no resume"
        prefs    = "✅ prefs"  if paths.preferences_path.exists() else "❌ no prefs"
        email    = "✅ email"  if paths.config_path.exists() else "❌ no email"
        print(f"  • {name:<25} {resume}  {prefs}  {email}")
    print(f"{'─'*50}\n")
