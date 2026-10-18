"""
Domain-specific utility functions for oceanographic queries.
Expands acronyms, adds domain context, and normalizes ocean terms.
"""

import re
from typing import Dict, List

# Oceanographic acronym and term expansions
OCEAN_SYNONYMS: Dict[str, List[str]] = {
    # Parameters
    r"\bsst\b": "sea surface temperature",
    r"\bsss\b": "sea surface salinity",
    r"\bdo\b": "dissolved oxygen",
    r"\bchl\b": "chlorophyll",
    r"\bchla\b": "chlorophyll-a",
    r"\bt-s\b": "temperature salinity",
    r"\bts diagram\b": "temperature salinity diagram",
    r"\bmld\b": "mixed layer depth",
    r"\bqc\b": "quality control",
    # Regions & Features
    r"\beio\b": "Equatorial Indian Ocean",
    r"\bsio\b": "Southern Indian Ocean",
    r"\bas\b": "Arabian Sea",
    r"\bbob\b": "Bay of Bengal",
    r"\bthermocline\b": "thermocline layer depth 50 to 200 meters",
    r"\bpycnocline\b": "density gradient layer",
    r"\bhalocline\b": "salinity gradient layer",
    r"\bdeep ocean\b": "pressure greater than 1000 dbar depth",
    r"\bsurface\b": "pressure less than 10 dbar surface layer",
    r"\beuphotic\b": "pressure less than 200 dbar euphotic zone",
}


def expand_query(query: str) -> str:
    """
    Expand domain acronyms and add context for better retrieval.
    E.g., "SST in AS" -> "sea surface temperature in Arabian Sea"
    """
    expanded = query
    for pattern, replacement in OCEAN_SYNONYMS.items():
        expanded = re.sub(pattern, replacement, expanded, flags=re.IGNORECASE)
    return expanded.strip()
