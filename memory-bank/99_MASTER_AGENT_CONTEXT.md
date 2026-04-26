# OCC IROPS Recovery Dashboard — Master Agent Context

This file combines all Agent-ready Markdown sections into one importable context.

---


# 00 — Project Context

## 1. Project Name

**OCC IROPS Recovery Dashboard**

## 2. Business Context

OCC needs a lightweight tool to support disruption impact analysis during IROPS, especially airport closure scenarios.

The tool should help OCC quickly identify:

- Directly affected flights.
- Downstream affected rotations.
- Aircraft registration chains.
- Impact levels.
- Summary KPIs.
- Exportable briefing output for Duty Manager / management.

## 3. MVP Scenario

The standard demo and tabletop scenario is:

| Item | Value |
|---|---|
| Airport | HAN |
| Closure start | 14:00 |
| Closure end | 18:00 |
| Date | 24/04/2026 |
| Boundary logic | Start inclusive, end exclusive |
| Rule | `time >= closure_start AND time < closure_end` |

## 4. MVP Input

Primary input file:

- AIMS `DayRepReport`

The parser must handle real AIMS exports, not only ideal sample data.

## 5. MVP Output

Expected MVP output includes:

- List of affected flights.
- Impact level: Level 1, Level 2, Level 3+.
- Actual numeric level stored internally.
- Aircraft registration.
- Route.
- STD / STA.
- Reason for impact.
- Exportable Excel report.
- Warnings for parser or data limitations.

## 6. Users and Roles

| Role | Responsibility |
|---|---|
| Developer / Code Agent | Build parser, cascade detector, UI, export, tests |
| AIMS PIC | Provide real DayRepReport, validate AIMS logic, coordinate pilot |
| OCC Controller | Run tool, review output, compare with operational understanding |
| Duty Manager | Use output as briefing input and make final operational decisions |
| Management | Review business value after pilot |

## 7. Core Framing

The correct framing for adoption:

> This is an automated AIMS report reader that reads the AIMS DayRepReport, calculates the impact structure, and prepares a review list for OCC.

Avoid presenting it as:

- AI decision-making.
- Automatic aircraft recovery.
- Replacement for AIMS.
- Replacement for OCC Controller or Duty Manager judgment.


---


# 01 — Cascade Detection Logic

## 1. Objective

Implement airport-closure impact detection and downstream cascade tracing for aircraft rotations.

The cascade logic must be deterministic, explainable, and auditable.

## 2. Boundary Condition — Time Window

### Rule

Airport closure time window must use:

```python
time >= closure_start AND time < closure_end
```

This means:

- Start boundary is inclusive.
- End boundary is exclusive.

### Reason

If airport closure is `14:00–18:00`, then:

- A flight arriving at `14:00:00` is affected.
- A flight arriving at `17:59` is affected.
- A flight arriving at `18:00:00` is not automatically affected because airport is assumed reopened.

### Example

| Flight | STA | Affected? | Explanation |
|---|---:|---|---|
| VN-A | 13:59 | No | Arrives before closure |
| VN-B | 14:00:00 | Yes | Exactly at closure start |
| VN-C | 17:59 | Yes | Within closure window |
| VN-D | 18:00:00 | No | End boundary is exclusive |

## 3. Level 1 Detection

### Level 1 arrival rule

A flight is Level 1 if destination airport is closed at scheduled arrival time:

```python
dest_affected = (
    (df["destination"] == event.airport) &
    (df["sta"] >= event.start_time) &
    (df["sta"] < event.end_time)
)
```

### Level 1 departure rule

A flight is Level 1 if origin airport is closed at scheduled departure time:

```python
orig_affected = (
    (df["origin"] == event.airport) &
    (df["std"] >= event.start_time) &
    (df["std"] < event.end_time)
)
```

### Combined Level 1 rule

```python
df.loc[dest_affected | orig_affected, "impact_level"] = 1
```

## 4. Level 2 and Downstream Cascade

