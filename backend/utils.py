"""Shared utilities: logging, JSON I/O, date helpers."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pytz

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(name: str = "job_matcher", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    logger.addHandler(ch)

    # File handler
    fh = logging.FileHandler(LOG_DIR / "job_matcher.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    logger.addHandler(fh)

    return logger


def load_json(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def now_ist() -> datetime:
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist)


def format_date_ist(dt: datetime | None = None) -> str:
    d = dt or now_ist()
    return d.strftime("%B %d, %Y")


def format_time_ist(dt: datetime | None = None) -> str:
    d = dt or now_ist()
    return d.strftime("%I:%M %p IST")


def stars_from_score(score: int) -> str:
    if score >= 90:
        return "⭐⭐⭐⭐⭐"
    if score >= 80:
        return "⭐⭐⭐⭐"
    if score >= 70:
        return "⭐⭐⭐"
    return "⭐⭐"
