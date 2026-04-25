"""HTML email template builder for the daily job digest."""

from __future__ import annotations

from typing import Any, Dict, List

from .utils import format_date_ist, format_time_ist, now_ist, stars_from_score

# ── Inline CSS palette ──────────────────────────────────────────────────────
_BRAND = "#1a73e8"
_SURFACE = "#f8f9fa"
_CARD_BG = "#ffffff"
_BORDER = "#e0e0e0"
_TEXT_MAIN = "#202124"
_TEXT_MUTED = "#5f6368"
_GREEN = "#34a853"
_RED = "#ea4335"


def _skill_row(skill: str, has_it: bool) -> str:
    icon = "✓" if has_it else "✗"
    color = _GREEN if has_it else _RED
    label = "You have this" if has_it else "Nice to have"
    return (
        f'<li style="margin:4px 0;color:{_TEXT_MAIN};">'
        f'<span style="color:{color};font-weight:700;">{icon}</span> '
        f'{skill} <span style="color:{_TEXT_MUTED};font-size:12px;">({label})</span></li>'
    )


def _job_card(rank: int, job: Dict[str, Any], profile: Dict[str, Any]) -> str:
    match = job.get("match_result", {})
    score = match.get("match_score", 0)
    stars = stars_from_score(score)

    user_skills_lower = {s.lower() for s in profile.get("technical_skills", [])}
    matching = match.get("matching_reasons", [])
    missing = match.get("missing_skills", [])
    tips = match.get("application_tips", [])
    recommendation = match.get("overall_recommendation", "")

    # Skill checklist: first list matched skills then missing
    all_skills = (
        [s.strip() for s in ", ".join(matching).split(",") if len(s.strip()) < 30][:5]
        + missing[:3]
    )
    skill_rows = "".join(
        _skill_row(s, s.lower() in user_skills_lower) for s in all_skills
    ) if all_skills else "<li>See job description for requirements</li>"

    tips_html = "".join(f"<li>{t}</li>" for t in tips[:3])

    apply_url = job.get("apply_url", "#")
    salary = job.get("salary_display", "Not listed")
    location = job.get("location", "India")
    company = job.get("company", "Company")
    title = job.get("title", "Role")
    created = job.get("created", "")[:10] or "Recently"

    return f"""
<div style="background:{_CARD_BG};border:1px solid {_BORDER};border-radius:12px;
            padding:24px;margin-bottom:24px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">

  <!-- Header row -->
  <div style="display:flex;justify-content:space-between;align-items:center;
              border-bottom:2px solid {_BRAND};padding-bottom:12px;margin-bottom:16px;">
    <span style="font-size:12px;color:{_TEXT_MUTED};font-weight:600;
                 text-transform:uppercase;letter-spacing:1px;">
      RANK #{rank}
    </span>
    <span style="font-size:20px;font-weight:800;color:{_BRAND};">{score}% MATCH {stars}</span>
  </div>

  <!-- Job basics -->
  <h2 style="margin:0 0 12px;color:{_TEXT_MAIN};font-size:20px;">🎯 {title}</h2>
  <table style="border-collapse:collapse;width:100%;margin-bottom:16px;">
    <tr>
      <td style="padding:4px 8px 4px 0;color:{_TEXT_MUTED};width:120px;">🏢 Company</td>
      <td style="padding:4px 0;font-weight:600;color:{_TEXT_MAIN};">{company}</td>
    </tr>
    <tr>
      <td style="padding:4px 8px 4px 0;color:{_TEXT_MUTED};">📍 Location</td>
      <td style="padding:4px 0;color:{_TEXT_MAIN};">{location}</td>
    </tr>
    <tr>
      <td style="padding:4px 8px 4px 0;color:{_TEXT_MUTED};">💰 Salary</td>
      <td style="padding:4px 0;font-weight:600;color:{_GREEN};">{salary}</td>
    </tr>
    <tr>
      <td style="padding:4px 8px 4px 0;color:{_TEXT_MUTED};">📅 Posted</td>
      <td style="padding:4px 0;color:{_TEXT_MAIN};">{created}</td>
    </tr>
  </table>

  <!-- Why it's a match -->
  <div style="background:{_SURFACE};border-radius:8px;padding:14px;margin-bottom:14px;">
    <p style="margin:0 0 6px;font-weight:700;color:{_GREEN};">✅ WHY IT'S A GREAT MATCH</p>
    <p style="margin:0;color:{_TEXT_MAIN};line-height:1.6;">{recommendation}</p>
  </div>

  <!-- Skills -->
  <div style="margin-bottom:14px;">
    <p style="margin:0 0 8px;font-weight:700;color:{_TEXT_MAIN};">📋 REQUIRED SKILLS:</p>
    <ul style="margin:0;padding-left:20px;line-height:1.8;">{skill_rows}</ul>
  </div>

  <!-- Application tips -->
  {"<div style='background:#e8f5e9;border-radius:8px;padding:14px;margin-bottom:14px;'>"
   "<p style='margin:0 0 8px;font-weight:700;color:#2e7d32;'>💡 APPLICATION TIPS:</p>"
   f"<ul style='margin:0;padding-left:20px;color:{_TEXT_MAIN};line-height:1.8;'>{tips_html}</ul></div>"
   if tips else ""}

  <!-- CTA buttons -->
  <div style="text-align:center;margin-top:16px;">
    <a href="{apply_url}"
       style="display:inline-block;background:{_BRAND};color:#fff;text-decoration:none;
              padding:12px 28px;border-radius:6px;font-weight:700;font-size:15px;
              margin:0 8px;">
      🚀 APPLY NOW
    </a>
    <a href="{apply_url}"
       style="display:inline-block;background:#fff;color:{_BRAND};text-decoration:none;
              padding:12px 28px;border-radius:6px;font-weight:700;font-size:15px;
              border:2px solid {_BRAND};margin:0 8px;">
      View Full Job
    </a>
  </div>
</div>
"""