After Level 1 flights are detected, downstream sectors on the same aircraft are assigned increasing impact levels.

Example:

| Correct level | Flight | Route | STD | STA | Reason |
|---:|---|---|---:|---:|---|
| 1 | 1504 | DAD → HAN | 12:40 | 14:00 | Cannot land — destination closed |
| 1 | 1505 | HAN → DAD | 14:35 | 15:55 | Cannot depart — origin closed |
| 2 | 637 | DAD → SGN | 16:40 | 18:00 | Aircraft misplaced |
| 3 | 1801 | SGN → BLR | 19:20 | 22:35 | Downstream cascade |

## 5. Critical Rule — Multiple Level 1 Flights on Same Aircraft

Do not implement cascade logic in a single naive loop.

Problem:

- The same aircraft may have more than one direct Level 1 impacted sector.
- If the code only starts cascade from the first Level 1, it may incorrectly assign levels after the second direct impact.

## 6. Required Algorithm — Two-Pass Detection

### Pass 1 — Detect all Level 1 flights independently

```python
df["impact_level_numeric"] = None

df.loc[dest_affected | orig_affected, "impact_level_numeric"] = 1
```

### Pass 2 — Trace downstream by aircraft

```python
for reg, group in df.groupby("aircraft_reg"):
    sorted_group = group.sort_values("std")
    cascade_level = None

    for idx, row in sorted_group.iterrows():
        if row["impact_level_numeric"] == 1:
            cascade_level = 2
        elif cascade_level is not None:
            if row["impact_level_numeric"] is None:
                df.at[idx, "impact_level_numeric"] = cascade_level
            cascade_level += 1
```

## 7. Level 3+ Display Rule

Store actual numeric level internally, but display Level 3 and above as `3+`.

| Stored numeric level | UI display | Purpose |
|---:|---|---|
| 1 | Level 1 | Direct impact |
| 2 | Level 2 | First downstream sector |
| 3 | 3+ | Grouped downstream display |
| 4 | 3+ | Grouped downstream display |
| 5+ | 3+ | Grouped downstream display |

### Recommended implementation

```python
def display_impact_level(level: int | None) -> str:
    if level is None:
        return "Not affected"
    if level == 1:
        return "Level 1"
    if level == 2:
        return "Level 2"
    return "3+"
```

## 8. Overnight Rotation Limitation

MVP limitation:

> Cascade detection is limited to flights within the loaded report date range.

If the DayRepReport only contains flights for 24/04, the tool will not detect downstream impact on 25/04.

### Required warning in README and UI

```text
Cascade detection is limited to flights within the loaded report date range.
Overnight downstream rotations outside the loaded file are not included in MVP.
```

## 9. Audit Trail Requirement

Each affected flight should include a reason field.

Examples:

| Impact level | Reason |
|---|---|
| Level 1 | Arrival into closed airport |
| Level 1 | Departure from closed airport |
| Level 2 | Downstream aircraft rotation after Level 1 impact |
| 3+ | Extended downstream cascade |


---


# 02 — Data Parsing Strategy

## 1. Objective

Build a robust parser for real AIMS DayRepReport files.

The parser is the highest-risk component of the MVP.  
It must handle variable headers, inconsistent time formats, registration formatting issues, and footer rows.

## 2. Standard Output Schema

The parser should normalize raw AIMS columns into this canonical schema:

| Canonical field | Description |
|---|---|
| `flight_date` | Operational date |
| `flight_no` | Flight number |
| `aircraft_reg` | Aircraft registration |
| `aircraft_type` | Aircraft type |
| `origin` | Departure airport |
| `destination` | Arrival airport |
| `std` | Scheduled departure datetime/time |
| `sta` | Scheduled arrival datetime/time |
| `raw_row_number` | Original row number from Excel |
| `data_quality_warning` | Optional warning string |

## 3. Dynamic Header Detection

AIMS DayRepReport may include several title or metadata rows before the actual header row.

