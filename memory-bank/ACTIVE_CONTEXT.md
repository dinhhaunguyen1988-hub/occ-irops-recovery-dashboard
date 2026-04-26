# Active Context — OCC IROPS Recovery Dashboard

> This file tracks the current state of the project for any agent or developer resuming work.

## Current Status

**Phase:** MVP Development Complete — Ready for Phase 0 Validation

## What Has Been Built

### Core Modules (All Complete)

| Module | File | Status |
|---|---|---|
| Time Parser | `src/parser/time_parser.py` | Complete — handles HH:MM, HHMM, H:MM, 2400, --:--, +1/+2, null |
| DayRepReport Parser | `src/parser/dayrep_parser.py` | Complete — dynamic header, column alias, footer filter, REG normalize |
| Cascade Detector | `src/cascade/cascade_detector.py` | Complete — two-pass, boundary rule, audit trail |
| Excel Exporter | `src/export/excel_exporter.py` | Complete — 5 sheets (Params, KPI, Affected, All, Warnings) |
| Event Model | `src/models/event.py` | Complete — AirportClosureEvent dataclass |
| Config | `src/config.py` | Complete — constants, patterns, keyword maps |
| Streamlit UI | `app.py` | Complete — sidebar input, KPI cards, tables, rotation view, export |

### Test Suite

| Test File | Tests | Status |
|---|---|---|
| `tests/test_time_parser.py` | 21 tests | All passing |
| `tests/test_dayrep_parser.py` | 12 tests | All passing |
| `tests/test_cascade_detector.py` | 23 tests | All passing |
| **Total** | **56 tests** | **All passing** |

### Documentation

| Document | Path | Status |
|---|---|---|
| README | `README.md` | Complete |
| User Guide | `docs/user_guide.md` | Complete |
| Known Limitations | `docs/known_limitations.md` | Complete |
| Pilot Plan | `docs/pilot_plan.md` | Complete |
| Feedback Form | `docs/feedback_form.md` | Complete |
| Tabletop Drill Script | `docs/tabletop_drill.md` | Complete |
| Phase 0 Validation | `docs/phase0_validation.md` | Complete |

### Sample Data

| File | Path | Status |
|---|---|---|
| Sample Generator | `data/sample/generate_sample_dayrep.py` | Complete |
| Sample DayRepReport | `data/sample/sample_dayrep_24042026.xlsx` | Generated — 358 flights |

## What Needs to Happen Next

### Immediate (Phase 0)

1. Collect 5–10 real AIMS DayRepReport files from AIMS PIC
2. Run Phase 0 validation with real data (see `docs/phase0_validation.md`)
3. Fix any parser edge cases discovered with real data
4. Validate KPI accuracy against manual count

### After Phase 0

1. Phase 1 — Shadowing (Week 1–2)
2. Phase 2 — Parallel Run (Week 3–4)
3. Phase 3 — Live Pilot / Tabletop Drill (Week 5–6)

## Key Decisions Made

1. **Boundary rule:** Start inclusive, end exclusive (`time >= start AND time < end`)
2. **Two-pass algorithm:** Pass 1 detects all Level 1 independently, Pass 2 traces downstream
3. **Display rule:** Level 3 and above shown as "3+" in UI
4. **No overnight cascade:** MVP limited to loaded report date range
5. **No optimization:** Tool is an analysis assistant, not a decision maker

## Known Risks

1. Real DayRepReport may have unexpected format variations not covered by parser
2. Time parsing edge cases may exist beyond the tested formats
3. Aircraft registration formats outside VN-prefix pattern need handling
4. Large files (>1000 flights) performance not yet validated with real data
