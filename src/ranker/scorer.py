from .. import config

def calculate_final_score(semantic_score: float, features: dict) -> float:
    """
    Calculates the final candidate score using the predefined weights.
    Ensure scores are properly normalized.
    """
    
    # Semantic score is from FAISS inner product, usually 0 to 1 for normalized vectors
    sem = max(0.0, min(1.0, semantic_score))
    
    h_skills = features.get("hard_skills_score", 0.0)
    exp = features.get("exp_score", 0.0)
    behav = features.get("behavioral_score", 0.0)
    
    # Weighted sum
    total_score = (
        (sem * config.WEIGHTS["semantic"]) +
        (h_skills * config.WEIGHTS["hard_skills"]) +
        (exp * config.WEIGHTS["experience"]) +
        (behav * config.WEIGHTS["behavioral"])
    )
    
    # Normalize to 0-100 range conceptually, though we can leave it as out of sum(WEIGHTS)
    max_score = sum(config.WEIGHTS.values())
    return total_score / max_score
