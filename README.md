# DevOps Job Auto-Apply Pipeline

Automated daily pipeline that searches **LinkedIn** and **Naukri**, filters by your skills,
and auto-applies to matching DevOps jobs in Hyderabad. Sends **Email** and **WhatsApp** alerts.

---

## Target Profile

| Field | Value |
|-------|-------|
| **Roles** | DevOps / SRE / Cloud / Platform / DevSecOps Engineer |
| **Location** | Hyderabad, Telangana |
| **Experience** | 5+ years |
| **Skills** | AWS, Kubernetes, Docker, Terraform, Git, GitHub Actions, EKS, CI/CD, Prometheus, Grafana, Datadog, Ansible, Helm, ArgoCD, ELK, PagerDuty, CloudWatch |

---

## How It Works

```
GitHub Actions  (8:30 AM IST + 1:30 PM IST, every day)
       |
  +----+----+
  |         |
LinkedIn  Naukri
Scraper   Scraper
  |         |
  +----+----+
       |
  Job Matcher
  - Location: Hyderabad
  - Experience: 5+ yrs
  - Skill match >= 30%
       |
  Duplicate Filter (SQLite)
       |
   Auto Apply
  /         \
Email     WhatsApp
(Gmail)   (Twilio)
```

---

## Repository Structure

```
JobApply/
+-- .github/workflows/daily-job-apply.yml
+-- src/
|   +-- scrapers/
|   |   +-- linkedin.py       LinkedIn job scraper
|   |   +-- naukri.py         Naukri job scraper
|   +-- matchers/
|   |   +-- job_matcher.py    Skills / location / experience filter
|   +-- apply/
|   |   +-- linkedin_apply.py LinkedIn Easy Apply automation
|   |   +-- naukri_apply.py   Naukri Quick Apply automation
|   +-- notifications/
|   |   +-- email_notifier.py    HTML email via Gmail SMTP
|   |   +-- whatsapp_notifier.py WhatsApp via Twilio
|   +-- utils/
|       +-- db.py             SQLite applied-jobs tracker
|       +-- helpers.py        Driver factory + browser helpers
+-- config/settings.py        Config + credentials loader
+-- data/applied_jobs.db      Auto-committed after each run
+-- main.py                   Pipeline orchestrator
+-- requirements.txt
+-- .env.example
+-- README.md
```

---

## Setup Guide

### Step 1 - Add GitHub Secrets

**Settings > Secrets and variables > Actions > New repository secret**

| Secret | Description |
|--------|-------------|
| `LINKEDIN_EMAIL` | Your LinkedIn login email |
| `LINKEDIN_PASSWORD` | Your LinkedIn password |
| `NAUKRI_EMAIL` | Your Naukri login email |
| `NAUKRI_PASSWORD` | Your Naukri password |
| `GMAIL_USER` | Gmail address to send alerts FROM |
| `GMAIL_APP_PASSWORD` | Gmail App Password (16-char) - see Step 3 |
| `ALERT_EMAIL` | Email address to RECEIVE daily reports |
| `TWILIO_ACCOUNT_SID` | From Twilio Console |
| `TWILIO_AUTH_TOKEN` | From Twilio Console |
| `TWILIO_WHATSAPP_FROM` | `whatsapp:+14155238886` (Twilio sandbox) |
| `WHATSAPP_TO` | Your number e.g. `whatsapp:+919XXXXXXXXX` |

### Step 2 - Activate Twilio WhatsApp Sandbox

1. Sign up free at https://www.twilio.com/try-twilio
2. Open WhatsApp on your phone
3. Send `join <your-sandbox-keyword>` to **+1-415-523-8886**
4. You will get a confirmation message

### Step 3 - Generate Gmail App Password

1. Enable 2-Step Verification on your Google account
2. Go to https://myaccount.google.com/apppasswords
3. Create password for "Mail" and use the 16-char code as `GMAIL_APP_PASSWORD`

### Step 4 - Enable GitHub Actions

Click the **Actions** tab and enable workflows if prompted.

### Step 5 - Test Run

**Actions > Daily DevOps Job Auto-Apply > Run workflow**

---

## Schedule

| Run | IST Time | UTC Cron |
|-----|----------|----------|
| Morning | 8:30 AM | `0 3 * * *` |
| Afternoon | 1:30 PM | `0 8 * * *` |

---

## Local Development

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
export $(cat .env | xargs)
python main.py
```

---

## Important Notes

1. **LinkedIn**: Only applies to **Easy Apply** jobs (filter `f_LF=f_AL`)
2. **Naukri**: Requires an active account with an uploaded resume
3. **Rate limiting**: Random 1-8 second delays between actions to avoid detection
4. **Max applications**: 15 per platform per run (configurable in `config/settings.py`)
5. **No duplicates**: SQLite DB tracks every applied job across all runs
6. **DB persistence**: Workflow commits `data/applied_jobs.db` after each run

---

## Customise

Edit `config/settings.py` to change search behaviour:

```python
search_keywords          = ["DevOps Engineer", "SRE", ...]
target_skills            = ["AWS", "Kubernetes", ...]
min_skill_match          = 30    # lower = more jobs applied
max_applications_per_run = 15
min_experience           = 5
```
