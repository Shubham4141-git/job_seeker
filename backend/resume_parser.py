"""Resume parser: PDF/DOCX → raw text → structured profile via LLM (with regex fallback)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils import setup_logging

logger = setup_logging(__name__)

# ──────────────────────────────────────────────
#  Text extraction (PDF / DOCX)
# ──────────────────────────────────────────────

def extract_text(resume_path: str) -> str:
    path = Path(resume_path)
    if not path.exists():
        raise FileNotFoundError(f"Resume not found: {resume_path}")
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_text_pdf(path)
    if suffix in (".docx", ".doc"):
        return _extract_text_docx(path)
    raise ValueError(f"Unsupported file type: {suffix}. Use PDF or DOCX.")


def _extract_text_pdf(path: Path) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as exc:
        logger.error("PDF extraction failed: %s", exc)
        raise


def _extract_text_docx(path: Path) -> str:
    try:
        from docx import Document
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as exc:
        logger.error("DOCX extraction failed: %s", exc)
        raise


# ──────────────────────────────────────────────
#  LLM extraction
# ──────────────────────────────────────────────

_LLM_PROMPT = """\
You are an expert resume parser. Extract structured information from the resume text below.

Return ONLY a valid JSON object with exactly these fields (use null if information is not found):

{{
  "full_name": "string or null",
  "email": "string or null",
  "current_job_title": "most recent job title as a string",
  "total_years_experience": "number (decimal ok, e.g. 2.5) — calculate by summing all work experience durations. If end date is missing assume present ({current_year}). Be accurate.",
  "career_level": "one of: fresher / junior / mid / senior / lead / manager / director",
  "work_experiences": [
    {{
      "title": "job title",
      "company": "company name",
      "start": "month year or year",
      "end": "month year or year or Present",
      "duration_months": "integer — calculate this accurately",
      "domain": "industry domain e.g. FinTech, E-commerce, IT Services, etc."
    }}
  ],
  "technical_skills": ["list of technical skills, tools, technologies mentioned"],
  "soft_skills": ["list of soft skills mentioned"],
  "education": [
    {{
      "degree": "e.g. B.Tech, MBA, M.Sc",
      "field": "e.g. Computer Science, MBA Finance",
      "institution": "college or university name",
      "year": "graduation year as integer or null"
    }}
  ],
  "certifications": ["list of certifications"],
  "current_location": "city name or null",
  "industry_domain": "primary industry/domain of the candidate",
  "languages": ["list of languages known"]
}}

Important rules:
- For total_years_experience: carefully read all job entries, calculate duration of each, sum them up. Do NOT just look for a "X years experience" line — compute it from dates.
- For career_level: base it on total experience and titles. 0-1 yr = fresher, 1-3 = junior, 3-6 = mid, 6-10 = senior, 10+ = lead/manager/director.
- Return ONLY the JSON, no explanation, no markdown.