Do not hardcode the header row.

### Header mapping

```python
HEADER_KEYWORD_MAP = {
    "DATE": ["DATE", "DATE OPS", "FLIGHT DATE"],
    "FLT":  ["FLT", "FLT NO", "FLIGHT", "FLIGHT NO"],
    "REG":  ["REG", "REGISTRATION", "TAIL"],
    "AC":   ["AC", "ACTYPE", "AIRCRAFT TYPE", "TYPE", "A/C"],
    "DEP":  ["DEP", "FROM", "ORIGIN", "DEP STN"],
    "ARR":  ["ARR", "TO", "DEST", "ARR STN"],
    "STD":  ["STD", "SCHED DEP", "SCHEDULED DEP"],
    "STA":  ["STA", "SCHED ARR", "SCHEDULED ARR"],
}
```

### Header detection rule

The header row is the first row that matches at least 6 of 8 keyword groups.

```python
def find_header_row(df_raw):
    for i, row in df_raw.iterrows():
        row_upper = [str(v).strip().upper() for v in row]
        matched = sum(
            1
            for aliases in HEADER_KEYWORD_MAP.values()
            if any(a in row_upper for a in aliases)
        )
        if matched >= 6:
            return i
    raise ValueError("Cannot detect header row in DayRepReport")
```

## 4. Column Variants

| Field | Standard name | Common AIMS variants |
|---|---|---|
| DATE | DATE | DATE OPS, FLIGHT DATE, Date |
| FLT | FLT | FLT NO, FLIGHT, FLIGHT NO, Flt |
| REG | REG | REGISTRATION, TAIL, Tail No |
| AC | AC | ACTYPE, AIRCRAFT TYPE, TYPE, A/C |
| DEP | DEP | FROM, ORIGIN, DEP STN, Dep |
| ARR | ARR | TO, DEST, ARR STN, Arr |
| STD | STD | SCHED DEP, SCHEDULED DEP, Sch Dep |
| STA | STA | SCHED ARR, SCHEDULED ARR, Sch Arr |

## 5. Time Parsing

Time parsing is likely to be the most fragile part of the project.

### Required time formats

| Format | Example | Required handling |
|---|---|---|
| `HH:MM` | `14:35` | Parse normally |
| `HHMM` | `1435` | Add colon |
| `H:MM` | `6:05` | Zero-pad hour if needed |
| `2400` | `2400` | Treat as midnight; next-day logic handled upstream |
| Blank/null | `""` | Return `None` |
| Placeholder | `--:--` | Return `None` |
| Next-day marker | `00:00+1` | Strip `+1`, parse time, flag if needed |

### Null values

```python
NULL_TIME_VALUES = {"", "--:--", "--", "N/A", "NONE", "NULL"}
```

### Recommended implementation

```python
from datetime import time, datetime
import pandas as pd

NULL_TIME_VALUES = {"", "--:--", "--", "N/A", "NONE", "NULL"}

def parse_time_field(raw) -> time | None:
    if pd.isna(raw):
        return None

    s = str(raw).strip().upper()

    if s in NULL_TIME_VALUES:
        return None

    s = s.replace("+1", "").replace("+2", "")

    if s == "2400":
        return time(0, 0)

    if ":" not in s:
        s = s.zfill(4)
        s = f"{s[:2]}:{s[2:]}"

    try:
        return datetime.strptime(s, "%H:%M").time()
    except ValueError:
        return None
```

## 6. Aircraft Registration Normalization

Aircraft registration is critical for cascade detection.

### Problem

If aircraft registration is not normalized, the same aircraft may be treated as multiple aircraft.

| Raw AIMS value | Normalized value | Risk if not normalized |
|---|---|---|
| `VN-A500` | `VN-A500` | OK |
| `VNA500` | `VN-A500` | Split aircraft chain |
| ` VN-A500` | `VN-A500` | Split aircraft chain |
| `VN-A500 ` | `VN-A500` | Split aircraft chain |
| `vn-a500` | `VN-A500` | Wrong grouping |

