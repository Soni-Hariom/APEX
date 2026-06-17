import os
import json
import datetime
import sys

def log_error(msg):
    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    with open("logs/error_log.log", "a", encoding="utf-8") as f:
        f.write(f"[APEX::INTERRUPT][{timestamp}] {msg}\n")
    print(f"[APEX::INTERRUPT][{timestamp}] DATA_GAP DETECTED")
    print(f"  Error Detail     : {msg}")
    print(f"  Pipeline status  : HALTED at Phase 1 — review required.")

def check_weights(scoring_weights):
    weights = [
        scoring_weights.get("skills_match", 0),
        scoring_weights.get("role_title_alignment", 0),
        scoring_weights.get("location_fit", 0),
        scoring_weights.get("salary_overlap", 0),
        scoring_weights.get("experience_fit", 0),
        scoring_weights.get("company_type_pref", 0)
    ]
    weight_sum = sum(weights)
    if abs(weight_sum - 1.00) > 1e-9:
        log_error(f"Scoring weights in config/scoring_weights.json sum to {weight_sum}, must sum to exactly 1.00 (Guardrail G-05 violation).")
        return False
    return True

def initialize_pipeline(force_run=False):
    base_dir = "."
    configs = {}
    
    # Files to load
    config_files = {
        "user_profile": "config/user_profile.json",
        "search_parameters": "config/search_parameters.json",
        "apify_config": "config/apify_config.json",
        "gdrive_config": "config/gdrive_config.json",
        "scoring_weights": "config/scoring_weights.json",
        "sync_manifest": "gdrive_sync/sync_manifest.json",
        "skills_taxonomy": "master_data/skills_taxonomy.json"
    }
    
    # Load each file
    for key, path in config_files.items():
        if not os.path.exists(path):
            log_error(f"Missing configuration file: {path}. Required for initialization.")
            sys.exit(1)
        try:
            with open(path, "r", encoding="utf-8") as f:
                configs[key] = json.load(f)
        except Exception as e:
            log_error(f"Malformed JSON in file: {path}. Details: {e}")
            sys.exit(1)

    # Load resume master (text file)
    resume_path = "master_data/resume_master.md"
    if not os.path.exists(resume_path):
        log_error(f"Missing resume master file: {resume_path}. Required for initialization.")
        sys.exit(1)
    try:
        with open(resume_path, "r", encoding="utf-8") as f:
            configs["resume_master"] = f.read()
    except Exception as e:
        log_error(f"Failed to read resume master: {resume_path}. Details: {e}")
        sys.exit(1)
            
    # Validate weights (G-05)
    if not check_weights(configs["scoring_weights"]):
        sys.exit(1)
        
    # Check date execution block
    today_str = datetime.date.today().isoformat()
    last_run = configs["sync_manifest"].get("last_run_date", "")
    
    if last_run == today_str and not force_run:
        timestamp = datetime.datetime.utcnow().isoformat() + "Z"
        # Log and halt
        with open("logs/execution_trace.log", "a", encoding="utf-8") as f:
            f.write(f"[APEX::INIT][{timestamp}] Pipeline skipped: already executed today ({today_str}).\n")
        print(f"[APEX::PHASE_1][{timestamp}] Today's run status: SKIP — already executed today ({today_str}).")
        sys.exit(0)
        
    return configs

if __name__ == "__main__":
    configs = initialize_pipeline(force_run=True)
    print("[APEX::PHASE_1] Initialization check passed successfully.")
