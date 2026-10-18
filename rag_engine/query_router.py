"""
Smart Query Router for FloatChat RAG pipeline.
Routes queries to:
  1. Template Route: Instant 0ms deterministic SQL for common aggregate queries (LLM bypass)
  2. Simple RAG: Standard single-region or single-parameter queries
  3. Complex RAG: Multi-condition, comparative, or temporal reasoning queries
"""

import re
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class QueryRouter:
    """
    Classifies incoming queries into template, simple_rag, or complex_rag routes.
    """

    TEMPLATES = {
        r"^(?:how many|total|count of)\s+floats(?:\s+are\s+there|\s+in\s+dataset)?\??$": {
            "sql": "SELECT COUNT(DISTINCT float_id) AS total_floats FROM argo_profiles;",
            "reason": "Unique float count",
        },
        r"^(?:how many|total|count of)\s+(?:records|measurements|profiles)\??$": {
            "sql": "SELECT COUNT(*) AS total_records FROM argo_profiles;",
            "reason": "Total record count",
        },
        r"^(?:what is the\s+)?date range(?:\s+of\s+the\s+dataset)?\??$": {
            "sql": "SELECT MIN(timestamp) AS earliest_date, MAX(timestamp) AS latest_date FROM argo_profiles;",
            "reason": "Dataset date range",
        },
    }

    def classify(self, query: str) -> Dict:
        """
        Classify query into appropriate execution route.
        """
        q_clean = query.strip().lower()

        # 1. Check deterministic templates (0ms bypass)
        for pattern, info in self.TEMPLATES.items():
            if re.search(pattern, q_clean):
                return {
                    "route": "template",
                    "template_sql": info["sql"],
                    "reason": info["reason"],
                }

        # 2. Check for complex RAG indicators
        complex_indicators = [
            "compare",
            "difference",
            "versus",
            "vs",
            "unusual",
            "anomaly",
            "trend",
            "relationship",
            "correlation",
            "water mass",
            "thermocline",
        ]
        if any(ind in q_clean for ind in complex_indicators):
            return {
                "route": "complex_rag",
                "reason": "Complex comparative or analytical query",
            }

        # 3. Default to standard Simple RAG
        return {
            "route": "simple_rag",
            "reason": "Standard data query",
        }

    def get_template_count(self) -> int:
        return len(self.TEMPLATES)