### Minimum required normalization

```python
df["aircraft_reg"] = df["aircraft_reg"].str.strip().str.upper()
```

### Recommended normalization function

```python
import re

def normalize_reg(raw: str | None) -> str | None:
    if raw is None:
        return None

    s = str(raw).strip().upper()

    if not s:
        return None

    # Convert VNA500 to VN-A500
    if re.match(r"^VN[A-Z0-9]{3,5}$", s):
        s = "VN-" + s[2:]

    return s
```

## 7. Footer Row Detection

DayRepReport may contain footer rows such as:

- `Total: 358 flights`
- `Generated by AIMS v8.2`
- Empty rows after the report body

These must not create phantom flights.

### Required filters

| Strategy | Description |
|---|---|
| Date parse filter | Remove rows where DATE cannot parse as valid date |
| Flight number pattern | Remove rows where FLT does not match flight number pattern |
| Stop-at-empty | Stop load after 3 consecutive rows with no DATE and no FLT |
| REG format check | Remove rows where REG format is invalid |

### Flight number pattern

```python
FLIGHT_NO_PATTERN = r"^[0-9]{3,4}[A-Z]?$"
```

### Registration format check

```python
REG_PATTERN = r"^[A-Z]{1,2}-[A-Z0-9]{3,5}$"
```

## 8. Data Quality Warnings

Parser should not silently fail.

Recommended warning categories:

| Warning code | Meaning |
|---|---|
| `HEADER_NOT_FOUND` | Header row cannot be detected |
| `TIME_PARSE_FAILED` | STD/STA cannot be parsed |
| `REG_INVALID` | Aircraft registration invalid or missing |
| `FOOTER_ROW_SKIPPED` | Footer row removed |
| `DATE_PARSE_FAILED` | Flight date invalid |
| `DUPLICATE_FLIGHT_ROW` | Duplicate candidate detected |
| `MISSING_REQUIRED_FIELD` | Required field missing |

## 9. Parser Build Priority

Build order:

1. Load raw Excel.
2. Detect header row.
3. Rename columns to canonical schema.
4. Remove footer/non-flight rows.
5. Normalize registration.
6. Parse date/time.
7. Create canonical dataframe.
8. Emit data quality warnings.
9. Run tests against real DayRepReport files.


---


# 03 — Pilot Rollout Plan

## 1. Pilot Principle

The project should be piloted carefully to support real OCC adoption.

Do not introduce the tool as AI, optimization, or automated decision-making.

Use this framing:

> The tool is an automated AIMS report reader that reads the DayRepReport, calculates affected flights, and prepares a structured list for review.

Duty Manager remains final decision maker.

## 2. Pilot Phases Overview

| Phase | Name | Duration | Main objective |
|---:|---|---|---|
| 0 | Internal Validation | 1 week before pilot | Confirm the tool works with real AIMS data |
| 1 | Shadowing | Week 1–2 | Let OCC Controller learn workflow |
| 2 | Parallel Run | Week 3–4 | Compare tool output with real process |
| 3 | Live Pilot | Week 5–6 | Evaluate actual business value |

## 3. Phase 0 — Internal Validation

### Participants

- Developer
- AIMS PIC

No OCC end user yet.

### Objective

Validate the tool against real DayRepReport files before any OCC user handles it.

### Activities

| Activity | Details |
|---|---|
| Collect real DayRepReport files | Use 5–10 recent operational days |
| Run parser | Record errors, warnings, edge cases |
| Compare with AIMS | Validate rotation chain and affected flights |
| Fix parser edge cases | Resolve all discovered data variants |
| Validate sample KPI | Confirm expected KPI values from sample |
| Document discrepancies | Record all mismatch cases |

### Pass criteria

