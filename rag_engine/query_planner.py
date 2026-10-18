"""
Query Planning module for complex multi-condition and comparative oceanographic queries.
Decomposes complex requests into structured sub-intents and spatial/temporal bounds.
"""

import re
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class QueryPlanner:
    """
    Analyzes complex questions and extracts structured filters, regions,
    time ranges, and comparison targets for SQL generation.
    """

    def plan(self, query: str) -> Dict:
        """
        Produce a structured plan for the query.
        """
        q_lower = query.lower()

        plan = {
            "intent_type": "standard_retrieval",
            "regions": [],
            "parameters": [],
            "float_ids": [],
            "depth_range": None,
            "time_range": None,
            "needs_multi_query": False,
        }

        # 1. Detect Comparative Intents
        if any(w in q_lower for w in ["compare", "versus", "vs", "difference between"]):
            plan["intent_type"] = "regional_comparison"
            plan["needs_multi_query"] = True

        # 2. Extract Ocean Regions
        region_map = {
            "arabian sea": "Arabian Sea",
            "bay of bengal": "Bay of Bengal",
            "equatorial indian ocean": "Equatorial Indian Ocean",
            "southern indian ocean": "Southern Indian Ocean",
            "red sea": "Red Sea",
            "andaman sea": "Andaman Sea",
        }
        for kw, name in region_map.items():
            if kw in q_lower:
                plan["regions"].append(name)

        # 3. Extract Float IDs
        float_matches = re.findall(r"\b(?:float\s*)?([0-9]{7})\b", q_lower)
        if float_matches:
            plan["float_ids"] = list(set(float_matches))
            plan["intent_type"] = "float_trajectory"

        # 4. Extract Parameters
        if any(w in q_lower for w in ["temp", "thermal", "warm", "cold"]):
            plan["parameters"].append("temperature")
        if any(w in q_lower for w in ["salin", "salt", "psu"]):
            plan["parameters"].append("salinity")
        if any(w in q_lower for w in ["oxygen", "do", "dissolved oxygen"]):
            plan["parameters"].append("dissolved_oxygen")
        if any(w in q_lower for w in ["chlorophyll", "chl", "chla"]):
            plan["parameters"].append("chlorophyll")
        if any(w in q_lower for w in ["ph", "acidity", "alkalinity"]):
            plan["parameters"].append("ph")

        # 5. Depth ranges
        if "surface" in q_lower or "upper" in q_lower:
            plan["depth_range"] = {"min": 0, "max": 10, "description": "surface (0-10m)"}
        elif "deep" in q_lower or "abyssal" in q_lower or "bottom" in q_lower:
            plan["depth_range"] = {"min": 1000, "max": 6000, "description": "deep (>1000m)"}
        elif "thermocline" in q_lower:
            plan["depth_range"] = {"min": 50, "max": 200, "description": "thermocline (50-200m)"}

        return plan
