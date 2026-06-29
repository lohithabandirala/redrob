"""
AlgoYodhas — Redrob Hackathon Ranking Pipeline
===============================================
Single-command reproduction:
    python run_pipeline.py --candidates ./candidates.jsonl

Output: submission.csv (100 rows, spec-compliant)
Runtime: < 5 minutes on a 16 GB CPU machine
"""

import argparse
import os
import sys
import time
import pandas as pd

# Support running from any working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import config
from src.data_loader import stream_candidates, get_jd_text
from src.models.semantic import SemanticMatcher
from src.features.honeypot import is_honeypot
from src.features.extractor import extract_features
from src.ranker.scorer import calculate_final_score
from src.ranker.explainer import generate_reasoning


def parse_args():
    parser = argparse.ArgumentParser(
        description="Redrob AI Candidate Ranking Pipeline — AlgoYodhas"
    )
    parser.add_argument(
        "--candidates",
        default=config.CANDIDATES_PATH,
        help="Path to candidates.jsonl (default: %(default)s)"
    )
    parser.add_argument(
        "--out",
        default=config.SUBMISSION_OUT_PATH,
        help="Output CSV path (default: %(default)s)"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=config.TOP_K_RETRIEVAL,
        help="Candidates to retrieve from FAISS before re-ranking (default: %(default)s)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    start_time = time.time()

    print("=" * 60)
    print("  AlgoYodhas — Redrob AI Ranking Pipeline")
    print("=" * 60)
    print(f"  Candidates file : {args.candidates}")
    print(f"  Output          : {args.out}")
    print()

    # ── STAGE 1: Load model ────────────────────────────────────────
    print("[1/5] Loading SentenceTransformer (all-MiniLM-L6-v2)...")
    matcher = SemanticMatcher()

    # ── STAGE 2: Stream + pre-filter ──────────────────────────────
    print("[2/5] Streaming candidates and applying pre-filter...")

    JD_REQUIRED_SKILLS = {
        "python", "elasticsearch", "faiss", "pinecone", "weaviate", "qdrant",
        "milvus", "opensearch", "machine learning", "nlp", "llm",
        "sentence-transformers", "bge", "e5", "ndcg", "mrr", "map", "a/b test"
    }
    VECTOR_TECHS = [
        "pinecone", "weaviate", "qdrant", "milvus", "opensearch",
        "elasticsearch", "faiss", "sentence-transformers", "bge", "e5",
        "openai embeddings"
    ]

    valid_candidates = []
    total_scanned   = 0
    honeypots_found = 0

    for cand in stream_candidates(args.candidates):
        total_scanned += 1

        # Honeypot gate
        if is_honeypot(cand):
            honeypots_found += 1
            continue

        profile = cand.get("profile", {})
        exp     = profile.get("years_of_experience", 0)

        # Experience gate (JD requires 5-9; we allow from 4 with slight penalty)
        if exp < 4:
            continue

        skills       = cand.get("skills", [])
        cand_skills  = {s.get("name", "").lower() for s in skills}

        # Build text blob: summary + all job titles/descriptions
        text_blob = profile.get("summary", "").lower()
        for job in cand.get("career_history", []):
            text_blob += (
                " " + job.get("title", "").lower()
                + " " + job.get("description", "").lower()
            )

        # Python gate
        if "python" not in cand_skills and "python" not in text_blob:
            continue

        # Vector tech gate — must have at least one embedding/search technology
        has_vector_tech = (
            any(t in cand_skills for t in VECTOR_TECHS) or
            any(t in text_blob   for t in VECTOR_TECHS)
        )
        if not has_vector_tech:
            continue

        valid_candidates.append(cand)

        if total_scanned % 10000 == 0:
            print(f"    Scanned {total_scanned:,} / {total_scanned:,} "
                  f"... kept {len(valid_candidates):,}")

    t1 = time.time() - start_time
    print(f"    Done in {t1:.1f}s — scanned {total_scanned:,}, "
          f"flagged {honeypots_found} honeypots, "
          f"kept {len(valid_candidates):,} valid candidates.")

    if not valid_candidates:
        print("ERROR: No candidates passed the pre-filter. "
              "Check that candidates.jsonl contains AI/ML profiles.")
        sys.exit(1)

    # ── STAGE 3: Semantic indexing (FAISS) ────────────────────────
    print(f"[3/5] Encoding {len(valid_candidates):,} candidates into FAISS index...")
    matcher.index_candidates(valid_candidates)
    t2 = time.time() - start_time
    print(f"    Done in {t2:.1f}s.")

    # ── STAGE 4: Semantic search ───────────────────────────────────
    jd_query = get_jd_text()
    top_k    = min(args.top_k, len(valid_candidates))
    print(f"[4/5] Semantic search — retrieving top {top_k} candidates...")
    top_results = matcher.search(jd_query, top_k=top_k)
    t3 = time.time() - start_time
    print(f"    Done in {t3:.1f}s.")

    # ── STAGE 5: Re-rank + generate reasoning ─────────────────────
    print("[5/5] Re-ranking with multi-signal composite score...")
    final_results = []

    for cand_id, sem_score in top_results:
        cand     = matcher.candidate_cache[cand_id]
        features = extract_features(cand, JD_REQUIRED_SKILLS)
        score    = calculate_final_score(sem_score, features)
        reasoning = generate_reasoning(cand, features, sem_score)

        final_results.append({
            "candidate_id": cand_id,
            "score":        round(score, 4),
            "reasoning":    reasoning
        })

    # Sort: score DESC, then candidate_id ASC for deterministic tie-breaking
    final_results.sort(key=lambda x: (-x["score"], x["candidate_id"]))
    top_100 = final_results[:100]

    # ── Output ────────────────────────────────────────────────────
    submission_rows = [
        {
            "candidate_id": r["candidate_id"],
            "rank":         rank,
            "score":        r["score"],
            "reasoning":    r["reasoning"]
        }
        for rank, r in enumerate(top_100, 1)
    ]

    df = pd.DataFrame(submission_rows, columns=["candidate_id", "rank", "score", "reasoning"])
    df.to_csv(args.out, index=False, encoding="utf-8")

    elapsed = time.time() - start_time
    print()
    print("=" * 60)
    print(f"  Pipeline complete in {elapsed:.1f}s")
    print(f"  Output saved → {args.out}")
    print(f"  Top candidate: {top_100[0]['candidate_id']} "
          f"(score={top_100[0]['score']:.4f})")
    print("=" * 60)


if __name__ == "__main__":
    main()
