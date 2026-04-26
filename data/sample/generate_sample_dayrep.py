"""Generate a realistic sample AIMS DayRepReport Excel file for demo and testing.

This script creates a sample report matching the MVP scenario:
- Date: 24/04/2026
- Airport closure: HAN 14:00-18:00
- Multiple aircraft with varying impact levels
- Realistic Vietnamese airline routes and registrations

Expected KPI after cascade analysis with HAN closure 14:00-18:00
(refreshed against the current cascade detector — see ``tests/test_cascade_detector.py``):
- Total flights: 358
- Affected flights: 139
- Level 1: 51
- Level 2: 41
- Level 3+: 47
- Aircraft affected: 26
"""

import random
from datetime import date, time, timedelta, datetime

import pandas as pd


AIRPORTS = ["HAN", "SGN", "DAD", "CXR", "PQC", "HPH", "VII", "VDH", "BMV", "UIH",
            "VCL", "THD", "DIN", "VDO", "PXU", "TBB", "VCA", "VCS"]

INTERNATIONAL = ["BKK", "SIN", "KUL", "NRT", "ICN", "PEK", "PVG", "HKG",
                 "TPE", "DEL", "BLR", "LHR", "CDG", "FRA", "SYD", "MEL"]

AIRCRAFT_TYPES = ["A321", "A321", "A321", "A330", "A350", "B787"]

REGISTRATIONS = [f"VN-A{i}" for i in range(500, 560)]


def _time_str(h: int, m: int) -> str:
    return f"{h:02d}:{m:02d}"


def _random_time(start_h: int, end_h: int) -> tuple[int, int]:
    h = random.randint(start_h, end_h - 1)
    m = random.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
    return h, m


def _flight_duration_minutes(origin: str, dest: str) -> int:
    domestic = set(AIRPORTS)
    if origin in domestic and dest in domestic:
        return random.choice([60, 75, 80, 90, 95, 100, 110, 120])
    return random.choice([150, 180, 210, 240, 300, 360, 420, 480, 540])


