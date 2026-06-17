import os
import json
import datetime
import re

def clean_tokens(text):
    text = text.lower()
    # Remove punctuation
    text = re.sub(r"[^\w\s]", " ", text)
    # Split into words
    words = set(text.split())
    # Remove stop words
    stop_words = {"and", "or", "the", "a", "an", "of", "to", "in", "for", "with", "at", "by", "on"}
    return words - stop_words

def calculate_jaccard_similarity(text1, text2):
    tokens1 = clean_tokens(text1)
    tokens2 = clean_tokens(text2)
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return len(intersection) / len(union)

def extract_experience_requirement(jd_text):
    """
    Extracts experience years from description text using heuristics.
    """
    jd_clean = jd_text.lower()
    # Search for patterns like '5+ years', '3-5 years', 'experience of 7 years'
    match_range = re.search(r"(\d+)\s*-\s*(\d+)\s*(?:years|yrs|year)", jd_clean)
    if match_range:
        return float(match_range.group(1)), float(match_range.group(2))
        
    match_plus = re.search(r"(\d+)\s*\+\s*(?:years|yrs|year)", jd_clean)
    if match_plus:
        val = float(match_plus.group(1))
        return val, val + 3.0 # assume range up to +3 years
        
    match_single = re.search(r"(?:experience of|require|needs)\s*(\d+)\s*(?:years|yrs|year)", jd_clean)
    if match_single:
        val = float(match_single.group(1))
        return val, val
        
    return None, None

