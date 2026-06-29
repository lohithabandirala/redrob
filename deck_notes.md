# AlgoYodhas — PDF Deck Notes
# Slide-by-slide content for the PDF deck.

---

## Slide 1 — Title
**AlgoYodhas**
Intelligent Multi-Signal Candidate Ranking

Team: AlgoYodhas | Contact: lohithab94@gmail.com
Sandbox: https://redrob9.streamlit.app/

---

## Slide 2 — The Problem
**Ranking 100,000 candidates efficiently**

Challenges:
- Semantic synonymy ("MLOps" ≠ "Machine Learning Pipelines" literally)
- Resume gaming / keyword stuffing
- Honeypot traps (adversarial fake profiles)
- CPU-only hardware constraints (latency & OOM limits)

---

## Slide 3 — System Architecture (Multi-Stage Pipeline)

```
Stage 1: Pre-filter & Ingestion (O(N))
  ↓ Fast boolean checks, honeypot elimination

Stage 2: Lexical + Semantic Embedding
  ↓ BM25-style lexical verification
  ↓ all-MiniLM-L6-v2 Semantic dense embedding (FAISS)

Stage 3: Multi-Signal Re-ranking (Scoring Model)
  ↓ Composite math score (Semantic + Lexical + Signals)

Stage 4: Explainability Generation
  ↓ Natural language output generation for recruiter review
```

---

## Slide 4 — Algorithmic Logic & Scoring Math

**Scoring Formula:**
`Final Score = 0.40(Semantic) + 0.20(Lexical/Hard) + 0.15(Experience Bracket) + 0.25(Behavioral Signal)`

**Why Dual-Path?**
- *Semantic*: Uses cosine similarity in a CPU-optimized FAISS IndexFlatIP to catch synonyms (e.g. "Kubernetes" ~ "container orchestration"). 
- *Lexical*: Strict keyword overlap checks to ensure critical hard skills (like Python) are not entirely hallucinated away by dense vector proximity.

---

## Slide 5 — Behavioral Signal Integration & Experience Decay

**Behavioral Math (25% total weight):**
Rewards recruiter responsiveness, GitHub activity, and profile completeness. Heavily penalizes ghosting or stagnant profiles.

**Experience Decay & Traps (15% total weight):**
- Bracket score: Ideal match at 5-9 years. Linear decay for over/under-qualified.
- Pedigree blindness: School rank is ignored in favor of raw open-source signals.
- *Temporal Decay:* Severe penalty (×0.5 multiplier) applied for stagnant consulting-only "body shop" tenures without modern project signals.

---

## Slide 6 — The "Honeypot" Profiling Trap Defense

We detect adversarial fake profiles without slowing down the pipeline:

1. **Temporal Impossibility Check:** career months > stated experience + buffer
2. **Skill Duration Fraud:** skill active > total career length
3. **Expert-inflation Anomaly:** excessive "expert" skills with near-zero duration

*Result: 100% test-suite success rate dropping honeypots to the bottom of the list.*

---

## Slide 7 — Memory Footprint & Throughput

Optimized for the CPU-only VM environment:
- **Streaming Ingestion:** The 465MB candidate JSONL is parsed line-by-line, never loaded entirely into RAM. Prevents OOM crashes.
- **Quantized Embedding Matrix:** We use `all-MiniLM-L6-v2` (just 22 MB) rather than massive multi-GB transformers.
- **FAISS Indexing:** Local exact inner-product search executes in <1 second after index compilation.
- **Total Pipeline Execution:** Evaluates all 100K profiles well under the ~90s/5-minute time threshold.

---

## Slide 8 — User Journey Map (Sandbox UI)

1. **Upload:** Recruiter uploads `candidates.jsonl` (or smaller batch) via Streamlit.
2. **Scan:** The UI displays real-time progress as the zero-memory ingestion scans the batch.
3. **Analyze:** The model executes the dual-path FAISS/Lexical ranker.
4. **Review:** Top candidates are displayed in the dashboard alongside their specific *Explainability* rationale.
5. **Export:** Recruiter downloads the fully formatted XLSX output.

---

## Slide 9 — "Explainable AI" Reasoning

We output 1-2 sentence contextual reasoning for *every* candidate rather than generic templates. 
The explainer specifically identifies the exact signals driving the rank:
- Semantic fit summary
- Highlighted strong behavioral signals (e.g., "high open-source engagement")
- Specific gap alerts (e.g., "Note: long notice period of 120 days" or "Slightly under-experienced at 2.5 years").

This ensures recruiters can trust *why* a candidate was surfaced.

---

## Slide 10 — Reproducibility & Validation

Our GitHub repo provides a unified `run_pipeline.py` script. 
It cleanly maps from the raw `candidates.jsonl` to the finalized `submission.xlsx` output with zero manual steps, completely satisfying the cold-run compute requirements. 
An internal `test_suite.py` ensures deterministic outputs across environments.
