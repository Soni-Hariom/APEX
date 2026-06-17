import os
import json
import datetime

def print_onboarding_form():
    form = """
╔══════════════════════════════════════════════════════╗
║          APEX ONBOARDING — CAREER PROFILE INTAKE     ║
╠══════════════════════════════════════════════════════╣
║  Answer each field. Leave blank if not applicable.   ║
╠══════════════════════════════════════════════════════╣
║  [1] TARGET ROLES       (e.g., "Data Scientist, ML Engineer") ║
║  [2] LOCATION PREFERENCE                                       ║
║      → India / Outside India / Both                           ║
║      → Cities (if specific): ___                              ║
║  [3] WORK MODE          Remote / Hybrid / On-site / Any       ║
║  [4] SALARY EXPECTATION                                        ║
║      → Min (₹/yr or $/yr): ___  |  Max: ___                  ║
║  [5] EXPERIENCE LEVEL   Fresher / 1-3 yrs / 3-7 yrs / 7+     ║
║  [6] KEY SKILLS         (comma-separated list)                ║
║  [7] PREFERRED COMPANY TYPE                                    ║
║      Startup / MNC / Product / Service / Any                  ║
║  [8] INDUSTRIES TO TARGET (e.g., Fintech, HealthTech)         ║
║  [9] COMPANIES TO AVOID  (comma-separated or "None")          ║
║  [10] PRIORITY COMPANIES (dream companies, if any)            ║
║  [11] RESUME FILE PATH  (or paste resume text below)          ║
║  [12] DAILY RUN TIME    (e.g., "09:00 IST" for auto-schedule) ║
╚══════════════════════════════════════════════════════╝
"""
    print(form)

def get_input(prompt_text, default=None):
    prompt_str = f"{prompt_text} [{default}]: " if default is not None else f"{prompt_text}: "
    val = input(prompt_str).strip()
    if not val:
        return default
    return val