def score_job_record(configs, record):
    weights = configs["scoring_weights"]
    profile = configs["user_profile"]
    
    # 1. Skills Match (35%)
    user_skills = set(s.lower() for s in profile.get("skills", []))
    must_have_skills = set(s.lower() for s in record.get("must_have_skills", []))
    
    if must_have_skills:
        matched = user_skills.intersection(must_have_skills)
        skills_score = (len(matched) / len(must_have_skills)) * 100.0
    else:
        # If no must-haves are defined, count intersection with extracted skills
        extracted = set(s.lower() for s in record.get("extracted_skills", []))
        if extracted:
            matched = user_skills.intersection(extracted)
            skills_score = (len(matched) / len(extracted)) * 100.0
        else:
            skills_score = 100.0 # Perfect neutral score
            
    # 2. Role Title Alignment (20%)
    title_similarities = [
        calculate_jaccard_similarity(record.get("title", ""), role)
        for role in profile.get("target_roles", [])
    ]
    role_score = max(title_similarities) * 100.0 if title_similarities else 0.0
    
    # 3. Location / Work Mode Fit (15%)
    location_score = 0.0
    job_loc = record.get("location", "").lower()
    job_mode = record.get("work_mode", "").lower()
    user_mode = profile.get("work_mode_preference", "").lower()
    
    # Mode match
    mode_match = False
    if user_mode == "any" or job_mode == user_mode:
        mode_match = True
    elif user_mode == "remote" and job_mode == "remote":
        mode_match = True
        
    # City match
    city_match = False
    target_cities = [c.lower() for c in profile.get("target_cities", [])]
    for city in target_cities:
        if city in job_loc:
            city_match = True
            break
            
    # Location Preference logic
    loc_pref = profile.get("location_preference", "both")
    pref_match = False
    is_india = "india" in job_loc or any(c in ["bengaluru", "hyderabad", "mumbai", "delhi", "chennai", "pune"] for c in job_loc.split())
    if loc_pref == "india_only" and is_india:
        pref_match = True
    elif loc_pref == "global" and not is_india:
        pref_match = True
    elif loc_pref == "both":
        pref_match = True
        
    if (city_match or job_mode == "remote") and mode_match:
        location_score = 100.0
    elif pref_match:
        location_score = 53.33 # maps to 8 points on scale of 15 (8/15 * 100)
    else:
        location_score = 0.0
        
    # 4. Salary Range Overlap (15%)
    salary_score = 50.0 # Neutral 7.5 points default if salary missing
    job_min = record.get("salary_min")
    job_max = record.get("salary_max")
    job_curr = record.get("salary_currency")
    
    user_min = profile.get("salary_min_inr")
    user_max = profile.get("salary_max_inr")
    
    # Standard USD to INR rate for comparison
    fx_rate = 83.0
    
    if job_min is not None and job_max is not None and user_min is not None and user_max is not None:
        # Normalize to INR for comparison
        j_min = job_min * fx_rate if job_curr == "USD" else job_min
        j_max = job_max * fx_rate if job_curr == "USD" else job_max
        
        # Calculate overlap
        o_min = max(user_min, j_min)
        o_max = min(user_max, j_max)
        
        if o_min <= o_max:
            overlap = o_max - o_min
            union = max(user_max, j_max) - min(user_min, j_min)
            salary_score = (overlap / union) * 100.0 if union > 0 else 100.0
        else:
            salary_score = 0.0
            
    # 5. Experience Level Fit (10%)
    exp_score = 0.0
    user_exp = profile.get("total_experience_yrs", 0.0)
    req_min, req_max = extract_experience_requirement(record.get("sort_jd", "") + " " + record.get("title", ""))
    
    if req_min is not None:
        if user_exp >= req_min:
            if req_max is None or user_exp <= req_max:
                exp_score = 100.0 # Exact fit
            else:
                exp_score = 50.0 # Overqualified
        elif abs(user_exp - req_min) <= 2.0:
            exp_score = 50.0 # Adjacent band
        else:
            exp_score = 0.0 # Outside
    else:
        exp_score = 100.0 # Neutral fit if not specified
        
    # 6. Company Type Preference (5%)
    company_score = 60.0 # Neutral (3/5 * 100)
    user_comp_pref = profile.get("preferred_company_type", "any")
    
    # For simulation, assume startup or MNC based on size / name
    job_comp = record.get("company", "").lower()
    is_startup = any(k in job_comp for k in ["inc", "innovators", "solutions", "tech", "lab", "labs"])
    
    if user_comp_pref == "any":
        company_score = 100.0
    elif user_comp_pref == "startup" and is_startup:
        company_score = 100.0
    elif user_comp_pref == "mnc" and not is_startup:
        company_score = 100.0
    else:
        company_score = 0.0
        
    # Weighted calculation
    score_composite = (
        skills_score * weights["skills_match"] +
        role_score * weights["role_title_alignment"] +
        location_score * weights["location_fit"] +
        salary_score * weights["salary_overlap"] +
        exp_score * weights["experience_fit"] +
        company_score * weights["company_type_pref"]
    )
    
    score_int = int(round(score_composite))
    
    # Classification
    if score_int >= 85:
        tier = "TIER_1: STRONG MATCH"
    elif score_int >= 70:
        tier = "TIER_2: GOOD MATCH"
    elif score_int >= 55:
        tier = "TIER_3: PARTIAL MATCH"
    elif score_int >= 40:
        tier = "TIER_4: WEAK MATCH"
    else:
        tier = "TIER_5: NO MATCH"
        
    # Recruiter / Contact person search logic
    jd_full = record.get("sort_jd", "") # search short jd or fallback
    recruiter_match = re.search(r"(?:reach out to|contact|recruiter|hiring manager:?)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)", jd_full)
    
    if recruiter_match:
        contact_person = recruiter_match.group(1)
    else:
        contact_person = f"Contact: Search '{record.get('company')} recruiter {record.get('title')}' on LinkedIn"
        
    scored_record = dict(record)
    scored_record["match_score"] = score_int
    scored_record["tier"] = tier
    scored_record["contact_person"] = contact_person
    
    return scored_record

def run_scoring(configs, normalized_records):
    scored_records = []
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    
    for norm in normalized_records:
        scored = score_job_record(configs, norm)
        # Drop Tier 5 from outputs as specified: "Score 0-39 Tier 5 silently discarded"
        if scored["match_score"] >= 40:
            scored_records = [scored] + scored_records
            
    # Sort descending by match_score
    scored_records.sort(key=lambda x: x["match_score"], reverse=True)
    
    with open("logs/execution_trace.log", "a", encoding="utf-8") as f:
        f.write(f"[APEX::SCORE][{timestamp}] Scoring complete. Survived records: {len(scored_records)} (Tiers 1-4)\n")
        
    print(f"[APEX::PHASE_4][{timestamp}] Scoring complete. {len(scored_records)} jobs kept (Tier 1-4) [OK]")
    return scored_records

if __name__ == "__main__":
    from src.initialize import initialize_pipeline
    from src.scraper import run_scraping
    from src.normalizer import run_normalization
    configs = initialize_pipeline(force_run=True)
    raw = run_scraping(configs)
    norm = run_normalization(configs, raw)
    run_scoring(configs, norm)
