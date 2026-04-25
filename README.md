# Daily Job Matcher — India Edition 🎯

AI-powered job search automation for Indian job seekers.  
Parses your resume → searches 40 000+ Indian job sources → sends a daily HTML digest.

---

## How It Works

```
Your Resume (PDF/DOCX)
       ↓
Resume Parser  →  Extracts: title, skills, location, experience
       ↓
Preference Setup  →  Confirms search criteria interactively
       ↓
Every day at 8 AM IST (GitHub Actions)
       ↓
Adzuna API  →  Fetches 50-100 fresh Indian jobs
       ↓
AI Matching  →  GPT or keyword scoring for each job
       ↓
Filter & Rank  →  Top 5-8 jobs above 70% match
       ↓
Gmail SMTP  →  Beautiful HTML digest lands in your inbox
```

---

## Web UI (Recommended)

Run the full-stack web app with two commands:

```bash
# Terminal 1 — Backend (FastAPI)
source venv/bin/activate
uvicorn backend.main_api:app --reload

# Terminal 2 — Frontend (React + Vite)
cd frontend
npm install      # first time only
npm run dev
```

Then open **http://localhost:5173** in your browser.

### What you can do in the UI
1. **Create a profile** — give it a name (e.g. `shubham_ml`)
2. **Setup** — upload your resume, verify extracted details, set preferences + recipient email
3. **Dashboard** — click "Fetch & Match Jobs", select the ones you like, click "Send to Email"

---

## CLI (Alternative)

You can also use the original command-line interface:

```bash
source venv/bin/activate

python main.py --create-profile shubham_ml
python main.py --setup --profile shubham_ml
python main.py --dry-run --profile shubham_ml
python main.py --profile shubham_ml
```

---

## Quick Start (15 minutes)

### Step 1 — Get API Keys

| Service | Cost | URL |
|---------|------|-----|
| **Adzuna API** | Free | https://developer.adzuna.com/ |
| **OpenAI** | Optional (pay-per-use) | https://platform.openai.com/api-keys |
| **Gmail App Password** | Free | Google Account → Security → App Passwords |

### Step 2 — Clone & Configure

```bash
git clone https://github.com/YOUR_USERNAME/daily-job-matcher.git
cd daily-job-matcher

# Copy example env and fill in your credentials
cp .env.example .env
nano .env          # or code .env / open in any editor
```

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Step 4 — Place Your Resume

Copy your resume (PDF or DOCX) to:
```
data/user_resume.pdf       # or .docx
```

### Step 5 — First-Time Setup

```bash
python main.py --setup
```

This will:
- Parse your resume automatically
- Show you what was extracted
- Ask you to confirm / update preferences
- Save everything locally

### Step 6 — Test Run

```bash
# Dry run — see matched jobs without sending email
python main.py --dry-run

# Test email — send a sample digest to verify SMTP
python main.py --test-email

# Full run
python main.py
```

### Step 7 — Enable Daily Automation (GitHub Actions)

1. Push the repo to GitHub (private recommended)
2. Go to **Settings → Secrets and variables → Actions**
3. Add each variable from `.env.example` as a **Repository Secret**
4. The workflow in `.github/workflows/daily_job_search.yml` runs automatically  
   every weekday at **8:00 AM IST**

To trigger manually: **Actions → Daily Job Search → Run workflow**

---

## Commands

### Default (single profile)

| Command | Description |
|---------|-------------|
| `python main.py` | Run full job search + send email |
| `python main.py --setup` | First-time setup (parse resume, set preferences) |
| `python main.py --update-prefs` | Update job search preferences |
| `python main.py --dry-run` | Run without sending email (safe test) |
| `python main.py --test-email` | Send a test email to verify SMTP |

### Multiple Profiles

Use profiles when you have **multiple resumes**, **different job targets**, or want to send results to **different email addresses**.

| Command | Description |
|---------|-------------|
| `python main.py --list-profiles` | Show all saved profiles and their status |
| `python main.py --create-profile <name>` | Create a new profile folder |
| `python main.py --setup --profile <name>` | Set up a specific profile |
| `python main.py --update-prefs --profile <name>` | Update preferences for a profile |
| `python main.py --dry-run --profile <name>` | Dry run for a specific profile |
| `python main.py --profile <name>` | Full run for a specific profile |
| `python main.py --test-email --profile <name>` | Test email for a specific profile |

#### Example: Two profiles for different job targets

```bash
# Create profiles
python main.py --create-profile retail
python main.py --create-profile supply_chain

# Copy the right resume into each profile folder
cp ~/Documents/retail_resume.pdf       profiles/retail/resume.pdf
cp ~/Documents/supply_chain_resume.pdf profiles/supply_chain/resume.pdf

# Set up each profile (parses resume + sets preferences + email)
python main.py --setup --profile retail
python main.py --setup --profile supply_chain

# Run both independently
python main.py --profile retail
python main.py --profile supply_chain
```

#### How profiles are isolated

Each profile has its own completely separate data — nothing is shared:

