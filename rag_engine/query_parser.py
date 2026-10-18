"""
Rule-based understanding of ARGO data questions.

`parse_question` turns a natural-language question into a `QuerySpec` — the
regions, floats, depth range, dates, coordinates, parameters and the kind of
answer wanted — and `build_query` turns that spec into SQL.

The guiding rule is: **only answer by rules what the rules fully understand.**
Every number in the question must be accounted for by a recognised constraint,
and questions that ask for something this grammar cannot express (medians,
correlations, "weird" data …) return `None`, so the caller falls back to the
LLM instead of silently answering a different question.

Everything here is pure (no I/O, no LLM): values placed in SQL come only from
fixed allow-lists or from numbers matched by regular expressions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

TABLE = "argo_profiles"

# Canonical region names stored in argo_profiles.ocean_region.
REGION_ALIASES: List[Tuple[str, str]] = [
    (r"arabian\s+sea", "Arabian Sea"),
    (r"bay\s+of\s+bengal", "Bay of Bengal"),
    (r"andaman\s+sea", "Andaman Sea"),
    (r"red\s+sea", "Red Sea"),
    (r"equatorial\s+indian\s+ocean", "Equatorial Indian Ocean"),
    (r"southern\s+indian\s+ocean", "Southern Indian Ocean"),
    (r"south(?:ern)?\s+indian\s+ocean", "Southern Indian Ocean"),
    (r"southern\s+ocean", "Southern Indian Ocean"),
    (r"equatorial(?:\s+(?:region|ocean|belt|zone))?", "Equatorial Indian Ocean"),
    (r"arabian", "Arabian Sea"),
    (r"bengal", "Bay of Bengal"),
    (r"andaman", "Andaman Sea"),
]

INDIAN_OCEAN_REGIONS = [
    "Arabian Sea",
    "Bay of Bengal",
    "Andaman Sea",
    "Red Sea",
    "Equatorial Indian Ocean",
    "Southern Indian Ocean",
]

# Word-boundary patterns: "do" must not match inside "does", "ph" not inside "graph".
PARAMETER_PATTERNS: List[Tuple[str, str]] = [
    ("temperature", r"temperatures?|temps?|thermal|warm(?:er|est|th)?|cold(?:er|est)?|cool(?:er|est)?|hot(?:ter|test)?|heat"),
    ("salinity", r"salinit(?:y|ies)|salt(?:y|ier|iest)?|saline|psu|fresh(?:er|est)?"),
    ("pressure", r"pressures?"),
    ("dissolved_oxygen", r"dissolved\s+oxygen|oxygen|o2|doxy"),
    ("chlorophyll", r"chlorophyll(?:-a)?|chla|chl|phytoplankton"),
    ("ph", r"ph|acidity|alkalinity"),
]

PARAMETER_LABELS = {
    "temperature": "temperature",
    "salinity": "salinity",
    "pressure": "pressure",
    "dissolved_oxygen": "dissolved oxygen",
    "chlorophyll": "chlorophyll",
    "ph": "pH",
}

# ARGO QC flags: 1 good, 2 probably good, 3 probably bad, 4 bad, 9 missing.
QC_COLUMN = {"temperature": "temp_qc", "salinity": "sal_qc"}
GOOD_QC = "(1, 2)"

MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sept": 9, "sep": 9, "october": 10,
    "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}
_MONTH_RE = "|".join(sorted(MONTHS, key=len, reverse=True))

CITIES = {
    "mumbai": (19.0760, 72.8777),
    "chennai": (13.0827, 80.2707),
    "kochi": (9.9312, 76.2673),
    "port blair": (11.6234, 92.7265),
    "colombo": (6.9271, 79.8612),
    "karachi": (24.8607, 67.0011),
}

# Requests the rule grammar cannot express.  Seeing one hands the question to the LLM.
UNSUPPORTED = re.compile(
    r"\b(correlat\w*|relationship|anomal\w*|unusual|weird|strange|outliers?|gradients?|"
    r"varianc\w*|deviation|stddev|std|median|percentiles?|quartiles?|histogram|"
    r"distribution|densit\w*|ratio|percent(?:age)?|proportion|predict\w*|forecast\w*|"
    r"why|explain|cause[sd]?|weekly|monthly|hourly|seasonal\w*|annual\w*|yearly|"
    r"except|excluding|exclude|other\s+than|outside|not\s+in|without|"
    r"mcp|tools?|model\s+context\s+protocol|"
    r"sound\s+speed|t-?s\s+diagram|per\s+cycle|each\s+cycle|by\s+cycle|"
    r"qc\s+flags?|quality\s+flags?|data\s+mode|platform)\b"
)

# Phrases that signal the user wants to WIDEN the scope, dropping inherited
# constraints.  For example, after asking about Oct 12, the follow-up
# "how many data for each day" means ALL days, not just Oct 12 again.
SCOPE_BROADENING = re.compile(
    r"\b(?:"
    # "each/every/all" + time unit
    r"(?:each|every|all|for\s+all|for\s+every|for\s+each)\s+"
    r"(?:day|date|week|month|year|float|region|sea|ocean|area|one|period|time)"
    r"|all\s+(?:data|days|dates|records|measurements|observations|the\s+data"
         r"|dataset|time|floats|regions|seas|oceans|profiles|available)"
    r"|entire\s+(?:dataset|data\s*set|period|range|time\s*line|data|archive)"
    r"|whole\s+(?:dataset|data\s*set|period|range|time\s*line|data|archive)"
    r"|complete\s+(?:dataset|data\s*set|data|archive)"
    r"|full\s+(?:dataset|data\s*set|data|range|archive)"
    r"|overall|everything|globally|everywhere"
    r"|across\s+all|over\s+all"
    r"|without\s+(?:any\s+)?(?:date|time|day|filter|restriction|limit)"
    r"|no\s+(?:date|time|day)\s+(?:filter|restriction|limit|constraint)"
    r"|remove\s+(?:the\s+)?(?:date|time|day|filter)"
    r"|ignore\s+(?:the\s+)?(?:date|time|day|filter|previous)"
    r")\b",
    re.IGNORECASE,
)

FOLLOW_UP = re.compile(
    r"^(?:and|also|ok(?:ay)?|now|then|so)\b|"
    r"\b(?:what|how)\s+about\b|"
    r"(?<!are )(?<!is )(?<!were )(?<!was )\bthere\b|"
    r"\b(?:that\s+(?:region|area|float|one|sea)|those|same|it|them|its|their|"
    r"this\s+(?:region|area|float|one|sea)|these|above|previous(?:ly)?|again|instead)\b"
)


@dataclass
class QuerySpec:
    """What the question asks for, independent of SQL."""

    regions: List[str] = field(default_factory=list)
    float_ids: List[str] = field(default_factory=list)
    cycle: Optional[int] = None
    parameters: List[str] = field(default_factory=list)

    depth_min: Optional[float] = None
    depth_max: Optional[float] = None
    date_from: Optional[datetime] = None  # inclusive
    date_to: Optional[datetime] = None  # exclusive
    lat_min: Optional[float] = None
    lat_max: Optional[float] = None
    lon_min: Optional[float] = None
    lon_max: Optional[float] = None
    point: Optional[Tuple[float, float]] = None
    radius_km: Optional[float] = None
    value_filters: List[Tuple[str, str, float]] = field(default_factory=list)

    # list | count | stats | compare | extreme | rank_floats | float_list |
    # trajectory | date_range | profile_analysis
    intent: str = "list"
    explicit_intent: bool = False
    count_target: str = "measurements"  # floats | profiles | measurements
    group_by: Optional[str] = None  # region | float | day | depth
    extreme: Optional[Tuple[str, str]] = None  # (column, "max" | "min")
    rank_by: Optional[str] = None  # cycles | measurements
    limit_n: Optional[int] = None
    latest_profiles: Optional[int] = None
    analysis: Optional[str] = None  # thermocline | water_masses
    include_bad_qc: bool = False
    follow_up: bool = False

    def has_scope(self) -> bool:
        return bool(
            self.regions or self.float_ids or self.point
            or self.lat_min is not None or self.lat_max is not None
            or self.lon_min is not None or self.lon_max is not None
        )

    def has_any_constraint(self) -> bool:
        return bool(
            self.has_scope() or self.parameters or self.value_filters
            or self.depth_min is not None or self.depth_max is not None
            or self.date_from or self.date_to or self.cycle is not None
        )

    def to_dict(self) -> Dict:
        data = asdict(self)
        for key in ("date_from", "date_to"):
            if data[key]:
                data[key] = data[key].isoformat()
        return data


@dataclass
class BuiltQuery:
    sql: str
    kind: str
    description: str
    # Totals over everything the filters match (the main query may be LIMITed).
    summary_sql: Optional[str] = None


class _Scanner:
    """Lower-cased question text from which recognised phrases are removed."""

    def __init__(self, text: str):
        text = text.lower().strip()
        text = text.replace("º", "°").replace("–", "-").replace("—", "-").replace("−", "-")
        text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)  # 1,000 -> 1000
        self.text = f" {text} "

    def take(self, pattern: str) -> Optional[re.Match]:
        match = re.search(pattern, self.text)
        if match:
            self.text = self.text[: match.start()] + " § " + self.text[match.end():]
        return match

    def take_all(self, pattern: str) -> List[re.Match]:
        found = []
        while True:
            match = self.take(pattern)
            if not match:
                return found
            found.append(match)

    def has(self, pattern: str) -> bool:
        return re.search(pattern, self.text) is not None


_NUM = r"(-?\d+(?:\.\d+)?)"
_DEPTH_UNIT = r"(?:m|meters?|metres?|dbar|db|decibars?)\b"
_GT = r"(?:above|over|greater\s+than|higher\s+than|more\s+than|exceeding|exceeds?|>=?|at\s+least)"
_LT = r"(?:below|under|less\s+than|lower\s+than|<=?|at\s+most)"
# In depth phrases the words flip meaning: "below 500 m" is deeper, "above 200 m" shallower.
_DEEPER = r"(?:deeper\s+than|below|beneath|under|greater\s+than|more\s+than|over|exceeding|>=?|at\s+least)"
_SHALLOWER = r"(?:shallower\s+than|above|less\s+than|<=?|at\s+most|within(?:\s+the)?(?:\s+(?:top|upper|first))?)"
# A threshold value: a whole number that is not the start of a depth ("200 m").
_VALUE = _NUM + r"(?![\d.])(?!\s*(?:m|meters?|metres?|dbar|db|decibars?)\b)"


def _signed(value: float, direction: str) -> float:
    return -value if direction[0] in ("s", "w") else value


def _parse_dates(scan: _Scanner, spec: QuerySpec, anchor: Optional[datetime]) -> bool:
    """Extract date constraints.  Returns False if a date could not be resolved."""
    default_year = anchor.year if anchor else None
    found: List[Tuple[int, datetime]] = []

    def add(match: re.Match, year, month, day) -> bool:
        year = int(year) if year else default_year
        if year is None:
            return False
        try:
            found.append((match.start(), datetime(year, int(month), int(day))))
        except ValueError:
            return False
        return True

    # Record the connector words before the dates are blanked out.
    original = scan.text

    for match in scan.take_all(r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b"):
        if not add(match, match.group(1), match.group(2), match.group(3)):
            return False
    for match in scan.take_all(
        rf"\b({_MONTH_RE})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(\d{{4}}))?\b"
    ):
        if not add(match, match.group(3), MONTHS[match.group(1)], match.group(2)):
            return False
    for match in scan.take_all(
        rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({_MONTH_RE})\.?(?:,?\s+(\d{{4}}))?\b"
    ):
        if not add(match, match.group(3), MONTHS[match.group(2)], match.group(1)):
            return False

    if found:
        dates = sorted(date for _, date in found)
        day = timedelta(days=1)
        if len(dates) >= 2:
            spec.date_from, spec.date_to = dates[0], dates[-1] + day
        elif re.search(r"\b(before|until|up\s+to|prior\s+to)\b", original):
            spec.date_to = dates[0]
        elif re.search(r"\b(after|since|starting|onwards?)\b", original):
            spec.date_from = dates[0]
        else:
            spec.date_from, spec.date_to = dates[0], dates[0] + day
        return True

    # A whole month: "in October 2025", "during october".
    match = scan.take(rf"\b(?:in|during|for|of)\s+({_MONTH_RE})\b(?:,?\s+(\d{{4}}))?") or scan.take(
        rf"\b({_MONTH_RE})\s+(\d{{4}})\b"
    )
    if match:
        name, year = match.group(1), match.group(2)
        if name == "may" and not year:
            return False
        year = int(year) if year else default_year
        if year is None:
            return False
        month = MONTHS[name]
        spec.date_from = datetime(year, month, 1)
        spec.date_to = datetime(year + (month == 12), month % 12 + 1, 1)
        return True

    # Relative windows are measured back from the newest observation in the
    # dataset, not from today: this is an archive, not a live feed.
    relative = scan.take(r"\b(?:last|past|previous|recent)\s+(\d+)\s+(day|week|month)s?\b")
    span = None
    if relative:
        size = {"day": 1, "week": 7, "month": 30}[relative.group(2)]
        span = int(relative.group(1)) * size
    elif scan.take(r"\b(?:last|past|this)\s+week\b"):
        span = 7
    elif scan.take(r"\b(?:last|past|this)\s+month\b"):
        span = 30
    elif scan.take(r"\btoday\b"):
        span = 1
    elif scan.take(r"\byesterday\b"):
        span = -1
    if span is not None:
        if anchor is None:
            return False
        end = datetime(anchor.year, anchor.month, anchor.day) + timedelta(days=1)
        if span == -1:
            spec.date_from, spec.date_to = end - timedelta(days=2), end - timedelta(days=1)
        else:
            spec.date_from, spec.date_to = end - timedelta(days=span), end
    return True


def _parse_location(scan: _Scanner, spec: QuerySpec) -> None:
    # A point: "15N 65E", "15.5°S, 60°W".
    point = scan.take(rf"\b{_NUM}\s*°?\s*([ns])\b[,\s]*{_NUM}\s*°?\s*([ew])\b")
    if point:
        spec.point = (
            _signed(float(point.group(1)), point.group(2)),
            _signed(float(point.group(3)), point.group(4)),
        )
    else:
        pair = scan.take(rf"\blat(?:itude)?\s*{_NUM}\s*,?\s*lon(?:gitude)?\s*{_NUM}")
        if pair:
            spec.point = (float(pair.group(1)), float(pair.group(2)))
        else:
            for city, coords in CITIES.items():
                if scan.take(rf"\b{city}\b"):
                    spec.point = coords
                    break
    if spec.point:
        radius = scan.take(rf"\b{_NUM}\s*(km|kilometers?|kilometres?|miles?)\b")
        if radius:
            spec.radius_km = float(radius.group(1)) * (1.60934 if radius.group(2).startswith("mile") else 1.0)
        else:
            spec.radius_km = 200.0

    def set_range(axis: str, low: float, high: float) -> None:
        low, high = min(low, high), max(low, high)
        if axis == "lat":
            spec.lat_min, spec.lat_max = low, high
        else:
            spec.lon_min, spec.lon_max = low, high

    # "10N to 20N", "5S - 5N", "60E to 80E"
    for match in scan.take_all(rf"\b{_NUM}\s*°?\s*([nsew])\s*(?:-|to|and|through)\s*{_NUM}\s*°?\s*([nsew])\b"):
        a, da, b, db = float(match.group(1)), match.group(2), float(match.group(3)), match.group(4)
        if da in "ns" and db in "ns":
            set_range("lat", _signed(a, da), _signed(b, db))
        elif da in "ew" and db in "ew":
            set_range("lon", _signed(a, da), _signed(b, db))
    # "between 10 and 15 degrees north", "10-20°N", "10 to 20 east"
    for match in scan.take_all(
        rf"\b(?:between\s+|from\s+)?{_NUM}\s*(?:-|to|and)\s*{_NUM}\s*(?:°|degrees?|deg)?\s*"
        r"(north|south|east|west|n|s|e|w)\b"
    ):
        a, b, direction = float(match.group(1)), float(match.group(2)), match.group(3)
        axis = "lat" if direction[0] in "ns" else "lon"
        set_range(axis, _signed(a, direction), _signed(b, direction))
    # "latitude between 10 and 15", "longitudes 60 to 80"
    for match in scan.take_all(
        rf"\b(lat|lon)(?:itude|gitude)?s?\s+(?:between\s+|from\s+|of\s+)?{_NUM}\s*(?:-|to|and)\s*{_NUM}\b(?:\s*(?:°|degrees?))?"
    ):
        set_range(match.group(1), float(match.group(2)), float(match.group(3)))

    if scan.take(r"\b(?:northern\s+hemisphere|north\s+of\s+the\s+equator)\b"):
        spec.lat_min = 0.0 if spec.lat_min is None else spec.lat_min
    if scan.take(r"\b(?:southern\s+hemisphere|south\s+of\s+the\s+equator)\b"):
        spec.lat_max = 0.0 if spec.lat_max is None else spec.lat_max


def _parse_values_and_depth(scan: _Scanner, spec: QuerySpec) -> bool:
    """Value thresholds ("warmer than 28") and depth ranges.  False = ambiguous."""
    param_words = {name: pattern for name, pattern in PARAMETER_PATTERNS}

    def add_value(param: str, op: str, value: float) -> None:
        spec.value_filters.append((param, op, value))
        if param not in spec.parameters:
            spec.parameters.append(param)

    # Comparatives that name their own parameter.
    for pattern, param, op in [
        (r"\b(?:warmer|hotter)\s+than", "temperature", ">"),
        (r"\b(?:colder|cooler)\s+than", "temperature", "<"),
        (r"\b(?:saltier|more\s+saline)\s+than", "salinity", ">"),
        (r"\b(?:fresher|less\s+saline)\s+than", "salinity", "<"),
    ]:
        for match in scan.take_all(rf"{pattern}\s*{_NUM}\s*(?:°\s*c|°|degrees?(?:\s+celsius)?|celsius|psu|c\b)?"):
            add_value(param, op, float(match.group(1)))

    # "<parameter> between A and B", "<parameter> above N", with optional units.
    for name in ("temperature", "salinity", "dissolved_oxygen", "chlorophyll", "ph"):
        words = param_words[name]
        unit = r"(?:°\s*c|°|degrees?(?:\s+celsius)?|celsius|psu|c\b)?"
        filler = r"(?:\s+(?:is|are|was|were|values?|readings?|of))*"
        for match in scan.take_all(
            rf"\b(?:{words})\b{filler}\s+(?:between|from)\s+{_NUM}\s*{unit}\s*(?:and|to|-)\s*{_VALUE}\s*{unit}"
        ):
            low, high = sorted((float(match.group(1)), float(match.group(2))))
            add_value(name, ">=", low)
            add_value(name, "<=", high)
        for match in scan.take_all(rf"\b(?:{words})\b{filler}\s+{_GT}\s*{_VALUE}\s*{unit}"):
            add_value(name, ">", float(match.group(1)))
        for match in scan.take_all(rf"\b(?:{words})\b{filler}\s+{_LT}\s*{_VALUE}\s*{unit}"):
            add_value(name, "<", float(match.group(1)))

    # Bare thresholds with a temperature/salinity unit.
    for match in scan.take_all(rf"{_GT}\s*{_NUM}\s*(?:°\s*c|degrees?\s+celsius|celsius|°c)"):
        add_value("temperature", ">", float(match.group(1)))
    for match in scan.take_all(rf"{_LT}\s*{_NUM}\s*(?:°\s*c|degrees?\s+celsius|celsius|°c)"):
        add_value("temperature", "<", float(match.group(1)))
    for match in scan.take_all(rf"{_GT}\s*{_NUM}\s*psu\b"):
        add_value("salinity", ">", float(match.group(1)))
    for match in scan.take_all(rf"{_LT}\s*{_NUM}\s*psu\b"):
        add_value("salinity", "<", float(match.group(1)))

    # Depth ranges and thresholds (pressure in dbar ≈ depth in metres).
    match = scan.take(
        rf"\b(?:between|from)\s+{_NUM}\s*(?:{_DEPTH_UNIT})?\s*(?:and|to|-)\s*{_NUM}\s*{_DEPTH_UNIT}"
    ) or scan.take(rf"\b{_NUM}\s*(?:-|to)\s*{_NUM}\s*{_DEPTH_UNIT}")
    if match:
        spec.depth_min, spec.depth_max = sorted((float(match.group(1)), float(match.group(2))))

    match = scan.take(rf"\b(?:deeper\s+than|deeper|beneath)\s*{_NUM}\s*(?:{_DEPTH_UNIT})?") or scan.take(
        rf"{_DEEPER}\s*{_NUM}\s*{_DEPTH_UNIT}"
    )
    if match and spec.depth_min is None:
        spec.depth_min = float(match.group(1))
    match = (
        scan.take(rf"\b(?:shallower\s+than|shallower)\s*{_NUM}\s*(?:{_DEPTH_UNIT})?")
        or scan.take(rf"\b(?:top|upper|first|uppermost)\s+{_NUM}\s*{_DEPTH_UNIT}")
        or scan.take(rf"{_SHALLOWER}\s*{_NUM}\s*{_DEPTH_UNIT}")
    )
    if match and spec.depth_max is None:
        spec.depth_max = float(match.group(1))

    match = scan.take(rf"\b(?:at|around|near)\s+(?:a\s+)?(?:depth\s+of\s+)?{_NUM}\s*{_DEPTH_UNIT}(?:\s+depth)?") or scan.take(
        rf"\b{_NUM}\s*{_DEPTH_UNIT}\s+depth\b"
    )
    if match and spec.depth_min is None and spec.depth_max is None:
        depth = float(match.group(1))
        window = max(5.0, depth * 0.1)
        spec.depth_min, spec.depth_max = max(0.0, depth - window), depth + window

    if spec.depth_min is None and spec.depth_max is None:
        if scan.take(r"\b(?:sea\s+)?(?:near[-\s])?surface\b"):
            spec.depth_max = 10.0
        elif scan.take(r"\b(?:deep\s+(?:ocean|water|sea|layer)s?|abyssal)\b"):
            spec.depth_min = 1000.0

    # A bare "above 20" / "below 500" with no unit and no parameter is ambiguous.
    return not scan.has(rf"(?:\babove|\bbelow|\bunder|\bover)\s*\d")


def parse_question(
    question: str,
    dataset_end: Optional[datetime] = None,
) -> Optional[QuerySpec]:
    """Return a QuerySpec, or None when the question is outside the rule grammar.

    `dataset_end` is the newest timestamp in the data; it resolves dates given
    without a year and relative windows such as "last 7 days".
    """
    if not question or not question.strip():
        return None

    scan = _Scanner(question)
    spec = QuerySpec()
    raw = scan.text

    spec.follow_up = FOLLOW_UP.search(raw.strip()) is not None
    if UNSUPPORTED.search(raw):
        return None

    # --- identifiers -------------------------------------------------------
    for match in scan.take_all(r"\bfloats?(?:\s*(?:id|ids|number|no\.?|#))?\s*[:#]?\s*(\d{5,9})\b"):
        spec.float_ids.append(match.group(1))
    for match in scan.take_all(r"\b(\d{7})\b"):  # ARGO WMO numbers are seven digits
        spec.float_ids.append(match.group(1))
    spec.float_ids = list(dict.fromkeys(spec.float_ids))

    cycle = scan.take(r"\bcycles?(?:\s*(?:number|no\.?|#))?\s*(\d{1,4})\b")
    if cycle:
        spec.cycle = int(cycle.group(1))

    # --- how many rows / profiles -----------------------------------------
    latest = scan.take(r"\b(?:latest|last|most\s+recent|newest)\s+(\d{1,3})\s+profiles?\b")
    if latest:
        spec.latest_profiles = int(latest.group(1))
    elif scan.take(r"\b(?:latest|last|most\s+recent|newest)\s+profile\b"):
        spec.latest_profiles = 1
    top = scan.take(r"\b(?:top|first)\s+(\d{1,3})\b(?!\s*(?:m|meters?|metres?|dbar)\b)") or scan.take(
        r"\b(\d{1,3})\s+(?=(?:warmest|hottest|coldest|coolest|saltiest|freshest|deepest|shallowest|highest|lowest)\b)"
    )
    if top:
        spec.limit_n = max(1, min(int(top.group(1)), 100))

    # --- constraints -------------------------------------------------------
    if not _parse_dates(scan, spec, dataset_end):
        return None
    _parse_location(scan, spec)
    if not _parse_values_and_depth(scan, spec):
        return None

    for pattern, canonical in REGION_ALIASES:
        if scan.take(rf"\b{pattern}\b") and canonical not in spec.regions:
            spec.regions.append(canonical)
            scan.take_all(rf"\b{pattern}\b")
    if not spec.regions and scan.take(r"\b(?:north(?:ern)?\s+)?indian\s+ocean\b"):
        spec.regions = list(INDIAN_OCEAN_REGIONS)

    for name, pattern in PARAMETER_PATTERNS:
        if scan.has(rf"\b(?:{pattern})\b") and name not in spec.parameters:
            spec.parameters.append(name)

    # Any number still unexplained is a constraint these rules did not understand.
    leftover = re.sub(r"\b(?:o2|t-?s)\b", " ", scan.text)
    if re.search(r"\d", leftover):
        return None

    spec.include_bad_qc = scan.has(r"\b(?:raw|unfiltered|all\s+qc|no\s+qc|including\s+bad|bad\s+data)\b")

    # --- grouping ----------------------------------------------------------
    if scan.has(r"\b(?:by|per|each|across|between|among)\s+(?:ocean\s+)?(?:regions?|seas?|oceans?|basins?)\b|\bregional(?:ly)?\b|\bwhich\s+(?:region|sea|ocean|basin)\b"):
        spec.group_by = "region"
    elif scan.has(r"\b(?:by|per|each|for\s+each|for\s+every)\s+float\b"):
        spec.group_by = "float"
    elif scan.has(r"\b(?:by|per|each)\s+(?:day|date)\b|\bdaily\b|\bday\s+by\s+day\b|\bover\s+time\b|\btime\s+series\b|\btrends?\b|\bchang\w+\s+over\b"):
        spec.group_by = "day"
    elif scan.has(
        r"\b(?:by|per|with|vs\.?|versus|against)\s+depth\b|\bat\s+different\s+depths\b|\bdepth\s+(?:bins?|levels?|layers?)\b|"
        r"\b(?:chang|var)\w*\s+with\s+depth\b|\bas\s+(?:you|we)\s+go\s+deeper\b"
    ):
        spec.group_by = "depth"

    # --- intent ------------------------------------------------------------
    has_stats_words = scan.has(
        r"\b(?:average|averaged|avg|mean|statistics?|stats|summary|summari[sz]e|typical|overall|range\s+of|min(?:imum)?\s+and\s+max(?:imum)?)\b"
    )
    superlative = _detect_extreme(scan, spec)

    if scan.has(r"\b(?:thermoclines?|mixed\s+layers?|mld)\b"):
        spec.intent, spec.analysis, spec.explicit_intent = "profile_analysis", "thermocline", True
    elif scan.has(r"\bwater\s+mass(?:es)?\b"):
        spec.intent, spec.analysis, spec.explicit_intent = "profile_analysis", "water_masses", True
    elif spec.float_ids and scan.has(r"\b(?:trajector\w+|track(?:ed|s)?|path|route|drift\w*|mov\w+|positions?|locations?|where\s+(?:is|was|did|has))\b"):
        spec.intent, spec.explicit_intent = "trajectory", True
    elif scan.has(r"\b(?:date\s+range|time\s+(?:range|period|span)|temporal\s+coverage|when\s+(?:was|were|is)\s+(?:the\s+)?(?:data|measurements|observations)|earliest|what\s+dates?|which\s+dates?|how\s+(?:old|recent|new))\b"):
        spec.intent, spec.explicit_intent = "date_range", True
    elif scan.has(r"\b(?:how\s+many|number\s+of|count(?:\s+of)?|total\s+number)\b"):
        spec.intent, spec.explicit_intent = "count", True
        if scan.has(r"\b(?:how\s+many|number\s+of|count(?:\s+of)?|total\s+number(?:\s+of)?)\s+(?:\w+\s+){0,2}?floats?\b"):
            spec.count_target = "floats"
        elif scan.has(r"\b(?:how\s+many|number\s+of|count(?:\s+of)?|total\s+number(?:\s+of)?)\s+(?:\w+\s+){0,2}?(?:profiles?|cycles?)\b"):
            spec.count_target = "profiles"
        else:
            spec.count_target = "measurements"
    elif scan.has(r"\b(?:most|fewest|least)\s+(?!recent)(?:\w+\s+)?(?:cycles?|profiles?)\b"):
        spec.intent, spec.rank_by, spec.explicit_intent = "rank_floats", "cycles", True
    elif scan.has(r"\b(?:most|fewest|least)\s+(?!recent)(?:\w+\s+)?(?:measurements?|data|records?|observations?|readings?)\b"):
        spec.intent, spec.rank_by, spec.explicit_intent = "rank_floats", "measurements", True
    elif scan.has(r"\b(?:compar\w+|versus|vs\.?|difference\s+between|differ\w*)\b"):
        spec.intent, spec.explicit_intent = "compare", True
    elif superlative and not has_stats_words:
        spec.intent, spec.extreme, spec.explicit_intent = "extreme", superlative, True
    elif has_stats_words:
        spec.intent, spec.explicit_intent = "stats", True
    elif not spec.parameters and scan.has(r"\b(?:which|what|list|show|find|display|all|any)\b[^?]*\bfloats\b|\bfloats\s+(?:in|near|within|around)\b"):
        spec.intent, spec.explicit_intent = "float_list", True
    elif spec.group_by:
        spec.intent = "stats"

    if not spec.has_any_constraint() and not spec.explicit_intent:
        # Nothing recognised at all: let the caller decide (follow-up or LLM).
        return spec if spec.follow_up else None
    return spec


def _detect_extreme(scan: _Scanner, spec: QuerySpec) -> Optional[Tuple[str, str]]:
    named = [
        (r"\b(?:warmest|hottest)\b", ("temperature", "max")),
        (r"\b(?:coldest|coolest)\b", ("temperature", "min")),
        (r"\bsaltiest\b", ("salinity", "max")),
        (r"\bfreshest\b", ("salinity", "min")),
        (r"\bdeepest\b", ("pressure", "max")),
        (r"\bshallowest\b", ("pressure", "min")),
    ]
    for pattern, result in named:
        if scan.has(pattern):
            if result[0] not in spec.parameters and result[0] != "pressure":
                spec.parameters.insert(0, result[0])
            return result
    column = spec.parameters[0] if spec.parameters else None
    if column:
        if scan.has(r"\b(?:highest|maximum|max|peak|largest|greatest)\b"):
            return (column, "max")
        if scan.has(r"\b(?:lowest|minimum|min|smallest)\b"):
            return (column, "min")
    return None


def _is_scope_broadening(question: str) -> bool:
    """Return True when the question explicitly wants ALL data, not a filtered subset.

    For example, after asking about Oct 12, the follow-up "how many data for
    each day" means ALL days — the date filter from the previous turn must be
    dropped, not inherited.
    """
    return SCOPE_BROADENING.search(question) is not None


def merge_context(
    spec: QuerySpec,
    previous: Optional[QuerySpec],
    question: str = "",
) -> QuerySpec:
    """Fill what a follow-up question leaves unsaid from the previous question.

    If the user's question uses *scope-broadening* language ("each day",
    "all data", "entire dataset", …) then the corresponding inherited
    constraint is intentionally skipped.  This prevents the common
    real-world mistake of carrying forward a single-day date filter when
    the user clearly wants to see every day.
    """
    if previous is None:
        return spec

    broadening = _is_scope_broadening(question)

    # --- Spatial scope -------------------------------------------------------
    if not spec.has_scope() and not broadening:
        spec.regions = list(previous.regions)
        spec.float_ids = list(previous.float_ids)
        spec.point, spec.radius_km = previous.point, previous.radius_km
        spec.lat_min, spec.lat_max = previous.lat_min, previous.lat_max
        spec.lon_min, spec.lon_max = previous.lon_min, previous.lon_max
        if spec.cycle is None:
            spec.cycle = previous.cycle

    # --- Temporal scope ------------------------------------------------------
    # Only inherit the date window when the user did NOT ask for "all/each/every".
    if spec.date_from is None and spec.date_to is None and not broadening:
        spec.date_from, spec.date_to = previous.date_from, previous.date_to

    # --- Depth scope ---------------------------------------------------------
    if spec.depth_min is None and spec.depth_max is None and not broadening:
        spec.depth_min, spec.depth_max = previous.depth_min, previous.depth_max

    # --- Parameters ----------------------------------------------------------
    if not spec.parameters:
        spec.parameters = list(previous.parameters)

    # --- Intent inheritance --------------------------------------------------
    if not spec.explicit_intent and previous.intent in ("stats", "compare", "count", "extreme", "profile_analysis"):
        spec.intent = previous.intent
        spec.count_target = previous.count_target
        spec.analysis = previous.analysis
        if spec.group_by is None:
            spec.group_by = previous.group_by
        if previous.extreme and spec.parameters:
            # "what about salinity?" after "warmest temperature" -> highest salinity
            spec.extreme = (spec.parameters[0], previous.extreme[1])
    return spec


def resolve_with_history(
    question: str,
    previous_questions: List[str],
    dataset_end: Optional[datetime] = None,
) -> Optional[QuerySpec]:
    """Parse `question`, carrying context from earlier user questions when it is a follow-up."""
    spec = parse_question(question, dataset_end)
    if spec is None or not previous_questions:
        return _finalise(spec)

    if not _continues(spec, question):
        return _finalise(spec)

    context: Optional[QuerySpec] = None
    for earlier in previous_questions[-4:]:
        parsed = parse_question(earlier, dataset_end)
        if parsed is None:
            context = None  # an LLM-answered turn breaks the rule-based chain
            continue
        if not parsed.has_any_constraint() and not parsed.explicit_intent:
            continue
        context = merge_context(parsed, context, earlier) if _continues(parsed, earlier) else parsed
    return _finalise(merge_context(spec, context, question))


def _continues(spec: QuerySpec, question: str) -> bool:
    """Does this question lean on the one before it?

    Either it says so ("what about…", "there", "the same…"), or it is a bare
    fragment such as "and salinity?" with no place and no verb of its own.
    A complete question ("How many floats are there?") starts afresh.

    Scope-broadening follow-ups ("for each day", "all data") are also
    continuations — they inherit *structure* (intent, count target) from
    the previous question while intentionally dropping *filters*.
    """
    if spec.follow_up:
        return True
    if _is_scope_broadening(question):
        return True
    return not spec.explicit_intent and not spec.has_scope() and len(question.split()) <= 5


def _finalise(spec: Optional[QuerySpec]) -> Optional[QuerySpec]:
    """A follow-up that found nothing to inherit is not answerable by rules."""
    if spec is None:
        return None
    if not spec.has_any_constraint() and not spec.explicit_intent:
        return None
    return spec


# ---------------------------------------------------------------------------
# SQL building
# ---------------------------------------------------------------------------

def _num(value: float) -> str:
    return repr(float(value))


def _haversine(lat: float, lon: float) -> str:
    # LEAST/GREATEST keep rounding error from pushing acos outside [-1, 1].
    return (
        f"(6371 * acos(LEAST(1, GREATEST(-1, cos(radians({_num(lat)})) * cos(radians(latitude)) * "
        f"cos(radians(longitude) - radians({_num(lon)})) + sin(radians({_num(lat)})) * sin(radians(latitude))))))"
    )


def _conditions(spec: QuerySpec, parameters: List[str], with_qc: bool = True, require_values: bool = True) -> List[str]:
    conditions: List[str] = []
    if len(spec.float_ids) == 1:
        conditions.append(f"float_id = '{spec.float_ids[0]}'")
    elif spec.float_ids:
        conditions.append("float_id IN ({})".format(", ".join(f"'{fid}'" for fid in spec.float_ids)))
    if spec.cycle is not None:
        conditions.append(f"cycle_number = {int(spec.cycle)}")
    if spec.regions:
        conditions.append("ocean_region IN ({})".format(", ".join(f"'{region}'" for region in spec.regions)))
    if spec.date_from:
        conditions.append(f"timestamp >= '{spec.date_from:%Y-%m-%d %H:%M:%S}'")
    if spec.date_to:
        conditions.append(f"timestamp < '{spec.date_to:%Y-%m-%d %H:%M:%S}'")
    if spec.lat_min is not None:
        conditions.append(f"latitude >= {_num(spec.lat_min)}")
    if spec.lat_max is not None:
        conditions.append(f"latitude <= {_num(spec.lat_max)}")
    if spec.lon_min is not None:
        conditions.append(f"longitude >= {_num(spec.lon_min)}")
    if spec.lon_max is not None:
        conditions.append(f"longitude <= {_num(spec.lon_max)}")
    if spec.point and spec.radius_km:
        conditions.append(f"{_haversine(*spec.point)} <= {_num(spec.radius_km)}")
    if spec.depth_min is not None:
        conditions.append(f"pressure >= {_num(spec.depth_min)}")
    if spec.depth_max is not None:
        conditions.append(f"pressure <= {_num(spec.depth_max)}")
    for column, op, value in spec.value_filters:
        conditions.append(f"{column} {op} {_num(value)}")
    if require_values:
        for parameter in parameters:
            conditions.append(f"{parameter} IS NOT NULL")
    if with_qc and not spec.include_bad_qc:
        for parameter in parameters:
            if parameter in QC_COLUMN:
                conditions.append(f"{QC_COLUMN[parameter]} IN {GOOD_QC}")
    return list(dict.fromkeys(conditions))


def _where(conditions: List[str]) -> str:
    return f" WHERE {' AND '.join(conditions)}" if conditions else ""


def _stat_columns(parameters: List[str]) -> str:
    columns = ["COUNT(*) AS measurement_count"]
    for parameter in parameters:
        columns += [
            f"ROUND(AVG({parameter})::numeric, 3)::float8 AS average_{parameter}",
            f"ROUND(MIN({parameter})::numeric, 3)::float8 AS minimum_{parameter}",
            f"ROUND(MAX({parameter})::numeric, 3)::float8 AS maximum_{parameter}",
        ]
    return ", ".join(columns)


def _summary_sql(where: str, parameters: List[str]) -> str:
    columns = [
        "COUNT(*) AS total_matching",
        "COUNT(DISTINCT float_id) AS floats",
        "COUNT(DISTINCT (float_id, cycle_number)) FILTER (WHERE float_id IS NOT NULL) AS profiles",
        "MIN(timestamp) AS earliest",
        "MAX(timestamp) AS latest",
    ]
    for parameter in parameters:
        columns += [
            f"ROUND(AVG({parameter})::numeric, 3)::float8 AS average_{parameter}",
            f"ROUND(MIN({parameter})::numeric, 3)::float8 AS minimum_{parameter}",
            f"ROUND(MAX({parameter})::numeric, 3)::float8 AS maximum_{parameter}",
        ]
    return f"SELECT {', '.join(columns)} FROM {TABLE}{where};"


def describe(spec: QuerySpec) -> str:
    """One line saying how the question was understood (shown to the user)."""
    labels = [PARAMETER_LABELS[p] for p in spec.parameters]
    what = " and ".join(labels) if labels else "data"
    lead = {
        "list": f"{(what if labels else 'temperature and salinity').capitalize()} measurements",
        "count": {"floats": "Number of floats", "profiles": "Number of profiles"}.get(
            spec.count_target, f"Number of {what} measurements" if labels else "Number of measurements"
        ),
        "stats": f"Average, minimum and maximum {what if labels else 'temperature and salinity'}",
        "compare": f"Comparison of {what if labels else 'temperature and salinity'}",
        "extreme": (
            f"{'Highest' if spec.extreme and spec.extreme[1] == 'max' else 'Lowest'} "
            f"{PARAMETER_LABELS.get(spec.extreme[0], spec.extreme[0]) if spec.extreme else what}"
        ),
        "rank_floats": f"Floats ranked by number of {spec.rank_by or 'cycles'}",
        "float_list": "Floats",
        "trajectory": "Trajectory",
        "date_range": "Date range of the data",
        "profile_analysis": "Thermocline and mixed layer" if spec.analysis == "thermocline" else "Water masses",
    }[spec.intent]

    parts = [lead]
    if spec.group_by:
        parts.append({"region": "by region", "float": "by float", "day": "by day", "depth": "by depth"}[spec.group_by])
    if spec.float_ids:
        parts.append("float " + ", ".join(spec.float_ids))
    if spec.cycle is not None:
        parts.append(f"cycle {spec.cycle}")
    if spec.regions and len(spec.regions) < len(INDIAN_OCEAN_REGIONS):
        parts.append(", ".join(spec.regions))
    elif spec.regions:
        parts.append("Indian Ocean regions")
    if spec.point:
        lat, lon = spec.point
        parts.append(
            f"within {spec.radius_km:g} km of {abs(lat):g}°{'N' if lat >= 0 else 'S'} {abs(lon):g}°{'E' if lon >= 0 else 'W'}"
        )
    if spec.lat_min is not None or spec.lat_max is not None:
        parts.append(f"latitude {spec.lat_min if spec.lat_min is not None else '…'} to {spec.lat_max if spec.lat_max is not None else '…'}")
    if spec.lon_min is not None or spec.lon_max is not None:
        parts.append(f"longitude {spec.lon_min if spec.lon_min is not None else '…'} to {spec.lon_max if spec.lon_max is not None else '…'}")
    if spec.depth_min is not None and spec.depth_max is not None:
        parts.append(f"{spec.depth_min:g}–{spec.depth_max:g} dbar")
    elif spec.depth_min is not None:
        parts.append(f"deeper than {spec.depth_min:g} dbar")
    elif spec.depth_max is not None:
        parts.append(f"shallower than {spec.depth_max:g} dbar")
    for column, op, value in spec.value_filters:
        parts.append(f"{PARAMETER_LABELS.get(column, column)} {op} {value:g}")
    if spec.date_from and spec.date_to and spec.date_to - spec.date_from == timedelta(days=1):
        parts.append(f"on {spec.date_from:%d %b %Y}")
    elif spec.date_from and spec.date_to:
        parts.append(f"{spec.date_from:%d %b %Y} to {(spec.date_to - timedelta(days=1)):%d %b %Y}")
    elif spec.date_from:
        parts.append(f"from {spec.date_from:%d %b %Y}")
    elif spec.date_to:
        parts.append(f"before {spec.date_to:%d %b %Y}")
    if spec.latest_profiles:
        parts.append(f"latest {spec.latest_profiles} profile{'s' if spec.latest_profiles != 1 else ''}")
    return " · ".join(parts)


def build_query(spec: QuerySpec) -> Optional[BuiltQuery]:
    """Translate a QuerySpec into SQL.  Returns None if the spec is not buildable."""
    built = _build(spec)
    if built is None:
        return None
    # Say which quality rule the SQL applied, so the answer can state it truthfully.
    if "_qc IN" in built.sql:
        built.description += " · good-quality values only (QC 1–2)"
    else:
        built.description += " · all quality flags included"
    return built


def _build(spec: QuerySpec) -> Optional[BuiltQuery]:
    description = describe(spec)
    measured = [p for p in spec.parameters if p != "pressure"]

    if spec.intent == "count":
        where = _where(_conditions(spec, measured, with_qc=False))
        columns = (
            "COUNT(DISTINCT float_id) AS float_count, "
            "COUNT(DISTINCT (float_id, cycle_number)) FILTER (WHERE float_id IS NOT NULL) AS profile_count, "
            "COUNT(*) AS measurement_count"
        )
        if spec.group_by == "region":
            sql = f"SELECT ocean_region, {columns} FROM {TABLE}{where} GROUP BY ocean_region ORDER BY measurement_count DESC LIMIT 100;"
        elif spec.group_by == "day":
            sql = f"SELECT DATE(timestamp) AS day, {columns} FROM {TABLE}{where} GROUP BY DATE(timestamp) ORDER BY day LIMIT 1000;"
        elif spec.group_by == "float":
            where = _where(_conditions(spec, measured, with_qc=False) + ["float_id IS NOT NULL"])
            sql = (
                "SELECT float_id, COUNT(DISTINCT cycle_number) AS profile_count, COUNT(*) AS measurement_count "
                f"FROM {TABLE}{where} GROUP BY float_id ORDER BY measurement_count DESC, float_id LIMIT {spec.limit_n or 50};"
            )
        else:
            sql = f"SELECT {columns} FROM {TABLE}{where};"
        return BuiltQuery(sql, "count", description)

    if spec.intent == "date_range":
        where = _where(_conditions(spec, measured, with_qc=False))
        sql = (
            "SELECT MIN(timestamp) AS earliest, MAX(timestamp) AS latest, "
            "COUNT(DISTINCT DATE(timestamp)) AS days_with_data, COUNT(DISTINCT float_id) AS float_count, "
            f"COUNT(*) AS measurement_count FROM {TABLE}{where};"
        )
        return BuiltQuery(sql, "date_range", description)

    if spec.intent == "rank_floats":
        conditions = _conditions(spec, measured, with_qc=False) + ["float_id IS NOT NULL"]
        order = "cycle_count" if spec.rank_by == "cycles" else "measurement_count"
        sql = (
            "SELECT float_id, COUNT(DISTINCT cycle_number) AS cycle_count, COUNT(*) AS measurement_count, "
            "MIN(timestamp) AS first_seen, MAX(timestamp) AS last_seen "
            f"FROM {TABLE}{_where(conditions)} GROUP BY float_id ORDER BY {order} DESC, float_id LIMIT {spec.limit_n or 10};"
        )
        return BuiltQuery(sql, "rank_floats", description)

    if spec.intent == "float_list":
        conditions = _conditions(spec, [], with_qc=False) + ["float_id IS NOT NULL"]
        sql = (
            "SELECT float_id, COUNT(DISTINCT cycle_number) AS cycle_count, COUNT(*) AS measurement_count, "
            "ROUND(AVG(latitude)::numeric, 4)::float8 AS latitude, ROUND(AVG(longitude)::numeric, 4)::float8 AS longitude, "
            "MAX(timestamp) AS last_seen "
            f"FROM {TABLE}{_where(conditions)} GROUP BY float_id ORDER BY last_seen DESC, float_id LIMIT 1000;"
        )
        summary = (
            "SELECT COUNT(DISTINCT float_id) AS floats, COUNT(DISTINCT (float_id, cycle_number)) FILTER (WHERE float_id IS NOT NULL) AS profiles, "
            f"COUNT(*) AS total_matching FROM {TABLE}{_where(conditions)};"
        )
        return BuiltQuery(sql, "float_list", description, summary)

    if spec.intent == "trajectory":
        if not spec.float_ids:
            return None
        conditions = _conditions(spec, [], with_qc=False)
        sql = (
            "SELECT float_id, cycle_number, MIN(timestamp) AS timestamp, "
            "ROUND(AVG(latitude)::numeric, 4)::float8 AS latitude, ROUND(AVG(longitude)::numeric, 4)::float8 AS longitude, "
            "COUNT(*) AS measurement_count, ROUND(MAX(pressure)::numeric, 1)::float8 AS deepest_pressure "
            f"FROM {TABLE}{_where(conditions)} GROUP BY float_id, cycle_number ORDER BY timestamp, cycle_number LIMIT 1000;"
        )
        return BuiltQuery(sql, "trajectory", description)

    if spec.intent == "profile_analysis":
        # One complete, quality-controlled profile: the named one, else the newest in scope.
        scope = _conditions(spec, [], with_qc=False) + ["float_id IS NOT NULL"]
        quality = [] if spec.include_bad_qc else [f"temp_qc IN {GOOD_QC}", f"sal_qc IN {GOOD_QC}"]
        chosen = (
            f"(float_id, cycle_number) IN (SELECT float_id, cycle_number FROM {TABLE}{_where(scope)} "
            "GROUP BY float_id, cycle_number HAVING COUNT(*) >= 20 ORDER BY MAX(timestamp) DESC LIMIT 1)"
        )
        conditions = [chosen, "temperature IS NOT NULL", "salinity IS NOT NULL"] + quality
        sql = (
            "SELECT float_id, cycle_number, latitude, longitude, timestamp, pressure, temperature, salinity "
            f"FROM {TABLE}{_where(conditions)} ORDER BY pressure ASC LIMIT 5000;"
        )
        return BuiltQuery(sql, "profile_analysis", description)

    only_pressure = ["pressure"] if "pressure" in spec.parameters else None
    stat_parameters = (measured or only_pressure or ["temperature", "salinity"])[:3]

    if spec.intent in ("stats", "compare") or (spec.intent == "extreme" and spec.group_by):
        group = spec.group_by
        if spec.intent == "compare" and group is None:
            group = "float" if len(spec.float_ids) > 1 else "region"
        conditions = _conditions(spec, stat_parameters)
        columns = _stat_columns(stat_parameters)
        first_average = f"average_{stat_parameters[0]}"
        if group == "region":
            if spec.intent == "extreme" and not spec.regions:
                conditions.append("ocean_region <> 'Other'")
            direction = "ASC" if spec.extreme and spec.extreme[1] == "min" else "DESC"
            order = f"{first_average} {direction}" if spec.intent == "extreme" else "ocean_region"
            sql = f"SELECT ocean_region, {columns} FROM {TABLE}{_where(conditions)} GROUP BY ocean_region ORDER BY {order} LIMIT 100;"
        elif group == "float":
            conditions.append("float_id IS NOT NULL")
            sql = (
                f"SELECT float_id, {columns} FROM {TABLE}{_where(conditions)} "
                f"GROUP BY float_id ORDER BY measurement_count DESC, float_id LIMIT {spec.limit_n or 50};"
            )
        elif group == "day":
            sql = f"SELECT DATE(timestamp) AS day, {columns} FROM {TABLE}{_where(conditions)} GROUP BY DATE(timestamp) ORDER BY day LIMIT 1000;"
        elif group == "depth":
            span = (spec.depth_max if spec.depth_max is not None else 2000.0) - (spec.depth_min or 0.0)
            size = 25 if span <= 300 else 50 if span <= 1000 else 100
            sql = (
                f"SELECT (FLOOR(pressure / {size}) * {size})::int AS depth_bin, {columns} "
                f"FROM {TABLE}{_where(conditions + ['pressure IS NOT NULL'])} "
                "GROUP BY depth_bin ORDER BY depth_bin LIMIT 500;"
            )
        else:
            sql = f"SELECT {columns} FROM {TABLE}{_where(conditions)};"
        return BuiltQuery(sql, "compare" if spec.intent == "compare" else "stats", description)

    base_columns = ["float_id", "cycle_number", "latitude", "longitude", "timestamp", "pressure"]

    if spec.intent == "extreme" and spec.extreme:
        column, direction = spec.extreme
        shown = [p for p in dict.fromkeys([column] + measured) if p != "pressure"]
        conditions = _conditions(spec, shown or [])
        if column == "pressure":
            conditions.append("pressure IS NOT NULL")
        columns = list(dict.fromkeys(base_columns + shown + (["ocean_region"] if not spec.regions else [])))
        sql = (
            f"SELECT {', '.join(columns)} FROM {TABLE}{_where(conditions)} "
            f"ORDER BY {column} {'DESC' if direction == 'max' else 'ASC'}, timestamp DESC LIMIT {spec.limit_n or 5};"
        )
        return BuiltQuery(sql, "extreme", description)

    # Plain listing of measurements, newest first.
    listed = measured or ["temperature", "salinity"]
    conditions = _conditions(spec, listed)
    where = _where(conditions)
    columns = list(dict.fromkeys(base_columns + listed))
    if spec.point and spec.radius_km:
        columns.append(f"ROUND({_haversine(*spec.point)}::numeric, 1)::float8 AS distance_km")
    limit = 1000
    if spec.latest_profiles:
        scope = _conditions(spec, [], with_qc=False) + ["float_id IS NOT NULL"]
        conditions = conditions + [
            f"(float_id, cycle_number) IN (SELECT float_id, cycle_number FROM {TABLE}{_where(scope)} "
            f"GROUP BY float_id, cycle_number ORDER BY MAX(timestamp) DESC LIMIT {int(spec.latest_profiles)})"
        ]
        where = _where(conditions)
        limit = 5000
    sql = (
        f"SELECT {', '.join(columns)} FROM {TABLE}{where} "
        f"ORDER BY timestamp DESC, float_id, cycle_number, pressure ASC LIMIT {limit};"
    )
    return BuiltQuery(sql, "list", description, _summary_sql(where, listed))