def run_onboarding():
    print_onboarding_form()
    
    # [1] Target Roles
    roles_raw = get_input("[1] Target Roles (comma separated)", "Machine Learning Engineer, Data Scientist")
    target_roles = [r.strip() for r in roles_raw.split(",") if r.strip()]
    
    # [2] Location Preference
    loc_pref = get_input("[2] Location Preference (India / Outside India / Both)", "Both").lower()
    if "india" in loc_pref and "outside" not in loc_pref:
        location_preference = "india_only"
    elif "outside" in loc_pref:
        location_preference = "global"
    else:
        location_preference = "both"
        
    cities_raw = get_input("    Cities (comma separated, if specific)", "Bengaluru, Hyderabad, San Francisco")
    target_cities = [c.strip() for c in cities_raw.split(",") if c.strip()]
    
    # [3] Work Mode
    work_mode_raw = get_input("[3] Work Mode (Remote / Hybrid / On-site / Any)", "Any").lower()
    if "remote" in work_mode_raw:
        work_mode_preference = "remote"
    elif "hybrid" in work_mode_raw:
        work_mode_preference = "hybrid"
    elif "site" in work_mode_raw:
        work_mode_preference = "onsite"
    else:
        work_mode_preference = "any"
        
    # [4] Salary Expectation
    salary_min_raw = get_input("[4] Salary Expectation - Min (INR or USD annual, e.g. 2500000 or 120000)", "2500000")
    salary_max_raw = get_input("[4] Salary Expectation - Max (INR or USD annual, e.g. 4500000 or 180000)", "4500000")
    
    try:
        sal_min = int(salary_min_raw)
    except:
        sal_min = 0
    try:
        sal_max = int(salary_max_raw)
    except:
        sal_max = 0
        
    # Detect currency based on size/input (simple heuristic for placeholder config representation)
    is_usd = sal_min < 1000000
    salary_min_inr = None if is_usd else sal_min
    salary_max_inr = None if is_usd else sal_max
    salary_min_usd = sal_min if is_usd else None
    salary_max_usd = sal_max if is_usd else None

    # [5] Experience Level
    exp_level = get_input("[5] Experience Level (Fresher / 1-3 yrs / 3-7 yrs / 7+)", "3-7 yrs")
    exp_map = {
        "fresher": 0.0,
        "1-3 yrs": 2.0,
        "3-7 yrs": 5.0,
        "7+": 8.0
    }
    total_experience_yrs = exp_map.get(exp_level.lower(), 4.5)
    
    # [6] Key Skills
    skills_raw = get_input("[6] Key Skills (comma separated)", "Python, PyTorch, SQL, Docker, FastAPI")
    skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
    
    # [7] Preferred Company Type
    comp_type = get_input("[7] Preferred Company Type (Startup / MNC / Product / Service / Any)", "Startup").lower()
    if "startup" in comp_type:
        preferred_company_type = "startup"
    elif "mnc" in comp_type:
        preferred_company_type = "mnc"
    elif "product" in comp_type:
        preferred_company_type = "product"
    elif "service" in comp_type:
        preferred_company_type = "service"
    else:
        preferred_company_type = "any"
        
    # [8] Industries
    ind_raw = get_input("[8] Industries to Target (comma separated)", "Fintech, HealthTech, SaaS")
    target_industries = [i.strip() for i in ind_raw.split(",") if i.strip()]
    
    # [9] Companies to Avoid
    avoid_raw = get_input("[9] Companies to Avoid (comma separated or None)", "None")
    avoid_companies = [c.strip() for c in avoid_raw.split(",") if c.strip() and c.strip().lower() != "none"]
    
    # [10] Priority Companies
    priority_raw = get_input("[10] Priority Companies (comma separated or None)", "Google, OpenAI, Anthropic")
    priority_companies = [c.strip() for c in priority_raw.split(",") if c.strip() and c.strip().lower() != "none"]
    
    # [11] Resume
    resume_path = get_input("[11] Resume File Path or type 'PASTE' to paste text", "master_data/resume_master.md")
    resume_content = ""
    if resume_path.upper() == "PASTE":
        print("Paste your resume content below. Press Ctrl+D (Linux/macOS) or Ctrl+Z (Windows) then Enter when finished:")
        import sys
        resume_content = sys.stdin.read().strip()
    elif os.path.exists(resume_path):
        with open(resume_path, "r", encoding="utf-8") as f:
            resume_content = f.read().strip()
    else:
        print(f"Warning: File not found at '{resume_path}'. Initializing with default resume template.")
        # Load from master if exists, otherwise placeholder
        master_path = "master_data/resume_master.md"
        if os.path.exists(master_path):
            with open(master_path, "r", encoding="utf-8") as f:
                resume_content = f.read().strip()
        else:
            resume_content = "# Jane Doe\nResume details..."
            
    # [12] Daily Run Time
    daily_time = get_input("[12] Daily Run Time (e.g. 09:00 IST)", "09:00 IST")
    
    # Save user_profile.json
    profile = {
        "candidate_name": "Jane Doe", # Default for mock
        "target_roles": target_roles,
        "total_experience_yrs": total_experience_yrs,
        "current_location": "Bengaluru, India" if location_preference == "india_only" or location_preference == "both" else "San Francisco, USA",
        "location_preference": location_preference,
        "target_cities": target_cities,
        "work_mode_preference": work_mode_preference,
        "salary_min_inr": salary_min_inr,
        "salary_max_inr": salary_max_inr,
        "salary_min_usd": salary_min_usd,
        "salary_max_usd": salary_max_usd,
        "skills": skills,
        "preferred_company_type": preferred_company_type,
        "target_industries": target_industries,
        "notice_period_days": 30,
        "profile_created_at": datetime.datetime.utcnow().isoformat() + "Z",
        "profile_updated_at": datetime.datetime.utcnow().isoformat() + "Z"
    }
    
    # Save search_parameters.json
    search_params = {
        "target_roles": target_roles,
        "locations": target_cities if target_cities else ["India"],
        "work_modes": [work_mode_preference] if work_mode_preference != "any" else ["remote", "hybrid", "onsite"],
        "results_limit_per_vector": 50,
        "date_posted_filter": "last24hours"
    }
    
    os.makedirs("config", exist_ok=True)
    os.makedirs("master_data", exist_ok=True)
    
    with open("config/user_profile.json", "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)
        
    with open("config/search_parameters.json", "w", encoding="utf-8") as f:
        json.dump(search_params, f, indent=2)
        
    with open("master_data/resume_master.md", "w", encoding="utf-8") as f:
        f.write(resume_content)
        
    with open("master_data/company_blocklist.txt", "w", encoding="utf-8") as f:
        for c in avoid_companies:
            f.write(c + "\n")
            
    with open("master_data/preferred_companies.txt", "w", encoding="utf-8") as f:
        for c in priority_companies:
            f.write(c + "\n")
            
    # Output onboarding confirmation
    print("\n[APEX::SESSION_0] Profile construction complete.")
    print("  → user_profile.json      [OK] WRITTEN")
    print("  → search_parameters.json [OK] WRITTEN")
    print("  → resume_master.md       [OK] WRITTEN")
    print("[APEX::SESSION_0] First pipeline run initiating in 3s...")

if __name__ == "__main__":
    run_onboarding()
