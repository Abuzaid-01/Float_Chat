"""
Hybrid Retriever — combines FAISS (semantic) + BM25 (keyword) with RRF reranking.

Why hybrid?
- FAISS excels at semantic similarity: "warm water near India" → finds temperature profiles
- BM25 excels at exact matches: "float 2902696" → finds that specific float
- Reciprocal Rank Fusion merges both without needing a trained reranker model

RRF formula: score(d) = Σ 1/(k + rank_i(d))
where k=60 (standard constant), rank_i(d) = rank of document d in result set i
"""

import re
import logging
import numpy as np
from typing import List, Tuple, Dict, Optional
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Hybrid retrieval combining FAISS vector search + BM25 keyword search,
    merged with Reciprocal Rank Fusion (RRF).
    """

    def __init__(self, vector_store, rrf_k: int = 60):
        """
        Args:
            vector_store: FAISSVectorStore instance (already loaded)
            rrf_k: RRF constant (default 60, standard in literature)
        """
        self.vector_store = vector_store
        self.rrf_k = rrf_k

        # Build BM25 index from vector store metadata
        self.bm25_index = None
        self.bm25_corpus_meta = []  # metadata aligned with BM25 corpus
        self._build_bm25_index()

    def _build_bm25_index(self):
        """
        Build a BM25 index from the existing vector store metadata.
        Uses the 'summary_text' field that's already stored with each vector.
        """
        metadata = self.vector_store.metadata
        if not metadata:
            logger.warning("⚠️ No metadata in vector store, BM25 disabled")
            return

        corpus = []
        self.bm25_corpus_meta = []

        for meta in metadata:
            # Extract searchable text from metadata
            text = meta.get("summary_text", "")
            if not text:
                # Fallback: combine available fields
                parts = []
                for key in ("float_id", "region", "platform_type", "description"):
                    val = meta.get(key)
                    if val:
                        parts.append(str(val))
                text = " ".join(parts)

            if text:
                # Tokenize: lowercase, split on alphanumeric
                tokens = self._tokenize(text)
                corpus.append(tokens)
                self.bm25_corpus_meta.append(meta)

        if corpus:
            self.bm25_index = BM25Okapi(corpus)
            logger.info(f"✅ BM25 index built with {len(corpus)} documents")
        else:
            logger.warning("⚠️ Empty corpus, BM25 index not built")

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenizer: lowercase, split on non-alphanumeric."""
        text = text.lower()
        tokens = re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", text)
        return tokens

    def search(
        self,
        query_text: str,
        query_embedding: np.ndarray,
        k: int = 5,
        faiss_weight: float = 1.0,
        bm25_weight: float = 1.0,
    ) -> List[Tuple[float, dict]]:
        """
        Hybrid search: FAISS + BM25, merged with weighted RRF.

        Args:
            query_text: Raw user query string (for BM25)
            query_embedding: Query embedding vector (for FAISS)
            k: Number of results to return
            faiss_weight: Weight for FAISS scores in RRF (default 1.0)
            bm25_weight: Weight for BM25 scores in RRF (default 1.0)

        Returns:
            List of (rrf_score, metadata) tuples, sorted by RRF score descending
        """
        # Retrieve more candidates than needed for better fusion
        candidate_k = min(k * 3, 20)

        # ── FAISS (semantic) search ──
        faiss_results = self.vector_store.search(query_embedding, k=candidate_k)

        # ── BM25 (keyword) search ──
        bm25_results = self._bm25_search(query_text, k=candidate_k)

        # ── Reciprocal Rank Fusion ──
        merged = self._rrf_merge(
            faiss_results,
            bm25_results,
            faiss_weight=faiss_weight,
            bm25_weight=bm25_weight,
        )

        # Return top-k
        top_results = merged[:k]

        logger.info(
            f"🔀 Hybrid search: FAISS={len(faiss_results)} + "
            f"BM25={len(bm25_results)} → merged={len(merged)} → top-{k}"
        )

        return top_results

    def _bm25_search(
        self, query_text: str, k: int = 10
    ) -> List[Tuple[float, dict]]:
        """
        BM25 keyword search over the metadata corpus.
        """
        if self.bm25_index is None or not self.bm25_corpus_meta:
            return []

        tokens = self._tokenize(query_text)
        if not tokens:
            return []

        # Get BM25 scores for all documents
        scores = self.bm25_index.get_scores(tokens)

        # Get top-k indices by score
        top_indices = np.argsort(scores)[::-1][:k]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score > 0:
                results.append((score, self.bm25_corpus_meta[idx]))

        return results

    def _rrf_merge(
        self,
        faiss_results: List[Tuple[float, dict]],
        bm25_results: List[Tuple[float, dict]],
        faiss_weight: float = 1.0,
        bm25_weight: float = 1.0,
    ) -> List[Tuple[float, dict]]:
        """
        Reciprocal Rank Fusion to merge two ranked result lists.

        RRF score for document d:
            score(d) = w1 * 1/(k + rank_faiss(d)) + w2 * 1/(k + rank_bm25(d))
        """
        doc_scores: Dict[str, float] = {}
        doc_meta: Dict[str, dict] = {}

        # Score FAISS results
        for rank, (score, meta) in enumerate(faiss_results, 1):
            doc_id = self._doc_id(meta)
            rrf_score = faiss_weight * (1.0 / (self.rrf_k + rank))
            doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + rrf_score
            doc_meta[doc_id] = meta

        # Score BM25 results
        for rank, (score, meta) in enumerate(bm25_results, 1):
            doc_id = self._doc_id(meta)
            rrf_score = bm25_weight * (1.0 / (self.rrf_k + rank))
            doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + rrf_score
            if doc_id not in doc_meta:
                doc_meta[doc_id] = meta

        # Sort by RRF score descending
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

        return [(score, doc_meta[doc_id]) for doc_id, score in sorted_docs]

    def _doc_id(self, meta: dict) -> str:
        """Generate a stable document ID from metadata."""
        summary = meta.get("summary_text", "")
        if summary:
            return str(hash(summary))

        parts = [
            str(meta.get("float_id", "")),
            str(meta.get("cycle_number", "")),
            str(meta.get("region", "")),
        ]
        return str(hash("|".join(parts)))

    def get_stats(self) -> Dict:
        """Return stats about the hybrid retriever."""
        return {
            "bm25_documents": len(self.bm25_corpus_meta),
            "faiss_vectors": (
                self.vector_store.index.ntotal if self.vector_store.index else 0
            ),
            "rrf_k": self.rrf_k,
        }
