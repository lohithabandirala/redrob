def is_honeypot(candidate: dict) -> bool:
    """
    Detects if a candidate is a honeypot/trap based on impossible configurations.
    Returns True if it is a trap, False otherwise.
    """
    profile = candidate.get("profile", {})
    stated_exp = profile.get("years_of_experience", 0)
    
    # 1. Check for temporal impossibility: calculated experience significantly exceeds stated experience + buffers
    careers = candidate.get("career_history", [])
    total_months_worked = sum([job.get("duration_months", 0) for job in careers])
    
    # If the sum of all their job durations is more than 3 years longer than their stated experience,
    # it's highly likely a honeypot (unless they worked many concurrent jobs, but the dataset is designed this way).
    if (total_months_worked / 12) > (stated_exp + 3):
        return True
        
    # 2. Check for impossible skill durations
    skills = candidate.get("skills", [])
    if skills:
        max_skill_months = max([s.get("duration_months", 0) for s in skills])
        # If they claim to have used a skill for more years than they have experience (with a 2 year buffer)
        if (max_skill_months / 12) > (stated_exp + 2):
            return True
            
    # 3. Check for absurd number of 'expert' skills with 0 experience
    expert_zero_exp_count = sum(1 for s in skills if s.get("proficiency") == "expert" and s.get("duration_months", 0) < 6)
    if expert_zero_exp_count > 5:
        return True
        
    # 4. Perplexity / Burstiness Proxy (White-font keyword stuffing check)
    # Bot-generated keyword-stuffed profiles typically have very low unique word ratios.
    text_blob = profile.get("summary", "").lower()
    for job in careers:
        text_blob += " " + job.get("description", "").lower()
    
    words = text_blob.split()
    if len(words) > 50:
        unique_words = len(set(words))
        vocab_richness = unique_words / len(words)
        # If vocabulary richness is extremely low (< 20%), it's highly repetitive stuffing
        if vocab_richness < 0.20:
            return True

    return False
