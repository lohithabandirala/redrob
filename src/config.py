import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.dirname(BASE_DIR) # The directory above hackathon_submission

CANDIDATES_PATH = os.path.join(DATA_DIR, "candidates.jsonl")
SUBMISSION_OUT_PATH = os.path.join(BASE_DIR, "submission.csv")

# Hyperparameters for 5-min CPU execution
TOP_K_RETRIEVAL = 500  # Number of candidates to retrieve from vector search for reranking
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Score Weights
WEIGHTS = {
    "semantic": 40,
    "hard_skills": 20,
    "experience": 15,
    "behavioral": 25
}
