from typing import Dict, Any

def generate_reasoning(candidate: Dict[str, Any], features: dict, semantic_score: float) -> str:
    """
    Generates a 1-2 sentence explanation as required by the hackathon spec.
    """
    profile = candidate.get("profile", {})
    title = profile.get("current_title", "Candidate")
    exp = profile.get("years_of_experience", 0)
    loc = profile.get("location", "")
    signals = candidate.get("redrob_signals", {})
    
    strengths = []
    if semantic_score > 0.6:
        strengths.append("strong semantic match to JD requirements")
    
    if features.get("hard_skills_score", 0) > 0.5:
        strengths.append("good overlap with required tech stack")
        
    if features.get("exp_score", 0) >= 0.9:
        strengths.append(f"ideal {exp} years of experience")
        
    if "pune" in loc.lower() or "noida" in loc.lower():
        strengths.append("ideal location")
        
    if signals.get("github_activity_score", 0) > 50:
        strengths.append("strong open-source/GitHub activity")
        
    if features.get("behavioral_score", 0) > 0.6:
        strengths.append("highly active and responsive profile")
        
    concerns = []
    notice_period = signals.get("notice_period_days", 90)
    missing_skills = features.get("missing_skills", [])
    
    if notice_period > 60:
        concerns.append(f"long notice period ({notice_period} days)")
        
    if exp > 10:
        concerns.append(f"potentially over-experienced ({exp} years)")
    elif exp < 5:
        concerns.append(f"slightly under-experienced ({exp} years)")

    reasoning = f"{title} with {exp} years of experience."
    
    if strengths:
        reasoning += " Strong fit due to " + " and ".join(strengths[:2]) + "."
        
    if missing_skills:
        # Just grab the top 2 missing skills to keep the string concise
        gaps = missing_skills[:2]
        gap_str = " and ".join(gaps)
        concerns.insert(0, f"lacks required hands-on experience with {gap_str}")

    if concerns:
        reasoning += " Note: " + ", ".join(concerns) + "."
        
    return reasoning
