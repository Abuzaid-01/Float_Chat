"""
Semantic Caching module for FloatChat RAG pipeline.
Uses cosine similarity on query embeddings with TTL and LRU eviction.
"""

import time
import numpy as np
from typing import Dict, Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)


class SemanticCache:
    """
    Semantic Cache for natural language queries and generated SQL.
    Returns sub-second cached results when similarity >= threshold.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.95,
        max_entries: int = 200,
        ttl_seconds: int = 1800,  # 30 minutes
    ):
        self.threshold = similarity_threshold
        self.max_entries = max_entries
        self.ttl = ttl_seconds
        self.cache: List[Dict] = []
        self.stats = {"hits": 0, "misses": 0, "evictions": 0}

    def check(self, query_embedding: np.ndarray) -> Optional[Dict]:
        """
        Check if semantically equivalent query exists in cache.
        Returns cached dict {query, sql, result_count, timestamp} or None.
        """
        if not self.cache:
            self.stats["misses"] += 1
            return None

        # Clean expired entries first
        now = time.time()
        self.cache = [e for e in self.cache if (now - e["timestamp"]) < self.ttl]

        if not self.cache:
            self.stats["misses"] += 1
            return None

        q_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-9)
        best_score = -1.0
        best_entry = None

        for entry in self.cache:
            e_emb = entry["embedding"]
            e_norm = e_emb / (np.linalg.norm(e_emb) + 1e-9)
            sim = float(np.dot(q_norm.flatten(), e_norm.flatten()))

            if sim > best_score:
                best_score = sim
                best_entry = entry

        if best_score >= self.threshold and best_entry is not None:
            self.stats["hits"] += 1
            best_entry["last_accessed"] = now
            logger.info(
                f"⚡ Semantic cache HIT (sim={best_score:.4f}): '{best_entry['query']}'"
            )
            return best_entry

        self.stats["misses"] += 1
        return None

    def store(
        self,
        query: str,
        embedding: np.ndarray,
        sql: str,
        result_count: int,
    ) -> None:
        """Store query, embedding, and generated SQL in cache."""
        now = time.time()

        # Evict oldest / least recently accessed if at max capacity
        if len(self.cache) >= self.max_entries:
            self.cache.sort(key=lambda x: x.get("last_accessed", x["timestamp"]))
            self.cache.pop(0)
            self.stats["evictions"] += 1

        self.cache.append(
            {
                "query": query,
                "embedding": embedding,
                "sql": sql,
                "result_count": result_count,
                "timestamp": now,
                "last_accessed": now,
            }
        )

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()

    def get_stats(self) -> Dict:
        """Get cache performance metrics."""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0.0
        return {
            "cached_entries": len(self.cache),
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": f"{hit_rate:.1f}%",
            "evictions": self.stats["evictions"],
        }
