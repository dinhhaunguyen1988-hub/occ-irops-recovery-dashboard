"""Lat/Lon coordinates for airports referenced by the sample data.

Coordinates are public IATA-airport coordinates rounded to 4 decimal places
(~11 m precision — plenty for a regional map view). Sources: Wikipedia.

Missing airports return None from :func:`get_coords`; the map view falls
back to skipping that airport rather than failing.
"""

from __future__ import annotations

# IATA -> (lat, lon)
AIRPORT_COORDS: dict[str, tuple[float, float]] = {
    # Vietnam — domestic
    "HAN": (21.2212, 105.8071),
    "SGN": (10.8188, 106.6519),
    "DAD": (16.0439, 108.1990),
    "HPH": (20.8194, 106.7250),
    "VCA": (10.0851, 105.7117),
    "VCS": (8.7321, 106.6330),
    "PXU": (13.9550, 108.0167),
    "VKG": (9.9817, 105.1336),
    "TBB": (13.0496, 109.3334),
    "UIH": (13.7550, 109.0420),
    "VCL": (15.4033, 108.7060),
    "DLI": (11.7503, 108.3669),
    "VDO": (21.1178, 107.4142),
    "BMV": (12.6683, 108.1203),
    "DIN": (21.3975, 103.0080),
    "HUI": (16.4015, 107.7032),
    "CXR": (12.2271, 109.1925),
    "VII": (18.7376, 105.6705),
    "PQC": (10.2270, 103.9670),
    "VDH": (17.5150, 106.5907),
    "THD": (19.9015, 105.4671),
    # International
    "BKK": (13.6900, 100.7501),
    "SIN": (1.3644, 103.9915),
    "KUL": (2.7456, 101.7099),
    "NRT": (35.7720, 140.3929),
    "ICN": (37.4602, 126.4407),
    "PEK": (40.0801, 116.5846),
    "PVG": (31.1443, 121.8083),
    "HKG": (22.3080, 113.9185),
    "TPE": (25.0797, 121.2342),
    "DEL": (28.5562, 77.1000),
    "BLR": (13.1986, 77.7066),
    "LHR": (51.4700, -0.4543),
    "CDG": (49.0097, 2.5479),
    "FRA": (50.0379, 8.5622),
    "SYD": (-33.9461, 151.1772),
    "MEL": (-37.6690, 144.8410),
}


def get_coords(iata: object) -> tuple[float, float] | None:
    """Look up coordinates by IATA code (case-insensitive). Returns None when unknown."""
    if iata is None:
        return None
    key = str(iata).strip().upper()
    if not key:
        return None
    return AIRPORT_COORDS.get(key)
