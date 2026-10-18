"""
Shared oceanographic utilities used across FloatChat.

These are pure functions (no I/O, no LLM) so they are safe to unit-test and
reuse from the data loader, NetCDF extractor, MCP tools and migration scripts.

- classify_ocean_region: map a lat/lon pair to one of the 6 Indian-Ocean regions
  that the SQL generator already uses for auto-classification.
- normalize_float_id: strip the numpy byte-string wrapper (b'XXXXXX ') so float
  IDs are stored as clean strings (e.g. "6904092") and exact matches can use
  the float_id index instead of forcing LIKE '%...%' scans.
"""

from typing import Optional, FrozenSet

# (region_name, lat_min, lat_max, lon_min, lon_max)
# NOTE: order matters — more specific (smaller) regions are checked FIRST so
# overlapping boxes resolve to the specific region (e.g. the Andaman Sea sits
# inside the Bay of Bengal bbox; the Red Sea overlaps the Arabian Sea bbox).
REGION_BOUNDS: tuple = (
    ("Red Sea", 12, 30, 32, 44),
    ("Andaman Sea", 5, 20, 92, 100),
    ("Arabian Sea", 5, 30, 40, 80),
    ("Bay of Bengal", 5, 25, 80, 100),
    ("Equatorial Indian Ocean", -10, 5, 40, 100),
    ("Southern Indian Ocean", -50, -10, 20, 120),
)

# Canonical region names (also used for whitelisting user-provided region strings)
KNOWN_REGIONS: FrozenSet[str] = frozenset(name for name, *_ in REGION_BOUNDS)

# Whitelist of columns that may be used in dynamic SQL (aggregation/parameter)
ALLOWED_PARAMETERS: FrozenSet[str] = frozenset(
    {
        "temperature",
        "salinity",
        "pressure",
        "dissolved_oxygen",
        "chlorophyll",
        "ph",
    }
)


def classify_ocean_region(latitude: Optional[float], longitude: Optional[float]) -> Optional[str]:
    """
    Classify a measurement into one of the known Indian-Ocean regions.

    Returns None when coordinates are missing/outside any region (e.g. other
    oceans) so callers can store a NULL and queries simply filter it out.
    """
    if latitude is None or longitude is None:
        return None
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        return None

    for name, lat_min, lat_max, lon_min, lon_max in REGION_BOUNDS:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return name
    return None


def normalize_float_id(raw: Optional[object]) -> Optional[str]:
    """
    Normalize an ARGO float identifier to a clean string.

    Handles:
    - numpy byte strings (str(np.bytes_)) -> "b'6904092 '" -> "6904092"
    - raw bytes objects
    - padded/whitespace variants ("6904092 ", "'6904092'")
    """
    if raw is None:
        return None

    if isinstance(raw, (bytes, bytearray)):
        s = raw.decode("utf-8", errors="ignore")
    else:
        s = str(raw)

    s = s.strip()

    # Strip the repr() wrapper that numpy bytes produce: b'XXXX' or b"XXXX"
    if s.startswith("b'") and s.endswith("'"):
        s = s[2:-1]
    elif s.startswith('b"') and s.endswith('"'):
        s = s[2:-1]

    # Remove any remaining surrounding quotes
    s = s.strip().strip("'\"").strip()

    return s or None