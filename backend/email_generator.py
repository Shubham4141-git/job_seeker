"""Generate and send the daily HTML email digest via Gmail SMTP."""

from __future__ import annotations

import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List

from .email_templates import build_email_html, build_subject
from .utils import setup_logging

logger = setup_logging(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
MAX_RETRIES = 3
RETRY_DELAY = 10  # seconds


def _build_message(
    sender: str,
    recipient: str,
    subject: str,
    html_body: str,
) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Daily Job Matcher <{sender}>"
    msg["To"] = recipient

    plain = "Your daily job digest is ready. Open this email in an HTML-capable client to view it."
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg


def send_digest(
    gmail_email: str,
    gmail_app_password: str,
    recipient_email: str,
    jobs: List[Dict[str, Any]],
    profile: Dict[str, Any],
    preferences: Dict[str, Any],
    total_fetched: int,
) -> bool:
    """
    Build and send the HTML digest email.
    Returns True on success, False after all retries exhausted.
    """
    html_body = build_email_html(
        jobs=jobs,
        profile=profile,
        preferences=preferences,
        total_fetched=total_fetched,
    )
    subject = build_subject(jobs)
    message = _build_message(gmail_email, recipient_email, subject, html_body)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.login(gmail_email, gmail_app_password)
                server.sendmail(gmail_email, recipient_email, message.as_string())
            logger.info("Email sent to %s (subject: %s)", recipient_email, subject)
            return True
        except smtplib.SMTPAuthenticationError as exc:
            logger.error(
                "Gmail authentication failed. Check your app password: %s", exc
            )
            return False  # No point retrying auth failures
        except Exception as exc:
            logger.warning(
                "Email send failed (attempt %d/%d): %s", attempt, MAX_RETRIES, exc
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    logger.error("All %d email send attempts failed.", MAX_RETRIES)
    return False
