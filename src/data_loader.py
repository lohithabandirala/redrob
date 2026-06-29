import json
from typing import Iterator, Dict, Any

def stream_candidates(filepath: str) -> Iterator[Dict[str, Any]]:
    """
    Streams candidates from a JSONL file one by one to avoid loading 
    the entire 100,000+ pool into memory at once.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)

def get_jd_text() -> str:
    """
    Returns a cleaned string representing the Job Description target.
    """
    # Hardcoded based on the job_description.txt analysis for speed
    return (
        "Senior AI Engineer, Founding Team, Redrob AI. "
        "Requires 5-9 years experience. "
        "Must have production experience with embeddings-based retrieval systems "
        "(sentence-transformers, OpenAI embeddings, BGE, E5) deployed to real users. "
        "Requires production experience with vector databases or hybrid search infrastructure "
        "(Pinecone, Weaviate, Qdrant, Milvus, OpenSearch, Elasticsearch, FAISS). "
        "Strong Python. Experience designing evaluation frameworks for ranking systems "
        "(NDCG, MRR, MAP, offline-to-online correlation, A/B test interpretation). "
        "Nice to have: LLM fine-tuning, learning-to-rank, HR-tech, distributed systems. "
        "Not looking for pure research without production deployment."
    )
