"""Global configuration constants for OCC IROPS Recovery Dashboard."""

# Header keyword mapping for dynamic header detection in AIMS DayRepReport.
#
# Aliases include English (canonical AIMS), Vietnamese (with and without
# diacritics, since the report can come either way depending on locale), and
# common variants observed in production exports.
HEADER_KEYWORD_MAP = {
    "DATE": [
        "DATE",
        "DATE OPS",
        "FLIGHT DATE",
        "NG\u00c0Y",
        "NG\u00c0Y BAY",
        "NGAY",
        "NGAY BAY",
    ],
    "FLT": [
        "FLT",
        "FLT NO",
        "FLT NO.",
        "FLIGHT",
        "FLIGHT NO",
        "FLIGHT NO.",
        "S\u1ed0 HI\u1ec6U",
        "S\u1ed0 HI\u1ec6U CHUY\u1ebeN BAY",
        "CHUY\u1ebeN",
        "CHUY\u1ebeN BAY",
        "CHUYEN",
        "CHUYEN BAY",
    ],
    "REG": [
        "REG",
        "REG.",
        "REG NO",
        "REGISTRATION",
        "TAIL",
        "T\u00c0U BAY",
        "TAU BAY",
        "\u0110\u0102NG K\u00dd",
        "DANG KY",
        "S\u1ed0 \u0110\u0102NG K\u00dd",
        "SO DANG KY",
    ],
    "AC": [
        "AC",
        "ACTYPE",
        "AIRCRAFT TYPE",
        "TYPE",
        "A/C",
        "LO\u1ea0I T\u00c0U",
        "LO\u1ea0I T\u00c0U BAY",
        "LOAI TAU",
        "LOAI TAU BAY",
    ],
    "DEP": [
        "DEP",
        "FROM",
        "ORIGIN",
        "DEP STN",
        "DEP STA",
        "DEP STATION",
        "\u0110I",
        "\u0110I\u1ec2M \u0110I",
        "DIEM DI",
        "S\u00c2N \u0110I",
        "SAN DI",
    ],
    "ARR": [
        "ARR",
        "TO",
        "DEST",
        "DESTINATION",
        "ARR STN",
        "ARR STA",
        "ARR STATION",
        "\u0110\u1ebeN",
        "\u0110I\u1ec2M \u0110\u1ebeN",
        "DIEM DEN",
        "S\u00c2N \u0110\u1ebeN",
        "SAN DEN",
    ],
    "STD": [
        "STD",
        "SCHED DEP",
        "SCHEDULED DEP",
        "GI\u1edc \u0110I",
        "GI\u1edc KH \u0110I",
        "GIO DI",
        "GIO KH DI",
    ],
    "STA": [
        "STA",
        "SCHED ARR",
        "SCHEDULED ARR",
        "GI\u1edc \u0110\u1ebeN",
        "GI\u1edc KH \u0110\u1ebeN",
        "GIO DEN",
        "GIO KH DEN",
    ],
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
    "impact_explanation",
    "cascade_root_flight",
]

MVP_LIMITATION_WARNING = (
    "Cascade detection is limited to flights within the loaded report date range. "
    "Overnight downstream rotations outside the loaded file are not included in MVP."
)