def build_email_html(
    jobs: List[Dict[str, Any]],
    profile: Dict[str, Any],
    preferences: Dict[str, Any],
    total_fetched: int,
) -> str:
    now = now_ist()
    date_str = format_date_ist(now)
    time_str = format_time_ist(now)
    job_title = profile.get("current_job_title", "Job Seeker")
    years = profile.get("total_years_experience", 0)
    location = profile.get("current_location", "India")
    sal_min = preferences.get("salary_min_lpa", 0)
    sal_max = preferences.get("salary_max_lpa", 0)
    titles = ", ".join(preferences.get("preferred_job_titles", [job_title])[:2])

    matched_count = len(jobs)
    avg_score = (
        round(sum(j["match_result"]["match_score"] for j in jobs) / matched_count)
        if jobs else 0
    )
    match_pct = f"{matched_count/total_fetched*100:.1f}%" if total_fetched else "0%"

    cards_html = "".join(_job_card(i + 1, job, profile) for i, job in enumerate(jobs))

    no_jobs_html = """
    <div style="text-align:center;padding:40px;color:#5f6368;">
      <p style="font-size:24px;">😔</p>
      <p style="font-size:18px;font-weight:600;">No strong matches found today</p>
      <p>Total jobs scanned: {total}. Try expanding your preferences.</p>
    </div>
    """.format(total=total_fetched) if not jobs else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Daily Job Digest</title>
</head>
<body style="margin:0;padding:0;background:{_SURFACE};font-family:-apple-system,BlinkMacSystemFont,
             'Segoe UI',Roboto,sans-serif;color:{_TEXT_MAIN};">

<!-- Outer wrapper -->
<table width="100%" cellpadding="0" cellspacing="0" style="background:{_SURFACE};">
<tr><td align="center" style="padding:20px 10px;">

