"""Global configuration constants for OCC IROPS Recovery Dashboard."""

# Header keyword mapping for dynamic header detection in AIMS DayRepReport
HEADER_KEYWORD_MAP = {
    "DATE": ["DATE", "DATE OPS", "FLIGHT DATE"],
    "FLT": ["FLT", "FLT NO", "FLIGHT", "FLIGHT NO"],
    "REG": ["REG", "REGISTRATION", "TAIL"],
    "AC": ["AC", "ACTYPE", "AIRCRAFT TYPE", "TYPE", "A/C"],
    "DEP": ["DEP", "FROM", "ORIGIN", "DEP STN"],
    "ARR": ["ARR", "TO", "DEST", "ARR STN"],
    "STD": ["STD", "SCHED DEP", "SCHEDULED DEP"],
    "STA": ["STA", "SCHED ARR", "SCHEDULED ARR"],
}

# Minimum number of header keyword groups that must match to identify the header row
MIN_HEADER_MATCH = 6

# Null time values that should be treated as None
NULL_TIME_VALUES = {"", "--:--", "--", "N/A", "NONE", "NULL"}

# Regex patterns for data validation
FLIGHT_NO_PATTERN = r"^[A-Z]{0,3}\s*\d{1,5}[A-Z]?$"
REG_PATTERN = r"^[A-Z]{1,2}-[A-Z0-9]{3,5}$"

# Canonical output column names
CANONICAL_COLUMNS = [
    "flight_date",
    "flight_no",
    "aircraft_reg",
    "aircraft_type",
    "origin",
    "destination",
    "std",
    "sta",
    "raw_row_number",
    "data_quality_warning",
]

# Columns added by cascade detector
CASCADE_COLUMNS = [
    "impact_level_numeric",
    "impact_level_display",
    "impact_reason",
    "cascade_root_flight",
]

MVP_LIMITATION_WARNING = (
    "Cascade detection is limited to flights within the loaded report date range. "
    "Overnight downstream rotations outside the loaded file are not included in MVP."
)
