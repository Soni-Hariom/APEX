import os
import json
import csv
import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

def get_google_sheets_service(gdrive_config):
    creds = None
    token_path = gdrive_config.get("oauth_token_path", "config/token.json")
    creds_path = gdrive_config.get("oauth_credentials_path", "config/credentials.json")
    scopes = gdrive_config.get("scopes", ["https://www.googleapis.com/auth/spreadsheets"])
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif os.path.exists(creds_path):
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, scopes)
            creds = flow.run_local_server(port=0)
            with open(token_path, "w", encoding="utf-8") as token:
                token.write(creds.to_json())
        else:
            return None
            
    return build("sheets", "v4", credentials=creds)

def write_to_google_sheet(service, sheet_id, rows_to_write):
    range_name = "DAILY_TRACKER!A:Z"
    value_input_option = "USER_ENTERED"
    
    body = {
        "values": rows_to_write
    }
    
    result = service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=range_name,
        valueInputOption=value_input_option,
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()
    
    # Extract updated range row number
    updated_range = result.get("updates", {}).get("updatedRange", "")
    # Format e.g., 'DAILY_TRACKER!A10:Z12'
    row_num = 1
    match = re.search(r":Z(\d+)", updated_range)
    if match:
        row_num = int(match.group(1))
    return row_num

def run_sync(configs, scored_records):
    gdrive_config = configs["gdrive_config"]
    sync_manifest = configs["sync_manifest"]
    sheet_id = gdrive_config.get("spreadsheet_id", "")
    
    is_mock = sheet_id == "YOUR_GOOGLE_SHEET_ID_HERE" or not sheet_id
    
    # Load manifest state
    written_ids = set(sync_manifest.get("written_job_ids", []))
    
    today_str = datetime.date.today().isoformat()
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    
    # Filter out records already in manifest (G-02)
    records_to_sync = []
    for r in scored_records:
        jid = r["job_id"]
        if jid not in written_ids:
            records_to_sync.append(r)
            
    if not records_to_sync:
        print("[APEX::PHASE_6] No new jobs to sync (all filtered by deduplication).")
        return scored_records
        
    # Prepare row data
    rows = []
    for r in records_to_sync:
        row = [
            today_str,
            r["job_id"],
            r["match_score"],
            r["tier"],
            r["title"],
            r["company"],
            r["location"],
            r["work_mode"],
            r.get("salary_min", ""),
            r.get("salary_max", ""),
            r.get("salary_currency", ""),
            r.get("date_posted", ""),
            r["sort_jd"],
            "|".join(r.get("extracted_skills", [])),
            "|".join(r.get("must_have_skills", [])),
            r["apply_url"],
            r.get("contact_person", ""),
            r.get("work_mode", "direct"), # apply route fallback
            r.get("cold_outreach_rec", False),
            "Startup" if "inc" in r["company"].lower() else "MNC", # Stage fallback
            4.0, # Rating fallback
            f"Apply via {r.get('source_platform')} for {r.get('title')}", # Strategy
            r.get("resume_tailoring_file", ""),
            "NOT_APPLIED",
            "",
            r.get("source_platform", "")
        ]
        rows.append(row)
        
    last_row = sync_manifest.get("last_row_written", 1)
    
    service = None
    if not is_mock:
        try:
            service = get_google_sheets_service(gdrive_config)
        except Exception as e:
            print(f"  Warning: Failed to connect to Google Sheets: {e}. Falling back to CSV.")
            
    if service is not None:
        print(f"[APEX::PHASE_6][{timestamp}] Appending {len(rows)} records to Google Sheet: {sheet_id}...")
        try:
            last_row = write_to_google_sheet(service, sheet_id, rows)
            print(f"  [SUCCESS] Written successfully to Sheet. Last row: {last_row}")
        except Exception as e:
            print(f"  [ERROR] Google Sheets API write failed: {e}. Writing to mock CSV instead.")
            service = None
            
    if service is None:
        csv_path = "gdrive_sync/mock_sheet.csv"
        print(f"[APEX::PHASE_6][{timestamp}] Offline/Mock Sync Mode: Appending {len(rows)} rows to local CSV '{csv_path}'...")
        
        file_exists = os.path.exists(csv_path)
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                # write header
                writer.writerow([
                    "Date", "Job_ID", "Match_Score", "Tier", "Role_Title", "Company", "Location", 
                    "Work_Mode", "Salary_Min", "Salary_Max", "Currency", "Date_Posted", "Sort_JD", 
                    "Key_Skills", "Must_Have_Skills", "Apply_URL", "Contact_Person", "Apply_Route", 
                    "Cold_Outreach_Rec", "Company_Stage", "Company_Rating", "Strategy_Summary", 
                    "Resume_Tailoring_File", "Application_Status", "Notes", "Source_Platform"
                ])
            writer.writerows(rows)
            
        # calculate row length
        with open(csv_path, "r", encoding="utf-8") as f:
            last_row = len(f.readlines())
            
    # Update manifest state
    new_written_ids = list(written_ids.union([r["job_id"] for r in records_to_sync]))
    
    sync_manifest["last_run_date"] = today_str
    sync_manifest["last_write_timestamp"] = timestamp
    sync_manifest["total_jobs_written"] = sync_manifest.get("total_jobs_written", 0) + len(records_to_sync)
    sync_manifest["written_job_ids"] = new_written_ids[-500:] # rolling window cap 500 records
    sync_manifest["last_row_written"] = last_row
    
    with open("gdrive_sync/sync_manifest.json", "w", encoding="utf-8") as f:
        json.dump(sync_manifest, f, indent=2)
        
    with open("logs/execution_trace.log", "a", encoding="utf-8") as f:
        f.write(f"[APEX::WRITE][{timestamp}] Wrote {len(records_to_sync)} job records. Total lifetime count: {sync_manifest['total_jobs_written']}\n")
        
    print(f"[APEX::PHASE_6][{timestamp}] Sheet sync complete. sync_manifest updated [OK]")
    return scored_records

if __name__ == "__main__":
    from src.initialize import initialize_pipeline
    from src.scraper import run_scraping
    from src.normalizer import run_normalization
    from src.scorer import run_scoring
    from src.synthesizer import run_synthesis
    configs = initialize_pipeline(force_run=True)
    raw = run_scraping(configs)
    norm = run_normalization(configs, raw)
    scored = run_scoring(configs, norm)
    synthed = run_synthesis(configs, scored)
    run_sync(configs, synthed)