def generate_flights() -> list[dict]:
    flights = []
    flight_counter = 100
    used_regs = random.sample(REGISTRATIONS, 40)

    for reg in used_regs:
        ac_type = random.choice(AIRCRAFT_TYPES)
        num_sectors = random.randint(2, 6)
        current_airport = random.choice(AIRPORTS)
        current_h, current_m = _random_time(5, 8)

        for sector in range(num_sectors):
            if sector == 0 and random.random() < 0.3:
                dest = random.choice(INTERNATIONAL)
            elif random.random() < 0.15:
                dest = random.choice(INTERNATIONAL)
            else:
                dest = random.choice([a for a in AIRPORTS if a != current_airport])

            std_h, std_m = current_h, current_m
            duration = _flight_duration_minutes(current_airport, dest)
            arr_total = std_h * 60 + std_m + duration
            sta_h, sta_m = arr_total // 60, arr_total % 60

            if sta_h >= 24:
                break

            flights.append({
                "DATE": "24/04/2026",
                "FLT": str(flight_counter),
                "REG": reg,
                "AC": ac_type,
                "DEP": current_airport,
                "ARR": dest,
                "STD": _time_str(std_h, std_m),
                "STA": _time_str(sta_h, sta_m),
            })

            flight_counter += 1
            current_airport = dest
            turnaround = random.choice([30, 35, 40, 45, 50, 55, 60])
            next_total = sta_h * 60 + sta_m + turnaround
            current_h, current_m = next_total // 60, next_total % 60

            if current_h >= 23:
                break

    # Ensure we have flights that specifically hit HAN during closure
    han_affected_regs = random.sample(used_regs, min(24, len(used_regs)))

    for i, reg in enumerate(han_affected_regs):
        ac_type = random.choice(AIRCRAFT_TYPES)

        # Create arrival into HAN during closure
        arr_h = random.randint(14, 17)
        arr_m = random.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
        dep_origin = random.choice([a for a in AIRPORTS if a != "HAN"])
        duration = _flight_duration_minutes(dep_origin, "HAN")
        dep_total = arr_h * 60 + arr_m - duration
        if dep_total < 0:
            dep_total = 300
        dep_h, dep_m = dep_total // 60, dep_total % 60

        flights.append({
            "DATE": "24/04/2026",
            "FLT": str(flight_counter),
            "REG": reg,
            "AC": ac_type,
            "DEP": dep_origin,
            "ARR": "HAN",
            "STD": _time_str(dep_h, dep_m),
            "STA": _time_str(arr_h, arr_m),
        })
        flight_counter += 1

        # Create departure from HAN during closure
        dep2_h = random.randint(14, 17)
        dep2_m = random.choice([0, 15, 30, 35, 40, 45])
        if dep2_h * 60 + dep2_m <= arr_h * 60 + arr_m:
            dep2_h = arr_h
            dep2_m = arr_m + 35
            if dep2_m >= 60:
                dep2_h += 1
                dep2_m -= 60
        if dep2_h >= 18:
            continue
        dest2 = random.choice([a for a in AIRPORTS if a != "HAN"])
        dur2 = _flight_duration_minutes("HAN", dest2)
        arr2_total = dep2_h * 60 + dep2_m + dur2
        arr2_h, arr2_m = arr2_total // 60, arr2_total % 60
        if arr2_h >= 24:
            continue

        flights.append({
            "DATE": "24/04/2026",
            "FLT": str(flight_counter),
            "REG": reg,
            "AC": ac_type,
            "DEP": "HAN",
            "ARR": dest2,
            "STD": _time_str(dep2_h, dep2_m),
            "STA": _time_str(arr2_h, arr2_m),
        })
        flight_counter += 1

        # Add downstream flights on same aircraft
        current_airport = dest2
        cur_h, cur_m = arr2_h, arr2_m
        turnaround = random.choice([35, 40, 45, 50])
        cur_total = cur_h * 60 + cur_m + turnaround
        cur_h, cur_m = cur_total // 60, cur_total % 60

        downstream_count = random.randint(1, 3)
        for _ in range(downstream_count):
            if cur_h >= 23:
                break
            next_dest = random.choice([a for a in AIRPORTS + INTERNATIONAL if a != current_airport])
            dur = _flight_duration_minutes(current_airport, next_dest)
            arr_total = cur_h * 60 + cur_m + dur
            arr_h_d, arr_m_d = arr_total // 60, arr_total % 60
            if arr_h_d >= 24:
                break

            flights.append({
                "DATE": "24/04/2026",
                "FLT": str(flight_counter),
                "REG": reg,
                "AC": ac_type,
                "DEP": current_airport,
                "ARR": next_dest,
                "STD": _time_str(cur_h, cur_m),
                "STA": _time_str(arr_h_d, arr_m_d),
            })
            flight_counter += 1
            current_airport = next_dest
            turn = random.choice([35, 40, 45])
            cur_total = arr_h_d * 60 + arr_m_d + turn
            cur_h, cur_m = cur_total // 60, cur_total % 60

    # Pad to ~358 flights
    while len(flights) < 358:
        reg = random.choice(used_regs)
        ac_type = random.choice(AIRCRAFT_TYPES)
        origin = random.choice(AIRPORTS)
        dest = random.choice([a for a in AIRPORTS if a != origin])
        h, m = _random_time(5, 22)
        dur = _flight_duration_minutes(origin, dest)
        arr_total = h * 60 + m + dur
        if arr_total >= 24 * 60:
            continue
        arr_h, arr_m = arr_total // 60, arr_total % 60
        flights.append({
            "DATE": "24/04/2026",
            "FLT": str(flight_counter),
            "REG": reg,
            "AC": ac_type,
            "DEP": origin,
            "ARR": dest,
            "STD": _time_str(h, m),
            "STA": _time_str(arr_h, arr_m),
        })
        flight_counter += 1

    flights = flights[:358]
    return flights


def create_dayrep_excel(output_path: str) -> None:
    """Create a sample DayRepReport Excel file with realistic structure."""
    random.seed(42)
    flights = generate_flights()

    df_flights = pd.DataFrame(flights)

    # Use numeric column indices so all DataFrames align correctly
    cols = list(range(8))

    title_rows = pd.DataFrame([
        ["AIMS DayRepReport", "", "", "", "", "", "", ""],
        ["Generated: 24/04/2026 06:00 UTC", "", "", "", "", "", "", ""],
        ["Airline: Vietnam Airlines", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "", ""],
    ], columns=cols)

    header_row = pd.DataFrame(
        [["DATE", "FLT", "REG", "AC", "DEP", "ARR", "STD", "STA"]],
        columns=cols,
    )

    df_flights.columns = cols

    footer_rows = pd.DataFrame([
        [f"Total: {len(flights)} flights", "", "", "", "", "", "", ""],
        ["Generated by AIMS v8.2", "", "", "", "", "", "", ""],
    ], columns=cols)

    combined = pd.concat(
        [title_rows, header_row, df_flights, footer_rows], ignore_index=True
    )

    combined.to_excel(output_path, index=False, header=False)
    print(f"Created sample DayRepReport: {output_path}")
    print(f"Total flights: {len(flights)}")
    print(f"Title rows: 4, Header row: 1, Footer rows: 2")


if __name__ == "__main__":
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output = os.path.join(script_dir, "sample_dayrep_24042026.xlsx")
    create_dayrep_excel(output)