<!-- Main container -->
<table width="640" cellpadding="0" cellspacing="0"
       style="max-width:640px;width:100%;background:{_CARD_BG};
              border-radius:16px;overflow:hidden;
              box-shadow:0 4px 12px rgba(0,0,0,0.1);">

  <!-- ── HEADER ── -->
  <tr>
    <td style="background:linear-gradient(135deg,{_BRAND} 0%,#0d47a1 100%);
               padding:32px 32px 24px;text-align:center;color:#fff;">
      <h1 style="margin:0 0 8px;font-size:26px;font-weight:800;">
        🎯 Daily Job Digest
      </h1>
      <p style="margin:0;font-size:15px;opacity:0.9;">{date_str} · {time_str}</p>
    </td>
  </tr>

  <!-- ── SUMMARY BANNER ── -->
  <tr>
    <td style="background:#e8f0fe;padding:20px 32px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="text-align:center;padding:0 8px;">
            <p style="margin:0;font-size:28px;font-weight:800;color:{_BRAND};">{total_fetched}</p>
            <p style="margin:4px 0 0;font-size:12px;color:{_TEXT_MUTED};text-transform:uppercase;">Jobs Scanned</p>
          </td>
          <td style="text-align:center;padding:0 8px;">
            <p style="margin:0;font-size:28px;font-weight:800;color:{_GREEN};">{matched_count}</p>
            <p style="margin:4px 0 0;font-size:12px;color:{_TEXT_MUTED};text-transform:uppercase;">Top Matches</p>
          </td>
          <td style="text-align:center;padding:0 8px;">
            <p style="margin:0;font-size:28px;font-weight:800;color:{_BRAND};">{avg_score}%</p>
            <p style="margin:4px 0 0;font-size:12px;color:{_TEXT_MUTED};text-transform:uppercase;">Avg Match</p>
          </td>
        </tr>
      </table>
      <hr style="border:none;border-top:1px solid {_BORDER};margin:16px 0 12px;">
      <p style="margin:0;font-size:14px;color:{_TEXT_MUTED};text-align:center;">
        <strong>Your Profile:</strong> {job_title} · {years} yrs · {location}
        &nbsp;|&nbsp;
        <strong>Searching:</strong> {titles} · ₹{sal_min}-{sal_max} LPA
      </p>
    </td>
  </tr>

  <!-- ── JOB CARDS ── -->
  <tr>
    <td style="padding:24px 32px;">
      {cards_html}
      {no_jobs_html}
    </td>
  </tr>

  <!-- ── APPLY STRATEGY ── -->
  <tr>
    <td style="background:{_SURFACE};padding:20px 32px;border-top:1px solid {_BORDER};">
      <h3 style="margin:0 0 12px;color:{_TEXT_MAIN};">📚 Apply Strategy</h3>
      <ol style="margin:0;padding-left:20px;color:{_TEXT_MAIN};line-height:1.9;">
        <li>Apply to jobs with <strong>85%+ match</strong> first</li>
        <li>Customise your cover letter using the tips above</li>
        <li>Follow up after 1 week if no response</li>
        <li>Try a LinkedIn direct message to the recruiter</li>
      </ol>
    </td>
  </tr>

  <!-- ── FOOTER ── -->
  <tr>
    <td style="background:#f1f3f4;padding:20px 32px;text-align:center;
               border-top:1px solid {_BORDER};">
      <p style="margin:0 0 6px;color:{_TEXT_MUTED};font-size:13px;">
        Next digest: tomorrow at {preferences.get('digest_time','08:00')} IST
      </p>
      <p style="margin:0;color:{_TEXT_MUTED};font-size:12px;">
        Sent via <strong>Daily Job Matcher v2.0</strong> · India Edition
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def build_subject(jobs: List[Dict[str, Any]]) -> str:
    count = len(jobs)
    date_str = format_date_ist()
    if not jobs:
        return f"😔 Daily Job Digest — {date_str} | No strong matches today"
    top_score = jobs[0]["match_result"]["match_score"] if jobs else 0
    return f"🎯 Your Daily Job Matches — {date_str} | {count} Best Jobs Found ({top_score}% top match)"