| Pass condition | Fail condition |
|---|---|
| Tool loads all sample DayRepReport files | Tool crashes with any real file |
| Rotation match rate > 95% | Match rate < 90% |
| Expected sample KPI is correct | KPI differs by more than 5% |
| All known time formats parse correctly | Any known time format fails |

## 4. Phase 1 — Shadowing

### Duration

Week 1–2.

### Participants

- 1 OCC Controller
- 1 AIMS PIC

No Duty Manager pressure yet.

### Activities

| Item | Details |
|---|---|
| Frequency | Daily during working days for 2 weeks |
| Main task | Load same-day DayRepReport and run hypothetical HAN closure scenario |
| Comparison | OCC Controller compares output with own operational mental model |
| Feedback | Fill 5-minute feedback form after each session |
| Process impact | No change to current operation |

### Feedback form

| Question | Scale |
|---|---|
| Can you load file and run tool by yourself? | Yes / No / Need support |
| Does output match your understanding of impact? | 1–5 |
| Is UI easy to read and understand? | 1–5 |
| What is confusing or missing? | Free text |
| Would you use this tool in real IROPS? | Yes / Maybe / No |

### Phase 1 pass criteria

- OCC Controller can run the tool without support after week 1.
- Average satisfaction score is at least 3.5/5.

## 5. Phase 2 — Parallel Run

### Duration

Week 3–4.

### Participants

- OCC Controller
- Duty Manager as observer

### Objective

Use the tool in parallel with the current AIMS/OCC process.  
The tool does not replace official decisions.

### Trigger

Use when there is a real minor delay or small disruption.

### Activities

| Item | Details |
|---|---|
| Process | OCC runs tool in parallel with existing workflow |
| Timing | Record time from disruption notice to tool output |
| Comparison | Compare tool recommendation with Duty Manager decision |
| Restriction | Tool output is not official decision basis yet |

### Metrics

| Metric | Baseline | Target |
|---|---|---|
| Time to identify affected flights | Measured in Phase 0 | < 5 minutes |
| Time to prepare Duty Manager briefing | Measured in Phase 0 | < 15 minutes |
| Tool output error vs AIMS | — | < 5% |
| Recommendation match with DM decision | — | > 70% |
| OCC Controller satisfaction | — | ≥ 4.0/5 |

### Phase 2 pass criteria

- Tool output generated in under 5 minutes.
- Duty Manager says output is useful or very useful.
- Recommendation match rate is above 70%.

## 6. Phase 3 — Live Pilot

### Duration

Week 5–6.

### Participants

- Full OCC team
- Duty Manager
- AIMS PIC / Developer support

### Rule

If real IROPS happens, use the tool as primary impact analysis support.  
If no real IROPS happens, conduct mandatory tabletop drill.

## 7. Tabletop Drill Scenario

### Scenario

HAN closure from 14:00 to 18:00 on 24/04/2026.

### Format

| Item | Duration |
|---|---:|
| Setup | 30 minutes |
| Scenario handling | 45 minutes |
| Debrief | 15 minutes |
| Total | 1.5 hours |

### Facilitator

AIMS PIC or developer facilitates.  
Duty Manager should act as the real decision maker, not facilitator.

### Script

| Time | Event | Required action |
|---|---|---|
| T+0 | Receive HAN closure notice 14:00–18:00 | Load DayRepReport and run tool |
| T+5 | Tool output is ready | OCC reviews affected flights and forwards to DM |
| T+10 | DM reviews decision list | DM approves/rejects recommendations |
| T+15 | Export Excel report | Prepare management briefing |
| T+30 | Management briefing | Use Excel output from tool |

## 8. Pilot Risks and Mitigation

| Risk | Severity | Mitigation |
|---|---|---|
| DayRepReport format changes suddenly | High | Test many real files in Phase 0; show clear header-detection error |
| Duty Manager has no time during real IROPS | Very high | Mandatory tabletop drill before live usage |
| OCC Controller does not trust output | Medium | Show audit trail: why flight X is Level 1, why Y is Level 2 |
| Scope creep during pilot | High | Limit pilot to Airport Closure only |
| Tool runs slowly with large file | Low | Performance test with 500+ rows before Phase 1 |
| User resistance due to workflow change | Medium | Frame as automated AIMS reader, not replacement for AIMS or DM judgment |


