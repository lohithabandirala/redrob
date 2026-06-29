from typing import Dict, Any

def extract_features(candidate: Dict[str, Any], jd_skills_set: set) -> Dict[str, float]:
    """
    Extracts numerical features used for ranking a candidate.
    """
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    careers = candidate.get("career_history", [])
    
    # 1. Hard Skills Match
    skills = candidate.get("skills", [])
    candidate_skills = {s.get("name", "").lower() for s in skills}
    overlap = len(candidate_skills.intersection(jd_skills_set))
    missing_skills = list(jd_skills_set - candidate_skills)
    hard_skills_score = min(overlap / len(jd_skills_set), 1.0) if jd_skills_set else 0.0
    
    # 2. Experience Fit (Target: 5-9 years, 7 is optimal)
    exp = profile.get("years_of_experience", 0)
    if 5 <= exp <= 9:
        exp_score = 1.0
    elif exp < 5:
        exp_score = max(0.0, 1.0 - (5 - exp) * 0.2)
    else:
        exp_score = max(0.0, 1.0 - (exp - 9) * 0.1)
        
    # --- Advanced Penalties and Traps ---
    # Consulting Trap
    it_services = {"tcs", "infosys", "wipro", "accenture", "cognizant", "capgemini"}
    company_names = [j.get("company", "").lower() for j in careers]
    if company_names and all(any(it in c for it in it_services) for c in company_names):
        exp_score *= 0.5 # Heavy penalty for pure consulting
        
    # Pure Research Trap
    industries = [j.get("industry", "").lower() for j in careers]
    if industries and all("research" in ind or "academia" in ind for ind in industries):
        exp_score *= 0.2 # Massive penalty
        
    # Title Chaser Trap
    if exp > 0 and len(careers) >= 4:
        # If they had 4+ jobs but total duration is very short (e.g., < 4 years)
        total_career_months = sum([j.get("duration_months", 0) for j in careers])
        if total_career_months < 48:
            exp_score *= 0.6
            
    # Location Bonus
    loc = profile.get("location", "").lower()
    if "pune" in loc or "noida" in loc:
        exp_score += 0.2
    elif "hyderabad" in loc or "mumbai" in loc or "delhi" in loc:
        exp_score += 0.1
    elif signals.get("willing_to_relocate", False):
        exp_score += 0.05
        
    exp_score = min(exp_score, 1.0)
        
    # 3. Behavioral Score
    response_rate = signals.get("recruiter_response_rate", 0.0)
    completeness = signals.get("profile_completeness_score", 0.0) / 100.0
    open_to_work = 1.0 if signals.get("open_to_work_flag") else 0.0
    
    # Notice period penalty
    notice_period = signals.get("notice_period_days", 90)
    notice_score = 1.0 if notice_period <= 30 else max(0.0, 1.0 - ((notice_period - 30) / 60))
    
    # New Signals
    github_score = signals.get("github_activity_score", 0) / 100.0
    github_score = max(0.0, github_score)
    interview_rate = signals.get("interview_completion_rate", 0.5)
    
    behavioral_score = (response_rate * 0.2) + (completeness * 0.1) + (open_to_work * 0.1) + (notice_score * 0.2) + (github_score * 0.2) + (interview_rate * 0.2)
    
    return {
        "hard_skills_score": hard_skills_score,
        "exp_score": exp_score,
        "behavioral_score": behavioral_score,
        "missing_skills": missing_skills
    }