Resume text:
{resume_text}
"""


def _parse_with_llm(text: str, api_key: str, current_year: int) -> Dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    prompt = _LLM_PROMPT.format(
        resume_text=text[:12000],  # stay within token limits
        current_year=current_year,
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    return json.loads(raw)


# ──────────────────────────────────────────────
#  Regex fallback (when no API key)
# ──────────────────────────────────────────────

_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.I)
_CITY_RE = re.compile(
    r"\b(Bangalore|Bengaluru|Mumbai|Delhi|Gurgaon|Gurugram|Noida|Hyderabad|"
    r"Chennai|Pune|Kolkata|Ahmedabad|Jaipur|Chandigarh|Zirakpur|Mohali|Remote)\b",
    re.I,
)
_SKILL_KEYWORDS = [
    "Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C\\+\\+", "C#",
    "React", "Angular", "Vue", "Node.js", "Django", "Flask", "FastAPI",
    "PyTorch", "TensorFlow", "Scikit-learn", "XGBoost", "LightGBM",
    "LLM", "GenAI", "Generative AI", "RAG", "Vector DB", "LangChain",
    "OpenAI", "Hugging Face", "Transformers", "BERT", "GPT",
    "SQL", "MySQL", "PostgreSQL", "MongoDB", "Redis", "Elasticsearch",
    "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Git",
    "Pandas", "NumPy", "Spark", "Kafka", "Airflow",
    "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
    "Data Science", "Data Engineering", "Excel", "Power BI", "Tableau",
    "Supply Chain", "Inventory Management", "SAP", "ERP", "Merchandising",
]
_SKILL_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(s) for s in _SKILL_KEYWORDS) + r")\b", re.I
)
_DEGREE_RE = re.compile(
    r"\b(B\.?Tech|B\.?E\.?|M\.?Tech|M\.?E\.?|MBA|BCA|MCA|B\.?Sc|M\.?Sc|"
    r"Bachelor|Master|Ph\.?D|Diploma)\b",
    re.I,
)
_JOB_TITLE_RE = re.compile(
    r"\b(Engineer|Developer|Scientist|Analyst|Manager|Designer|Architect|"
    r"Consultant|Lead|Head|Director|VP|Intern|Associate|Senior|Junior|"
    r"Full.?Stack|DevOps|ML|AI|Data|Product|Software|Mobile|Planner|"
    r"Buyer|Merchandiser|Coordinator|Executive|Officer)\b",
    re.I,
)


def _regex_fallback(text: str) -> Dict[str, Any]:
    """Basic extraction when LLM is unavailable."""
    skills = sorted({m.group(0).strip() for m in _SKILL_PATTERN.finditer(text)})

    years_match = re.search(r"(\d+)\+?\s*years?\s*(of\s*)?(experience|exp)", text, re.I)
    years = int(years_match.group(1)) if years_match else 0
    if not years:
        year_nums = {int(y) for y in _YEAR_RE.findall(text) if 2000 <= int(y) <= 2030}
        years = max(0, max(year_nums) - min(year_nums)) if year_nums else 0

    city_m = _CITY_RE.search(text)
    location = city_m.group(0).strip() if city_m else None

    degree_m = _DEGREE_RE.search(text)
    education = [{"degree": degree_m.group(0).strip(), "field": None, "institution": None, "year": None}] if degree_m else []

    email_m = _EMAIL_RE.search(text)

    title = "Unknown"
    for line in [ln.strip() for ln in text.splitlines() if ln.strip()][:30]:
        if _JOB_TITLE_RE.search(line) and len(line) < 80 and "@" not in line:
            title = line
            break

    return {
        "full_name": None,
        "email": email_m.group(0) if email_m else None,
        "current_job_title": title,
        "total_years_experience": float(years),
        "career_level": _infer_career_level(title, years),
        "work_experiences": [],
        "technical_skills": skills,
        "soft_skills": [],
        "education": education,
        "certifications": [],
        "current_location": location,
        "industry_domain": None,
        "languages": [],
    }


def _infer_career_level(title: str, years: float) -> str:
    t = title.lower()
    if "director" in t or "vp" in t:
        return "director"
    if "head" in t or "lead" in t:
        return "lead"
    if "manager" in t:
        return "manager"
    if "senior" in t or "sr" in t:
        return "senior"
    if years >= 10:
        return "lead"
    if years >= 6:
        return "senior"
    if years >= 3:
        return "mid"
    if years >= 1:
        return "junior"
    return "fresher"


# ──────────────────────────────────────────────
#  Public API
# ──────────────────────────────────────────────

def parse_resume(resume_path: str, openai_api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Parse a resume and return a structured profile dict.
    Uses LLM if api_key provided, otherwise falls back to regex.
    """
    import datetime
    logger.info("Parsing resume: %s", resume_path)
    text = extract_text(resume_path)

    if not text or len(text.strip()) < 50:
        raise ValueError("Resume appears empty or could not be parsed.")

    if openai_api_key:
        logger.info("Extracting profile using LLM …")
        try:
            profile = _parse_with_llm(text, openai_api_key, datetime.date.today().year)
            profile["_extraction_method"] = "llm"
            logger.info(
                "LLM parsed: title=%s | exp=%.1f yrs | skills=%d",
                profile.get("current_job_title"),
                profile.get("total_years_experience") or 0,
                len(profile.get("technical_skills") or []),
            )
            return profile
        except Exception as exc:
            logger.warning("LLM extraction failed (%s), falling back to regex", exc)

    logger.info("Extracting profile using regex fallback …")
    profile = _regex_fallback(text)
    profile["_extraction_method"] = "regex"
    return profile