---


# 04 — Definition of Done

## 1. Priority Action List

Implementation priority is based on operational risk.

| Priority | Item | Related area | Required action |
|---:|---|---|---|
| 1 | `parse_time_field()` | Data Parsing | Write and test with all known time formats first |
| 2 | REG normalization | Data Parsing | Apply `str.strip().str.upper()` immediately after load |
| 3 | Two-pass cascade detection | Cascade Logic | Pass 1 Level 1; Pass 2 downstream |
| 4 | Boundary condition | Cascade Logic | Use exclusive end: `< closure_end` |
| 5 | `HEADER_KEYWORD_MAP` | Data Parsing | Use fuzzy/alias match, at least 6/8 groups |
| 6 | Overnight limitation warning | Cascade Logic | Show warning in README and UI |
| 7 | Phase 0 validation | Pilot | Test with 5–10 real DayRepReport files before users |

## 2. MVP Definition of Done

| Criterion | Target | Validation phase |
|---|---:|---|
| Parser handles all known time formats | 100% | Phase 0 |
| REG normalization creates no phantom aircraft | 0 known errors | Phase 0 |
| Header detection works with real DayRepReports | At least 5 files | Phase 0 |
| Expected KPI: `358/87/39/23/25/24` | 100% accurate | Phase 0 |
| OCC Controller can run tool without support | By week 2 | Phase 1 |
| OCC Controller satisfaction | ≥ 4.0/5 | Phase 1–2 |
| Tool output generated in under 5 minutes | < 5 minutes | Phase 2 |
| Recommendation matches DM decision | > 70% | Phase 2 |
| Tabletop Drill completed | 1 drill | Phase 3 |
| DM says output is useful | Yes | Phase 3 |

## 3. Engineering Done Checklist

### Parser

- [ ] Raw Excel file can be loaded.
- [ ] Dynamic header row can be detected.
- [ ] Column aliases map correctly to canonical schema.
- [ ] Footer rows are skipped.
- [ ] Invalid rows are logged as warnings.
- [ ] All required time formats are handled.
- [ ] Aircraft registration is normalized.
- [ ] Canonical dataframe is returned.
- [ ] Parser tests pass.

### Cascade detector

- [ ] Airport closure event can be configured.
- [ ] Boundary rule uses start inclusive, end exclusive.
- [ ] Arrival Level 1 detection works.
- [ ] Departure Level 1 detection works.
- [ ] Multiple Level 1 flights on same aircraft are handled.
- [ ] Downstream cascade is traced by aircraft registration.
- [ ] Numeric impact level is stored.
- [ ] UI display level maps 3 and above to `3+`.
- [ ] Reason field is generated for each affected flight.
- [ ] Cascade tests pass.

### UI / Streamlit

- [ ] User can upload DayRepReport.
- [ ] User can enter airport closure event.
- [ ] Tool displays summary KPI.
- [ ] Tool displays affected flight table.
- [ ] Tool shows data quality warnings.
- [ ] Tool shows MVP overnight limitation warning.
- [ ] User can export Excel report.

### Pilot readiness

- [ ] 5–10 real DayRepReport files tested.
- [ ] Known discrepancies documented.
- [ ] Tabletop Drill scenario prepared.
- [ ] Feedback form prepared.
- [ ] Duty Manager briefing output prepared.

## 4. Core Conclusion

The hardest part of this project is not business logic.

Cascade detection itself is relatively simple.

The real challenges are:

1. Data quality in real AIMS DayRepReport files.
2. Change management with OCC Controller and Duty Manager.
3. Building trust through audit trail and controlled pilot rollout.

Therefore:

> Invest more effort in Phase 0 validation and Tabletop Drill than in extra Streamlit features.


---


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


---


# 06 — Agent Prompt

Use this prompt when asking a coding Agent such as Codex to implement or update the project.

---

You are building an MVP named **OCC IROPS Recovery Dashboard**.

The tool supports OCC during airport closure disruptions by reading an AIMS DayRepReport, detecting directly affected flights, tracing downstream aircraft rotation cascade, and producing a structured output for OCC Controller and Duty Manager review.

## Business framing

Do not frame the product as AI or optimization.  
It is an automated AIMS report reader and impact analysis assistant.

Duty Manager remains the final decision maker.

## MVP scope

Implement only Airport Closure scenario.

Do not implement:

- aircraft recovery optimization
- crew legality
- passenger reaccommodation
- automated decision-making
- overnight rotation beyond loaded report
- live AIMS integration
- database persistence unless explicitly requested

## Input

AIMS DayRepReport Excel file.

The report may have:

- title rows before header
- variable column names
- inconsistent time format
- blank times
- `--:--`
- `2400`
- `+1` next-day marker
- footer rows
- inconsistent aircraft registration format

## Parser requirements

Create robust parser that:

1. Detects header dynamically using keyword alias mapping.
2. Requires at least 6 of 8 expected header groups.
3. Maps columns into canonical schema.
4. Removes footer and non-flight rows.
5. Normalizes aircraft registration.
6. Parses AIMS time fields.
7. Emits warnings instead of silently failing.

Canonical fields:

```text
flight_date
flight_no
aircraft_reg
aircraft_type
origin
destination
std
sta
raw_row_number
data_quality_warning
```

## Cascade logic requirements

Use airport closure boundary:

```python
time >= closure_start and time < closure_end
```

Level 1:

- arrival into closed airport, or
- departure from closed airport

Use two-pass detection:

1. Detect all Level 1 flights independently.
2. Trace downstream cascade by aircraft registration sorted by STD.

Store actual numeric level in:

```text
impact_level_numeric
```

Display:

```text
1 -> Level 1
2 -> Level 2
3 or higher -> 3+
```

Add audit reason for each affected flight.

## Required tests

Write tests for:

- all time formats
- header detection
- REG normalization
- footer filtering
- boundary condition start inclusive / end exclusive
- multiple Level 1 flights on same aircraft
- downstream cascade Level 2 and Level 3+
- non-affected aircraft

## UI requirements

Use Streamlit.

Minimum UI:

- upload DayRepReport
- airport code input
- closure date input
- closure start/end time input
- run analysis
- KPI summary
- affected flights table
- data quality warning panel
- export Excel button

Always display this warning:

```text
Cascade detection is limited to flights within the loaded report date range.
Overnight downstream rotations outside the loaded file are not included in MVP.
```

## Delivery priority

Build in this order:

1. `parse_time_field()`
2. aircraft registration normalization
3. dynamic header detection
4. DayRepReport canonical parser
5. two-pass cascade detector
6. test suite
7. Streamlit UI
8. Excel export
9. pilot documentation

## Definition of Done

The MVP is done only when:

- parser handles all known time formats
- header detection works with at least 5 real DayRepReport files
- expected KPI sample result is correct
- cascade logic passes multiple-Level-1 test
- tool output is generated under 5 minutes
- Excel export works
- warnings are visible
- tests pass

Implement the simplest reliable solution.  
Do not expand scope until MVP has passed Phase 0 validation.


---


# 07 — Test Cases and Acceptance Criteria

## 1. Time Parser Test Cases

| Raw value | Expected result | Notes |
|---|---|---|
| `14:35` | `14:35` | Standard |
| `1435` | `14:35` | HHMM |
| `6:05` | `06:05` | One-digit hour |
| `605` | `06:05` | HMM |
| `2400` | `00:00` | Midnight |
| `--:--` | `None` | Placeholder |
| `--` | `None` | Placeholder |
| `""` | `None` | Blank |
| `None` | `None` | Null |
| `00:00+1` | `00:00` | Strip next-day marker |
| `00:00+2` | `00:00` | Strip next-day marker |
| `abc` | `None` + warning | Invalid |

