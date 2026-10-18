"""
Few-Shot Example Store with Dynamic Promotion.
Supplies high-quality query-SQL pairs to the LLM and dynamically learns from good queries.
"""

from typing import List, Dict, Optional
import numpy as np
import logging
from vector_store.embeddings import EmbeddingGenerator

logger = logging.getLogger(__name__)

# Curated seed examples covering all key oceanographic query patterns
SEED_EXAMPLES = [
    {
        "query": "Show temperature profiles in the Arabian Sea",
        "sql": """SELECT latitude, longitude, timestamp, pressure, temperature, salinity
FROM argo_profiles
WHERE latitude BETWEEN 5 AND 30
  AND longitude BETWEEN 40 AND 80
  AND temp_qc IN (1,2,3)
ORDER BY timestamp DESC
LIMIT 1000;""",
        "tags": ["geographic", "temperature", "arabian_sea"],
    },
    {
        "query": "How many floats are active in the dataset?",
        "sql": """SELECT COUNT(DISTINCT float_id) AS total_floats,
       MIN(timestamp) AS earliest_date,
       MAX(timestamp) AS latest_date
FROM argo_profiles;""",
        "tags": ["statistics", "count", "floats"],
    },
    {
        "query": "Compare average temperature and salinity between Arabian Sea and Bay of Bengal",
        "sql": """SELECT 
    CASE 
        WHEN latitude BETWEEN 5 AND 30 AND longitude BETWEEN 40 AND 80 THEN 'Arabian Sea'
        WHEN latitude BETWEEN 5 AND 25 AND longitude BETWEEN 80 AND 100 THEN 'Bay of Bengal'
    END as region,
    ROUND(AVG(temperature)::numeric, 2) as avg_temperature,
    ROUND(AVG(salinity)::numeric, 2) as avg_salinity,
    COUNT(*) as measurements
FROM argo_profiles
WHERE ((latitude BETWEEN 5 AND 30 AND longitude BETWEEN 40 AND 80)
    OR (latitude BETWEEN 5 AND 25 AND longitude BETWEEN 80 AND 100))
  AND temp_qc IN (1,2,3)
  AND sal_qc IN (1,2,3)
GROUP BY region;""",
        "tags": ["comparison", "regions", "statistics"],
    },
    {
        "query": "Show data for float 2902696",
        "sql": """SELECT cycle_number, latitude, longitude, timestamp, pressure, temperature, salinity
FROM argo_profiles
WHERE float_id LIKE '%2902696%'
  AND temp_qc IN (1,2,3)
ORDER BY cycle_number ASC, pressure ASC
LIMIT 1000;""",
        "tags": ["float_specific", "trajectory"],
    },
    {
        "query": "Show deep ocean measurements below 1000 meters",
        "sql": """SELECT float_id, latitude, longitude, timestamp, pressure, temperature, salinity, dissolved_oxygen
FROM argo_profiles
WHERE pressure > 1000
  AND temp_qc IN (1,2,3)
ORDER BY pressure DESC
LIMIT 1000;""",
        "tags": ["depth", "deep_ocean"],
    },
]


class ExampleStore:
    """
    Manages few-shot examples for prompt injection.
    Computes semantic similarity to find the most relevant examples for a user query.
    """

    def __init__(self):
        self.embedding_generator = EmbeddingGenerator()
        self.examples: List[Dict] = []
        self.embeddings: Optional[np.ndarray] = None

    def initialize(self):
        """Load and embed seed examples."""
        self.examples = [dict(ex) for ex in SEED_EXAMPLES]
        self._rebuild_index()

    def _rebuild_index(self):
        """Compute embeddings for all stored examples."""
        if not self.examples:
            self.embeddings = None
            return

        texts = [ex["query"] for ex in self.examples]
        emb_list = [self.embedding_generator.generate_embedding(t) for t in texts]
        self.embeddings = np.array(emb_list, dtype="float32")

    def get_similar_examples(self, query: str, k: int = 3) -> List[Dict]:
        """Retrieve the top-k most similar few-shot examples."""
        if not self.examples or self.embeddings is None:
            return []

        q_emb = self.embedding_generator.generate_embedding(query)
        q_norm = q_emb / (np.linalg.norm(q_emb) + 1e-9)

        # Compute cosine similarity
        e_norms = self.embeddings / (
            np.linalg.norm(self.embeddings, axis=1, keepdims=True) + 1e-9
        )
        sims = np.dot(e_norms, q_norm)

        top_indices = np.argsort(sims)[::-1][:k]
        results = []
        for idx in top_indices:
            ex = dict(self.examples[idx])
            ex["similarity"] = float(sims[idx])
            results.append(ex)

        return results

    def promote_from_logs(self, query: str, sql: str, result_count: int) -> bool:
        """
        Self-improvement: dynamically promote high-quality queries to example store.
        """
        if result_count < 1 or len(query) < 10:
            return False

        # Don't add duplicates
        for ex in self.examples:
            if ex["query"].lower() == query.lower():
                return False

        self.examples.append({"query": query, "sql": sql, "tags": ["promoted"]})
        self._rebuild_index()
        logger.info(f"📈 Promoted query to ExampleStore: '{query}'")
        return True

    def get_count(self) -> int:
        return len(self.examples)

    def get_stats(self) -> Dict:
        return {"total_examples": len(self.examples)}
