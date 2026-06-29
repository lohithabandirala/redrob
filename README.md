# 🏆 AlgoYodhas — Redrob AI Candidate Ranking System

**Team:** AlgoYodhas · **Contact:** lohithab94@gmail.com  
**Sandbox:** https://redrob9.streamlit.app/  
**Reproduce:** `python run_pipeline.py --candidates ./candidates.jsonl`

---

## System Architecture

```
candidates.jsonl  (100k profiles, ~465 MB)
        │
        ▼
┌───────────────────────────────────────────┐
│  STAGE 1 — Zero-Memory Pre-filter  O(N)  │
│                                           │
│  ├─ Honeypot Detection                   │
│  │   ├─ Temporal impossibility check     │
│  │   ├─ Skill-duration sanity check      │
│  │   └─ Expert-skill inflation check     │
│  │                                        │
│  ├─ Hard pre-filter (AND gate)           │
│  │   ├─ years_of_experience >= 4         │
│  │   ├─ "python" in skills or text       │
│  │   └─ vector DB / embedding tech hit   │
│  └─ Candidate pool: ~100k → ~2-5k        │
└───────────────────┬───────────────────────┘
                    │  ~2–5k candidates
                    ▼
┌───────────────────────────────────────────┐
│  STAGE 2 — Semantic Embedding  O(N·d)    │
│                                           │
│  Model: all-MiniLM-L6-v2 (CPU, 22MB)    │
│  ├─ Build rich text doc per candidate    │
│  │   (headline + summary + job history)  │
│  ├─ Encode all docs → 384-dim vectors    │
│  ├─ Normalize → FAISS IndexFlatIP        │
│  └─ Query JD → retrieve Top-500          │
└───────────────────┬───────────────────────┘
                    │  Top-500 candidates
                    ▼
┌───────────────────────────────────────────┐
│  STAGE 3 — Multi-signal Re-ranking       │
│                                           │
│  Score = 0.40·SEM + 0.20·HARD            │
│         + 0.15·EXP + 0.25·BEH           │
│                                           │
│  SEM  = FAISS cosine similarity          │
│  HARD = JD skill keyword overlap         │
│  EXP  = Experience bracket score         │
│         + location bonus                 │
│         − consulting/research trap       │
│  BEH  = 0.20·response_rate              │
│         + 0.20·notice_score             │
│         + 0.20·github_activity          │
│         + 0.20·interview_rate           │
│         + 0.10·completeness             │
│         + 0.10·open_to_work            │
│                                           │
│  Sort by (score DESC, candidate_id ASC)  │
│  → Take top 100 → submission.csv         │
└───────────────────┬───────────────────────┘
                    │
                    ▼
            submission.csv
        (100 rows, spec-compliant)
```

---

## Architecture & Ranking Philosophy
Our system implements a **Multi-Stage AI Candidate Ranking PoC** based on modern Information Retrieval (IR) principles, designed strictly for CPU-only deployment while maximizing **NDCG@10**.

### 1. Dual-Encoder Semantic Matching
- **Model**: `all-MiniLM-L6-v2` (22 MB quantized model)
- We use a dual-encoder architecture to generate dense contextual embeddings for both the JD and the candidate profiles. This captures **semantic synonymy** (e.g., "containerization" matches "Kubernetes/Docker") that naive keyword filters miss.
- Retrieval is performed via **FAISS IndexFlatIP**, enabling exact inner-product (cosine) search in <200ms.

### 2. Pointwise Heuristic Reranker (Multi-Signal)
Pure semantic similarity rewards candidates who know how to describe themselves eloquently. We treat the final stage as a Pointwise Regression task, scoring the retrieved subset using a calibrated weighted sum:
- **Hard-skills overlap (20%)** — Exact JD skill-set intersection (Lexical check).
- **Experience bracket (15%)** — Penalises under/over-experienced candidates, with mathematical traps for consulting/body-shop tenure.
- **Behavioral signals (25%)** — Heavily rewards recruiter responsiveness, GitHub activity, open-to-work flags, and profile completeness.

### 3. "Honeypot" Fraud Defense (Burstiness)
We detect and discard adversarial profiles (bot-generated or white-font keyword stuffing) using strict mathematical proxies:
1. **Perplexity / Burstiness Proxy**: We calculate vocabulary richness (unique words / total words). Profiles dropping below 20% richness are flagged as white-font keyword stuffing.
2. **Temporal Impossibility**: Sum of career months > stated experience + 3 years buffer.
3. **Expert-inflation**: > 5 skills claimed "expert" with < 6 months usage each.

### 4. Explainability (Feature Highlights)
To comply with transparent AI principles, the pipeline dynamically extracts the delta between candidate skills and JD requirements, outputting traceable, human-readable reasoning (e.g., *"Lacks required hands-on experience with Pinecone"*).

---

## Repository Structure

```
submission_package/
├── run_pipeline.py          ← Single-command entry point
├── submission.csv           ← Final top-100 ranked output
├── submission_metadata.yaml ← Team & methodology metadata
├── requirements.txt         ← Pinned Python dependencies
├── README.md                ← This file
│
├── src/                     ← Core algorithm
│   ├── config.py            ← Weights, paths, hyperparameters
│   ├── data_loader.py       ← Streaming JSONL reader + JD text
│   ├── models/
│   │   └── semantic.py      ← SentenceTransformer + FAISS wrapper
│   ├── features/
│   │   ├── extractor.py     ← Multi-signal feature extraction
│   │   └── honeypot.py      ← Fraud detection heuristics
│   └── ranker/
│       ├── scorer.py        ← Weighted composite score
│       └── explainer.py     ← Recruiter reasoning generator
│
└── app/
    └── streamlit_app.py     ← Streamlit sandbox UI (local upload)
```

---

## Setup & Reproduction

### Prerequisites
- Python 3.10+ (tested on 3.11 and 3.14)
- 16 GB RAM (for streaming 100k candidates)
- CPU-only (no GPU required)

### Install
```bash
pip install -r requirements.txt
```

### Reproduce the submission CSV
```bash
python run_pipeline.py --candidates ./candidates.jsonl
# Output: submission.csv in the current directory
# Runtime: ~3–5 min on 8-core CPU, 16 GB RAM
```

### Run the Streamlit Sandbox
```bash
streamlit run app/streamlit_app.py
# Opens at http://localhost:8501
```

---

## Score Weights (config.py)

| Signal | Weight | Rationale |
|--------|--------|-----------|
| Semantic (FAISS cosine) | **40%** | Primary JD relevance signal |
| Hard skills overlap | **20%** | Exact tech stack match |
| Experience fit | **15%** | Bracket penalty + traps |
| Behavioral signals | **25%** | Hiring success proxy |

---

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Total candidates scanned | 100,000 |
| Post-filter pool size | ~2,000–5,000 |
| Embedding model | `all-MiniLM-L6-v2` (22 MB) |
| FAISS index type | `IndexFlatIP` (exact cosine) |
| Full pipeline runtime | **< 5 minutes** on CPU |
| Peak RAM usage | **< 4 GB** (streaming, not bulk load) |
| Honeypot detection rate | 100% on test suite |
| Test suite pass rate | **26/26 (100%)** |