## 2. Boundary Condition Test Cases

Closure:

```text
Airport: HAN
Start: 14:00
End: 18:00
```

| Flight | Route | STD | STA | Expected |
|---|---|---:|---:|---|
| A | DAD → HAN | 12:40 | 13:59 | Not affected |
| B | DAD → HAN | 12:40 | 14:00 | Level 1 |
| C | DAD → HAN | 12:40 | 17:59 | Level 1 |
| D | DAD → HAN | 12:40 | 18:00 | Not affected |
| E | HAN → DAD | 14:35 | 15:55 | Level 1 |
| F | HAN → DAD | 18:00 | 19:20 | Not affected |

## 3. Multiple Level 1 on Same Aircraft

Input:

| Flight | REG | Route | STD | STA |
|---|---|---|---:|---:|
| 1504 | VN-A500 | DAD → HAN | 12:40 | 14:00 |
| 1505 | VN-A500 | HAN → DAD | 14:35 | 15:55 |
| 637 | VN-A500 | DAD → SGN | 16:40 | 18:00 |
| 1801 | VN-A500 | SGN → BLR | 19:20 | 22:35 |

Expected:

| Flight | Expected level | Reason |
|---|---:|---|
| 1504 | 1 | Arrival into closed airport |
| 1505 | 1 | Departure from closed airport |
| 637 | 2 | Downstream after Level 1 |
| 1801 | 3 | Extended downstream cascade; display `3+` |

## 4. REG Normalization Test Cases

| Raw | Expected |
|---|---|
| `VN-A500` | `VN-A500` |
| `VNA500` | `VN-A500` |
| ` VN-A500` | `VN-A500` |
| `VN-A500 ` | `VN-A500` |
| `vn-a500` | `VN-A500` |

## 5. Header Detection Test Cases

Header should be detected when row contains at least 6 of these groups:

```text
DATE, FLT, REG, AC, DEP, ARR, STD, STA
```

Test variants:

| Raw column | Canonical |
|---|---|
| `FLIGHT DATE` | DATE |
| `FLT NO` | FLT |
| `REGISTRATION` | REG |
| `TAIL` | REG |
| `AIRCRAFT TYPE` | AC |
| `FROM` | DEP |
| `TO` | ARR |
| `SCHEDULED DEP` | STD |
| `SCHEDULED ARR` | STA |

## 6. Footer Filtering Test Cases

Rows should be skipped if they contain:

| Row content | Expected action |
|---|---|
| `Total: 358 flights` | Skip |
| `Generated by AIMS v8.2` | Skip |
| Empty DATE and FLT for 3 consecutive rows | Stop reading body |
| Invalid DATE | Skip or warning |
| Invalid FLT pattern | Skip or warning |
| Invalid REG pattern | Skip or warning |

## 7. Acceptance Criteria for MVP

### Functional

- [ ] User uploads DayRepReport.
- [ ] Parser detects header dynamically.
- [ ] Parser returns canonical dataframe.
- [ ] Cascade detector assigns impact level.
- [ ] UI shows affected flights.
- [ ] UI shows warnings.
- [ ] Excel export works.

### Operational

- [ ] Tool can process 5–10 real DayRepReport files.
- [ ] Output is explainable to OCC Controller.
- [ ] Duty Manager can review Excel output.
- [ ] Tool does not replace Duty Manager decision.

### Performance

- [ ] Tool processes report within 5 minutes.
- [ ] Performance test uses at least 500 rows.

### Pilot

- [ ] Phase 0 validation completed.
- [ ] Phase 1 Shadowing completed.
- [ ] Phase 2 Parallel Run completed or planned.
- [ ] Phase 3 Tabletop Drill completed if no real IROPS occurs.