```
profiles/
  retail/
    resume.pdf            # Your resume for retail roles
    parsed_resume.json    # Auto-extracted from retail resume
    preferences.json      # "Buying Planner", 12 LPA, Chandigarh
    config.json           # Send FROM / TO email for this profile
    job_history.json      # Jobs already sent (won't repeat)

  supply_chain/
    resume.pdf            # Different resume
    parsed_resume.json    # Extracted from supply chain resume
    preferences.json      # "Supply Chain Analyst", 15 LPA, Mumbai
    config.json           # Different email config
    job_history.json      # Separate history
```

---

## Environment Variables

See `.env.example` for all variables with descriptions.  
Key ones:

| Variable | Required | Description |
|----------|----------|-------------|
| `ADZUNA_APP_ID` | Yes | From developer.adzuna.com |
| `ADZUNA_APP_KEY` | Yes | From developer.adzuna.com |
| `GMAIL_EMAIL` | Yes | Your Gmail address |
| `GMAIL_APP_PASSWORD` | Yes | 16-char Gmail app password |
| `RECIPIENT_EMAIL` | Yes | Where to send the digest |
| `OPENAI_API_KEY` | No | For GPT matching (optional) |
| `USE_GPT_MATCHING` | No | `true` / `false` (default `true`) |
| `SALARY_MIN_LPA` | No | Minimum salary expectation |
| `MATCH_SCORE_THRESHOLD` | No | Min score to include a job (default 70) |

---

## File Structure

```
daily-job-matcher/
├── main.py                    # CLI entry point
├── config.py                  # Environment config loader
├── profile_manager.py         # Multi-profile support
├── resume_parser.py           # PDF/DOCX → profile dict (LLM-powered)
├── profile_builder.py         # Verification + search preference builder
├── preference_extractor.py    # Load/save preferences
├── job_fetcher.py             # Adzuna API integration
├── job_matcher.py             # GPT + keyword matching
├── email_generator.py         # Gmail SMTP sender
├── email_templates.py         # HTML email builder
├── utils.py                   # Logging, JSON helpers
├── requirements.txt           # Python deps
├── backend/
│   ├── main_api.py            # FastAPI app (uvicorn entry point)
│   └── routers/
│       ├── profiles.py        # GET/POST/DELETE /api/profiles
│       ├── resume.py          # Upload + confirm resume
│       ├── jobs.py            # Fetch + match jobs
│       └── email.py           # Send digest + test email
├── frontend/
│   ├── package.json
│   ├── vite.config.js         # Proxy /api → localhost:8000
│   └── src/
│       ├── App.jsx
│       ├── api/index.js       # All API calls
│       ├── pages/
│       │   ├── ProfilesPage.jsx
│       │   ├── SetupPage.jsx  # 3-step wizard (upload→verify→prefs)
│       │   └── DashboardPage.jsx
│       └── components/
│           ├── Navbar.jsx
│           ├── JobCard.jsx
│           └── StepIndicator.jsx
├── .env.example
├── .github/
│   └── workflows/
│       └── daily_job_search.yml
├── data/                      # Default (single-profile) data
│   ├── user_resume.pdf        # Your resume (gitignored)
│   ├── parsed_resume.json     # Extracted profile
│   ├── user_preferences.json  # Your search preferences
│   └── job_history.json       # Sent job IDs (dedup)
├── profiles/                  # Named profiles (multi-profile)
│   └── <profile_name>/
│       ├── resume.pdf         # Profile-specific resume
│       ├── parsed_resume.json
│       ├── preferences.json
│       ├── config.json        # Profile email config
│       └── job_history.json
├── templates/
│   └── email_template.html
└── logs/
    └── job_matcher.log
```

---

## How Matching Works

**With GPT (recommended):** Each job is sent to `gpt-4o-mini` along with your resume
profile. GPT returns a structured JSON with match score, reasoning, and application tips.
Typical cost: ~$0.01–0.05 per run.

**Without GPT (free fallback):** Keyword overlap between your skills and the job description
drives a rule-based score. Less accurate but zero cost.

Set `USE_GPT_MATCHING=false` in `.env` to always use the free fallback.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ADZUNA_APP_ID` not found | Check `.env` file and spelling |
| Gmail authentication failed | Re-generate app password with 2FA enabled |
| Resume parsed as empty | Ensure PDF has selectable text (not scanned image) |
| No jobs found | Broaden `PREFERRED_LOCATIONS` or lower `SALARY_MIN_LPA` |
| Low match scores | Lower `MATCH_SCORE_THRESHOLD` or enable GPT matching |
| GitHub Actions not running | Check secrets are set; try manual trigger |

---

## Local Cron (alternative to GitHub Actions)

**Linux / macOS:**
```bash
crontab -e
# Add (runs at 8 AM IST = 2:30 AM UTC):
30 2 * * 1-5 cd /path/to/daily-job-matcher && python main.py >> logs/cron.log 2>&1
```

**Windows Task Scheduler:**
- Action: `python C:\path\to\main.py`
- Trigger: Daily at 8:00 AM

---

## Privacy

- Your resume and credentials **never leave your machine / GitHub private repo**
- Adzuna only receives job search queries (title, location, salary range)
- If using GPT: resume profile and job descriptions are sent to OpenAI (see their privacy policy)

---

*Daily Job Matcher v2.0 · India Edition · Built for Indian job seekers*
