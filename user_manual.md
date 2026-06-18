# APEX User Manual

Welcome to the APEX (Autonomous Placement & Execution Agent) setup and operational manual. This document guides you step-by-step through setting up your environment, adding API keys, tailoring the configurations, and executing the agent.

---

## 1. Prerequisites & Environment Setup

Ensure you have Python 3.8 or higher installed on your machine.

### Step 1: Create a Python Virtual Environment
Open your terminal (PowerShell or Git Bash on Windows) in the [APEX directory](file:///d:/Hariom/My Projects/APEX) and run:
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate virtual environment (Git Bash/Linux/macOS)
source venv/Scripts/activate
```

### Step 2: Install Required Dependencies
With the virtual environment active, install the dependencies listed in [requirements.txt](requirements.txt):
```powershell
pip install -r requirements.txt
```

---

## 2. API Setup & Authentication

APEX depends on two external tools: **Apify** (for job scraping) and **Google Drive/Sheets** (for tracking job application status).

### Configuration A: Apify API Setup
1. Go to [Apify Console](https://console.apify.com/) and register for an account.
2. Navigate to **Settings** -> **Integrations** and copy your **Personal API Token**.
3. Open [config/apify_config.json](config/apify_config.json) and replace `"YOUR_APIFY_API_TOKEN_HERE"` with your copied token.

### Configuration B: Google Sheets OAuth Setup
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project named `APEX-Job-Tracker`.
3. Enable the **Google Sheets API** and the **Google Drive API** under API Library.
4. Set up an OAuth Consent Screen (external, adding your own email as a test user).
5. Navigate to **Credentials** -> **Create Credentials** -> **OAuth Client ID**. Select application type "Desktop App" and click Create.
6. Download the credential JSON file and save it as `credentials.json` inside the [config/](config) folder:
   - File path: `d:/Hariom/My Projects/APEX/config/credentials.json`
7. Create a new Google Sheet in your Google Drive to track your applications:
   - Set up the headers for Tab 1: `DAILY_TRACKER` exactly as specified in the readme schema (Date, Job_ID, Match_Score, Tier, Role_Title, etc.).
   - Copy the Sheet ID from the URL: `https://docs.google.com/spreadsheets/d/[SPREADSHEET_ID_HERE]/edit`
8. Open [config/gdrive_config.json](config/gdrive_config.json) and replace `"YOUR_GOOGLE_SHEET_ID_HERE"` with your spreadsheet ID.

---

## 3. Customize Your Candidate Profile

Before running the agent, update the template configurations in the repository to reflect your profile:

1. **Master Profile:** Update [config/user_profile.json](config/user_profile.json) with your name, experience, preferred cities, salary ranges, notice period, and core skill keywords.
2. **Search Parameters:** Update [config/search_parameters.json](config/search_parameters.json) to set your active search terms, locations, and preferred work mode filters.
3. **Master Resume:** Replace the contents of [master_data/resume_master.md](master_data/resume_master.md) with your unedited canonical resume text.
4. **Blocklists and Dream Companies:** 
   - Add companies you wish to ignore to [master_data/company_blocklist.txt](master_data/company_blocklist.txt) (one per line).
   - Add dream target companies to [master_data/preferred_companies.txt](master_data/preferred_companies.txt) (one per line).

---

## 4. Running the Pipeline

Once configured, the APEX agent can be run using the core scripts (which we will develop in the next phases).

### Command Reference
* **Intake Form (Reset):**
  `python -m src.onboard` — Collects your details in an interactive questionnaire to build configs.
* **Daily Automation Run:**
  `python -m src.main` — Executes the complete 8-phase cognitive pipeline end-to-end.
* **Execution Telemetry:**
  - Standard process events are written to [logs/execution_trace.log](logs/execution_trace.log).
  - Errors and halts are written to [logs/error_log.log](logs/error_log.log).
  - Duplicate matches that were blocked from writing are written to [logs/dedup_log.log](logs/dedup_log.log).

### Accessing Deliverables
* Check [output/daily_report/](output/daily_report) for your daily Markdown briefing report detailing matches sorted by score.
* Go to [output/tailored_resumes/](output/tailored_resumes) to find files named `[Job_ID]_resume.md` showing how to optimize your resume bullets.
* Go to [output/outreach_scripts/](output/outreach_scripts) for customized recruiter messaging templates.
