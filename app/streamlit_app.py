"""
AlgoYodhas — Redrob AI Candidate Ranking Sandbox
=================================================
Streamlit app for the hackathon sandbox requirement.
Accepts a small candidate JSONL upload (≤100 candidates),
runs the full ranking pipeline locally, and displays results.

Run:  streamlit run app/streamlit_app.py
"""
import streamlit as st
import pandas as pd
import json
import os
import sys
import time
import io

# Add parent dir to path to import src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.semantic import SemanticMatcher
from src.features.extractor import extract_features
from src.features.honeypot import is_honeypot
from src.ranker.explainer import generate_reasoning
from src.data_loader import get_jd_text


def sanitize_text(text: str) -> str:
    """Escape dollar signs to prevent Streamlit LaTeX rendering."""
    if not text:
        return ""
    return text.replace("$", r"\$")


# ── Page Config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Redrob AI Ranking Sandbox",
    page_icon=":material/analytics:",
    layout="wide"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Outfit', sans-serif !important; }
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        color: #f8fafc;
    }
    .stButton > button {
        background: linear-gradient(90deg, #ec4899 0%, #8b5cf6 100%) !important;
        color: white !important; border: none !important;
        border-radius: 12px !important; padding: 12px 24px !important;
        font-weight: 600 !important; transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(236, 72, 153, 0.3) !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(236, 72, 153, 0.5) !important;
    }
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px; padding: 15px;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    h1 {
        background: -webkit-linear-gradient(45deg, #f472b6, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────
st.title("AlgoYodhas — AI Candidate Ranking Sandbox")
st.write("Upload a small JSONL file (≤100 candidates) and run the full ML ranking pipeline locally.")

# ── Sidebar ───────────────────────────────────────────────────────
st.sidebar.header("Pipeline Configuration")
st.sidebar.markdown("""
**Model:** `all-MiniLM-L6-v2` (22 MB, CPU)  
**Index:** FAISS IndexFlatIP (exact cosine)  
**Weights:** 40% semantic · 20% hard · 15% exp · 25% behavioral
""")

# ── File Upload ───────────────────────────────────────────────────
st.subheader("📁 Upload Candidates (JSONL)")
uploaded_file = st.file_uploader(
    "Select a .jsonl file with candidate profiles",
    type=["jsonl"],
    help="Each line must be a valid JSON object with candidate_id, profile, skills, career_history, and redrob_signals."
)

if uploaded_file is not None:
    st.success(f"File loaded: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")

# ── Run Pipeline ──────────────────────────────────────────────────
if st.button("🚀 Run ML Ranking Pipeline", disabled=(uploaded_file is None)):
    st.info("Running full pipeline: Pre-filter → Semantic Embedding → FAISS Search → Re-ranking...")

    try:
        # ── Parse JSONL ───────────────────────────────────────────
        raw_text = uploaded_file.read().decode("utf-8")
        all_candidates = []
        for line in raw_text.strip().split("\n"):
            line = line.strip()
            if line:
                all_candidates.append(json.loads(line))

        total_uploaded = len(all_candidates)
        st.write(f"Parsed **{total_uploaded}** candidate profiles.")

        # ── Stage 1: Pre-filter ───────────────────────────────────
        JD_REQUIRED_SKILLS = {
            "python", "elasticsearch", "faiss", "pinecone", "weaviate",
            "qdrant", "milvus", "opensearch", "machine learning", "nlp",
            "llm", "sentence-transformers", "bge", "e5", "ndcg", "mrr",
            "map", "a/b test"
        }
        VECTOR_TECHS = [
            "pinecone", "weaviate", "qdrant", "milvus", "opensearch",
            "elasticsearch", "faiss", "sentence-transformers", "bge",
            "e5", "openai embeddings"
        ]

        valid_candidates = []
        honeypots = 0
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, cand in enumerate(all_candidates):
            progress_bar.progress((i + 1) / total_uploaded)

            if is_honeypot(cand):
                honeypots += 1
                continue

            profile = cand.get("profile", {})
            exp = profile.get("years_of_experience", 0)
            if exp < 4:
                continue

            skills = cand.get("skills", [])
            cand_skills = {s.get("name", "").lower() for s in skills}

            text_blob = profile.get("summary", "").lower()
            for job in cand.get("career_history", []):
                text_blob += " " + job.get("title", "").lower()
                text_blob += " " + job.get("description", "").lower()

            if "python" not in cand_skills and "python" not in text_blob:
                continue

            has_vector = (
                any(t in cand_skills for t in VECTOR_TECHS) or
                any(t in text_blob for t in VECTOR_TECHS)
            )
            if has_vector:
                valid_candidates.append(cand)

        progress_bar.progress(1.0)
        status_text.text(
            f"Pre-filter complete: {total_uploaded} scanned → "
            f"{len(valid_candidates)} valid, {honeypots} honeypots flagged."
        )

        if not valid_candidates:
            st.error("No candidates passed the pre-filter. "
                     "Ensure profiles have Python + vector DB experience.")
            st.stop()

        st.success(f"✅ {len(valid_candidates)} candidates passed pre-filter "
                   f"({honeypots} honeypots removed)")

        # ── Stage 2 & 3: Semantic search + Re-rank ────────────────
        with st.spinner("Loading SentenceTransformer & building FAISS index..."):
            matcher = SemanticMatcher()
            matcher.index_candidates(valid_candidates)

            JD_TEXT = get_jd_text()
            top_k = min(100, len(valid_candidates))
            results = matcher.search(JD_TEXT, top_k=top_k)

        # ── Stage 4: Score + explain ──────────────────────────────
        csv_rows = []
        display_results = []

        for rank, (cand_id, sem_score) in enumerate(results, 1):
            cand = matcher.candidate_cache[cand_id]
            features = extract_features(cand, JD_REQUIRED_SKILLS)
            reasoning = generate_reasoning(cand, features, sem_score)
            safe_reasoning = sanitize_text(reasoning)

            final_score = (
                (sem_score * 0.4)
                + (features["hard_skills_score"] * 0.3)
                + (features["exp_score"] * 0.15)
                + (features["behavioral_score"] * 0.15)
            )

            csv_rows.append(
                f'{cand_id},{rank},{final_score:.4f},"{reasoning}"'
            )
            display_results.append({
                "rank": rank,
                "candidate_id": cand_id,
                "score": final_score,
                "reasoning": safe_reasoning,
                "features": features,
            })

        # ── Display Results ───────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        st.write("### :material/workspace_premium: Top Candidate Matches")

        for res in display_results[:10]:
            with st.container():
                st.markdown(f"#### #{res['rank']} — {res['candidate_id']}")
                col1, col2 = st.columns([1, 4])

                with col1:
                    st.metric(label="Match Score",
                              value=f"{int(res['score'] * 100)}%")
                    st.progress(min(max(res["score"], 0.0), 1.0))

                with col2:
                    st.info(f"**Why they match:** {res['reasoning']}")

                st.markdown("<br>", unsafe_allow_html=True)

        # ── Download CSV ──────────────────────────────────────────
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.success(":material/check_circle: ML Pipeline finished successfully!")

        csv_output = "candidate_id,rank,score,reasoning\n" + "\n".join(csv_rows)
        st.download_button(
            label=":material/download: Download submission.csv",
            data=csv_output,
            file_name="submission.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Error during pipeline: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
