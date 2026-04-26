# OCC IROPS Recovery Dashboard

> An automated AIMS report reader that reads the AIMS DayRepReport, calculates the impact structure, and prepares a review list for OCC.

## Overview

This tool supports OCC during airport closure disruptions by:

1. Reading an AIMS DayRepReport (Excel)
2. Detecting directly affected flights (Level 1)
3. Tracing downstream aircraft rotation cascade (Level 2, 3+)
4. Producing a structured output for OCC Controller and Duty Manager review
5. Exporting an Excel report for management briefing

**The Duty Manager remains the final decision maker.**

## MVP Limitation

```
Cascade detection is limited to flights within the loaded report date range.
Overnight downstream rotations outside the loaded file are not included in MVP.
```

## Quick Start

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
pip install -r requirements.txt
```

### Run the Dashboard

```bash
streamlit run app.py
```

### Run Tests

```bash
python -m pytest tests/ -v
```

## Project Structure

```
occ-irops-recovery-dashboard/
├── README.md
├── requirements.txt
├── app.py                          # Streamlit UI
├── src/
│   ├── config.py                   # Global configuration
│   ├── parser/
│   │   ├── time_parser.py          # AIMS time field parser
│   │   └── dayrep_parser.py        # DayRepReport Excel parser
│   ├── cascade/
│   │   └── cascade_detector.py     # Two-pass cascade detection
│   ├── export/
│   │   └── excel_exporter.py       # Excel report export
│   └── models/
│       └── event.py                # Airport closure event model
├── tests/
│   ├── test_time_parser.py
│   ├── test_dayrep_parser.py
│   └── test_cascade_detector.py
├── memory-bank/                    # Project knowledge base
│   ├── README.md
│   ├── 00_PROJECT_CONTEXT.md
│   ├── 01_CASCADE_DETECTION_LOGIC.md
│   ├── 02_DATA_PARSING_STRATEGY.md
│   ├── 03_PILOT_ROLLOUT_PLAN.md
│   ├── 04_DEFINITION_OF_DONE.md
│   ├── 05_AGENT_IMPLEMENTATION_GUIDE.md
│   ├── 06_AGENT_PROMPT.md
│   ├── 07_TEST_CASES_AND_ACCEPTANCE.md
│   └── 99_MASTER_AGENT_CONTEXT.md
├── docs/
│   ├── pilot_plan.md
│   ├── known_limitations.md
│   └── user_guide.md
└── data/
    ├── sample/
    └── real_validation/
```

## MVP Scenario

| Item | Value |
|---|---|
| Airport | HAN |
| Closure start | 14:00 |
| Closure end | 18:00 |
| Date | 24/04/2026 |
| Boundary logic | Start inclusive, end exclusive |

## Cascade Detection Logic

- **Level 1**: Flight directly affected (arrival into or departure from closed airport)
- **Level 2**: First downstream sector on same aircraft after Level 1 impact
- **Level 3+**: Extended downstream cascade (displayed as "3+")

Two-pass algorithm ensures multiple Level 1 flights on the same aircraft are handled correctly.

## Users and Roles

| Role | Responsibility |
|---|---|
| Developer / Code Agent | Build parser, cascade detector, UI, export, tests |
| AIMS PIC | Provide real DayRepReport, validate AIMS logic, coordinate pilot |
| OCC Controller | Run tool, review output, compare with operational understanding |
| Duty Manager | Use output as briefing input and make final operational decisions |

## Important Notes

- This tool is **not** AI decision-making or automatic aircraft recovery
- This tool does **not** replace AIMS, OCC Controller, or Duty Manager judgment
- MVP scope is limited to **Airport Closure** scenario only
