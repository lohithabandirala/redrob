import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Tuple, Dict
from src import config

class SemanticMatcher:
    def __init__(self, model_name: str = config.EMBEDDING_MODEL):
        # Load the sentence transformer model
        # using cpu by default as per hackathon spec
        self.model = SentenceTransformer(model_name, device='cpu')
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatIP(self.embedding_dim) # Inner product (Cosine sim for normalized vectors)
        
        # We need to store candidate mappings
        self.candidate_ids = []
        self.candidate_cache = {}

    def _build_document(self, candidate: Dict) -> str:
        """
        Builds a semantic document from a candidate profile.
        Combines headline, summary, and experience.
        """
        profile = candidate.get("profile", {})
        doc = profile.get("headline", "") + ". " + profile.get("summary", "")
        
        careers = candidate.get("career_history", [])
        for job in careers:
            doc += f" {job.get('title', '')} at {job.get('company', '')}. {job.get('description', '')}"
            
        return doc

    def index_candidates(self, candidates: List[Dict]):
        """
        Indexes a list of candidate dictionaries. 
        """
        docs = []
        for cand in candidates:
            self.candidate_ids.append(cand["candidate_id"])
            self.candidate_cache[cand["candidate_id"]] = cand
            docs.append(self._build_document(cand))
            
        if not docs:
            return
            
        # Encode and normalize for cosine similarity
        embeddings = self.model.encode(docs, normalize_embeddings=True, show_progress_bar=True, batch_size=64)
        
        # Add to FAISS index
        self.index.add(np.array(embeddings, dtype=np.float32))

    def search(self, query: str, top_k: int = 500) -> List[Tuple[str, float]]:
        """
        Searches the index and returns the top_k candidate IDs and their similarity scores.
        """
        query_embedding = self.model.encode([query], normalize_embeddings=True)
        scores, indices = self.index.search(np.array(query_embedding, dtype=np.float32), top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1:
                results.append((self.candidate_ids[idx], float(score)))
                
        return results
