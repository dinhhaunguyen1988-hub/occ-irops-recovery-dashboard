# 05 — Agent Implementation Guide

## 1. Mission for Coding Agent

Build a minimal but reliable OCC IROPS Recovery Dashboard for Airport Closure scenario.

The first version must prioritize:

1. Real AIMS DayRepReport parsing.
2. Correct cascade detection.
3. Explainable output.
4. Excel export.
5. Pilot readiness.

Do not expand scope until MVP is validated.

## 2. Suggested Repository Structure

```text
occ-irops-recovery-dashboard/
├── README.md
├── requirements.txt
├── app.py
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── parser/
│   │   ├── __init__.py
│   │   ├── dayrep_parser.py
│   │   └── time_parser.py
│   ├── cascade/
│   │   ├── __init__.py
│   │   └── cascade_detector.py
│   ├── export/
│   │   ├── __init__.py
│   │   └── excel_exporter.py
│   └── models/
│       ├── __init__.py
│       └── event.py
├── tests/
│   ├── test_time_parser.py
│   ├── test_dayrep_parser.py
│   └── test_cascade_detector.py
├── data/
│   ├── sample/
│   └── real_validation/
└── docs/
    ├── pilot_plan.md
    ├── known_limitations.md
    └── user_guide.md
```

## 3. Module Responsibilities

### `src/parser/time_parser.py`

Responsible for:

- Parsing AIMS time fields.
- Handling `HH:MM`, `HHMM`, `H:MM`, `2400`, blank, `--:--`, `+1`.
- Returning `datetime.time | None`.
- Creating warnings for unparseable values.

### `src/parser/dayrep_parser.py`

Responsible for:

- Loading DayRepReport Excel file.
- Detecting header row.
- Mapping raw columns to canonical schema.
- Removing footer rows.
- Normalizing aircraft registration.
- Returning clean dataframe and warnings.

### `src/cascade/cascade_detector.py`

Responsible for:

- Detecting Level 1 direct impact.
- Tracing downstream cascade by aircraft registration.
- Storing `impact_level_numeric`.
- Creating display field `impact_level_display`.
- Creating reason/audit field.

### `src/export/excel_exporter.py`

Responsible for:

- Exporting affected flights.
- Exporting summary KPI.
- Exporting data quality warnings.
- Exporting parameters used in the run.

### `app.py`

Responsible for:

- Streamlit UI.
- File upload.
- Event parameter input.
- Dashboard display.
- Warning display.
- Excel download.

## 4. Implementation Sequence

### Step 1 — Build and test time parser

Create test cases for:

```text
14:35
1435
6:05
605
2400
--:--
""
None
00:00+1
00:00+2
invalid
```

### Step 2 — Build DayRepReport parser

Test with realistic messy input:

- Title rows before header.
- Variable column names.
- Footer rows.
- Bad time values.
- REG with lowercase, spaces, missing hyphen.

### Step 3 — Build cascade detector

Test cases:

- Arrival into closed airport.
- Departure from closed airport.
- Flight at start boundary.
- Flight at end boundary.
- Multiple Level 1 flights on same aircraft.
- Downstream Level 2 and Level 3+.
- Aircraft with no impact.

### Step 4 — Build Streamlit UI

Minimum UI:

- Upload file.
- Enter airport.
- Enter closure date.
- Enter start/end time.
- Show summary KPIs.
- Show affected flight table.
- Show data warnings.
- Export Excel.

### Step 5 — Prepare pilot pack

- User guide.
- Known limitations.
- Feedback form.
- Tabletop Drill script.
- Phase 0 validation checklist.

## 5. Non-Negotiable Coding Rules

- Do not hardcode header row number.
- Do not hardcode column position.
- Do not use `<= closure_end`.
- Do not merge Level 1 detection and downstream cascade in one pass.
- Do not display Level 4/5/6 separately in MVP UI; display as `3+`.
- Do not drop rows silently; log warnings.
- Do not hide MVP limitation about report date range.
- Do not build optimization or recommendation engine in MVP.

## 6. Recommended Dataframe Columns After Cascade

```text
flight_date
flight_no
aircraft_reg
aircraft_type
origin
destination
std
sta
impact_level_numeric
impact_level_display
impact_reason
cascade_root_flight
raw_row_number
data_quality_warning
```

## 7. Suggested Streamlit Layout

```text
Page title: OCC IROPS Recovery Dashboard

Sidebar:
- Upload DayRepReport
- Airport code
- Closure date
- Closure start time
- Closure end time
- Run analysis button

Main:
1. MVP limitation warning
2. Data quality warning panel
3. KPI cards
4. Affected flights table
5. Aircraft rotation view
6. Export Excel button
```

## 8. Required UI Warning

```text
MVP Limitation:
Cascade detection is limited to flights within the loaded report date range.
Overnight downstream rotations outside the loaded file are not included.
```
