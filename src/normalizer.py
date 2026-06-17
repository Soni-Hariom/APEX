import os
import json
import datetime
import re
import hashlib

def load_blocklist():
    blocklist = set()
    path = "master_data/company_blocklist.txt"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                comp = line.strip().lower()
                if comp:
                    blocklist.add(comp)
    return blocklist

def load_preferred_companies():
    preferred = set()
    path = "master_data/preferred_companies.txt"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                comp = line.strip().lower()
                if comp:
                    preferred.add(comp)
    return preferred

def parse_salary(salary_raw):
    """
    Parses salary strings like '₹12-18 LPA' or '$140k-$175k' into standard units.
    """
    if not salary_raw:
        return None, None, None
        
    s = salary_raw.lower().replace(",", "")
    
    # Heuristics for currency
    currency = None
    if "$" in s or "usd" in s:
        currency = "USD"
    elif "₹" in s or "inr" in s or "lpa" in s:
        currency = "INR"
    elif "£" in s or "gbp" in s:
        currency = "GBP"
    elif "€" in s or "eur" in s:
        currency = "EUR"
        
    # Extract numeric ranges
    numbers = re.findall(r"\d+", s)
    if not numbers:
        return None, None, currency
        
    nums = [int(n) for n in numbers]
    
    # Scale multipliers
    multiplier = 1
    if "lpa" in s or "lakh" in s:
        multiplier = 100000
    elif "k" in s:
        multiplier = 1000
        
    if len(nums) >= 2:
        val_min = nums[0] * multiplier
        val_max = nums[1] * multiplier
    else:
        val_min = nums[0] * multiplier
        val_max = val_min
        
    return val_min, val_max, currency

def extract_skills(jd_text, taxonomy):
    extracted = set()
    jd_clean = jd_text.lower()
    
    for canonical, aliases in taxonomy.items():
        for alias in aliases:
            # Match word boundaries to prevent substring matching issues (e.g. 'git' in 'digital')
            pattern = rf"\b{re.escape(alias.lower())}\b"
            if re.search(pattern, jd_clean):
                extracted.add(canonical)
                break
                
    return sorted(list(extracted))

def truncate_jd_summary(jd_text):
    """
    Returns a factual summary of <= 120 words. (Guardrail G-06)
    """
    # Simple extraction of first 3 sentences
    sentences = re.split(r"(?<=[.!?])\s+", jd_text)
    summary_candidate = " ".join(sentences[:3])
    
    words = summary_candidate.split()
    if len(words) > 120:
        truncated = " ".join(words[:119]) + "..."
        return truncated
    return summary_candidate

def run_normalization(configs, raw_records):
    taxonomy = configs["skills_taxonomy"]
    sync_manifest = configs["sync_manifest"]
    
    blocklist = load_blocklist()
    preferred = load_preferred_companies()
    written_ids = set(sync_manifest.get("written_job_ids", []))
    
    normalized_records = []
    
    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    
    for raw in raw_records:
        job_id = raw.get("job_id")
        if not job_id:
            # fallback
            job_id = hashlib.sha256(raw["apply_url"].encode("utf-8")).hexdigest()
            
        company = raw.get("company", "").strip()
        title = raw.get("title", "").strip()
        
        # 1. Deduplication (G-02)
        if job_id in written_ids:
            with open("logs/dedup_log.log", "a", encoding="utf-8") as f:
                f.write(f"[APEX::DEDUP][{timestamp}] Rejected duplicate job_id: {job_id} ({title} @ {company})\n")
            continue
            
        # 2. Blocklist check (G-03)
        if company.lower() in blocklist:
            with open("logs/execution_trace.log", "a", encoding="utf-8") as f:
                f.write(f"[APEX::NORMALIZE][{timestamp}] Discarded blocklisted company: {company} (Job ID: {job_id})\n")
            continue
            
        # 3. Salary Normalization
        sal_min, sal_max, currency = parse_salary(raw.get("salary_raw", ""))
        
        # 4. Skill Extraction
        jd_text = raw.get("jd_full_text", "")
        extracted_sk = extract_skills(jd_text, taxonomy)
        
        # 5. Must-have/Nice-to-have heuristic (from JD text)
        must_have = []
        nice_have = []
        
        # Heuristic: split JD into requirements vs nice to have section
        jd_lower = jd_text.lower()
        req_index = jd_lower.find("requirements:") if "requirements:" in jd_lower else jd_lower.find("must have:")
        nice_index = jd_lower.find("nice to have:") if "nice to have:" in jd_lower else jd_lower.find("preferred:")
        
        # If no explicit indices, we put top proficiency skills in must_have, rest in nice_to_have
        if req_index != -1:
            req_text = jd_text[req_index:nice_index] if nice_index != -1 and nice_index > req_index else jd_text[req_index:]
            must_have = extract_skills(req_text, taxonomy)
            
        if nice_index != -1:
            nice_text = jd_text[nice_index:]
            nice_have = extract_skills(nice_text, taxonomy)
            
        # Fallback if parsing didn't separate them
        if not must_have:
            must_have = extracted_sk[:3]
            nice_have = extracted_sk[3:]
        else:
            # Ensure must_have matches are in overall extracted skills list
            for s in must_have:
                if s not in extracted_sk:
                    extracted_sk.append(s)
                    
        # 6. JD Summarization (G-06)
        sort_jd = truncate_jd_summary(jd_text)
        
        # 7. Preferred Company Flag
        is_priority = company.lower() in preferred
        
        norm_record = {
            "job_id": job_id,
            "title": title,
            "company": company,
            "location": raw.get("location", ""),
            "work_mode": raw.get("work_mode", "unknown"),
            "salary_min": sal_min,
            "salary_max": sal_max,
            "salary_currency": currency,
            "date_posted": raw.get("date_posted", ""),
            "apply_url": raw.get("apply_url", ""),
            "sort_jd": sort_jd,
            "extracted_skills": extracted_sk,
            "must_have_skills": must_have,
            "nice_to_have_skills": nice_have,
            "source_platform": raw.get("source_platform", "unknown"),
            "is_priority_company": is_priority,
            "blocklisted": False
        }
        
        normalized_records.append(norm_record)
        
    # Write normalized output file
    today_str = datetime.date.today().isoformat()
    norm_path = f"scraped_data/normalized/{today_str}_norm.json"
    os.makedirs("scraped_data/normalized", exist_ok=True)
    
    with open(norm_path, "w", encoding="utf-8") as f:
        json.dump(normalized_records, f, indent=2)
        
    with open("logs/execution_trace.log", "a", encoding="utf-8") as f:
        f.write(f"[APEX::NORMALIZE][{timestamp}] Normalization finished. Output: {len(normalized_records)} records -> {norm_path}\n")
        
    print(f"[APEX::PHASE_3][{timestamp}] Normalization complete. Cleaned payload written to '{norm_path}' [OK]")
    return normalized_records

if __name__ == "__main__":
    from src.initialize import initialize_pipeline
    from src.scraper import run_scraping
    configs = initialize_pipeline(force_run=True)
    raw = run_scraping(configs)
    run_normalization(configs, raw)
