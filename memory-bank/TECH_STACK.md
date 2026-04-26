# Tech Stack — OCC IROPS Recovery Dashboard

> Updated end of Sprint 7 (cumulative merge PR #9).

## Language & Runtime

- **Python 3.10+** (CI matrix: 3.10 / 3.11 / 3.12; runs cleanly on 3.13 after PR #9 LogRecord fix).

## Runtime Dependencies (`requirements.txt`)

| Package | Version | Purpose | Sprint introduced |
|---|---|---|---|
| `streamlit` | `>=1.30.0,<1.41.0` | Dashboard UI | MVP |
| `pandas` | `>=2.0.0` | Data manipulation | MVP |
| `openpyxl` | `>=3.1.0` | Excel reader | MVP |
| `xlsxwriter` | `>=3.1.0` | Excel writer (5-sheet workbook) | MVP |
| `plotly` | `>=5.20.0` | Gantt rotation chart + scattergeo map | Sprint 2 / Sprint 3 |
| `reportlab` | `>=4.0.0` | 1-page PDF briefing | Sprint 3 |
| `streamlit-authenticator` | `>=0.3.2,<0.4` | yaml-file users + bcrypt cookies | Sprint 5 |
| `PyYAML` | `>=6.0` | Locales + users.yaml | Sprint 5 / Sprint 6 |
| `bcrypt` | `>=4.0.0` | Password hashing | Sprint 5 |
| `pytest` | `>=7.0.0` | Test framework (pinned in runtime to keep dev/prod parity) | Sprint 1 |

## Dev Dependencies (`requirements-dev.txt`)

| Package | Purpose | Sprint introduced |
|---|---|---|
| `ruff` | Linter + formatter (also runs `ruff format` as canonical formatter) | Sprint 1 |
| `black` | Kept for editor compatibility (`ruff format` is authoritative) | Sprint 1 |
| `mypy` | Static type checker (CI gate on `src/`) | Sprint 1 |
| `pre-commit` | Local pre-commit hook runner | Sprint 1 |
| `pandas-stubs` | Type stubs for `pandas` | Sprint 1 |
| `types-openpyxl` | Type stubs for `openpyxl` | Sprint 1 |
| `types-PyYAML` | Type stubs for `PyYAML` | Sprint 5 |

## Architecture Diagram

```
Input
  ┌────────────────────────────────────────────┐
  │ AIMS DayRepReport(s) (.xlsx)               │
  │ (single or multi-day, multi-file)          │
  └────────────────────┬───────────────────────┘
                       ▼
                src/parser/
                  dayrep_parser.py + multi_file.py + time_parser.py
                       ▼
                Canonical DataFrame
                       ▼
                src/cascade/
                  cascade_detector.py (Pass 1 union, Pass 2 rotation) +
                  ranking.py (priority score)
                       ▼
                src/impact/pax_estimator.py (est_pax + est_cost_usd)
                       ▼
                ┌────────────────┐  ┌────────────────────────────┐
                │ Streamlit UI   │  │ Excel / PDF / SQLite       │
                │ (KPIs, Gantt,  │  │ (history + settings +      │
                │  Map, Top-10,  │  │  audit log + briefing)     │
                │  Decision      │  └────────────────────────────┘
                │  support,      │
                │  Stress test,  │
                │  Validation,   │
                │  i18n VN/EN)   │
                └────────────────┘
```

## Key Design Patterns

1. **Canonical schema** — all raw AIMS columns normalised to standard names; alias map covers VN-accented headers in NFC + NFD.
2. **Two-pass cascade detection** — Pass 1 union of L1 masks across events (closure-date filtered); Pass 2 single rotation walk over the merged L1 set, sorted by `(flight_date, std)`.
3. **Multi-event union, single Pass 2** — never run Pass 2 per-event; double-counts downstream sectors.
4. **Closure type cosmetic** — `airport_closed / runway_closed / atc_flow` is a label and a colour; never a logic branch.
5. **Warning accumulation** — parser never silently fails. Row-level `data_quality_warning` flows from parser → table → Excel export.
6. **Stateful sessions** — `st.session_state["analysis_active"]` is the source of truth for "should the result page render," decoupled from the one-shot Run Analysis button.
7. **Separation of concerns** — parser / cascade / impact / decision / export / persistence / auth / integration / visualization / i18n are independent modules.
8. **Adversarial test data** — exact numeric KPI assertions over aggregate-only assertions.
9. **Estimates labelled** — every estimated number rendered to UI is suffixed `(est.)`.
10. **Suggestion only** — recovery options / reaccommodation / stress test are always labelled "Suggestion only — Duty Manager decides."

## File Layout (post-Sprint 7)

```
src/
├── auth/users.py
├── cascade/cascade_detector.py + ranking.py
├── decision/recovery.py + reaccommodation.py + stress.py
├── export/excel_exporter.py + pdf_briefing.py
├── i18n/translator.py
├── impact/pax_estimator.py
├── integration/watcher.py + alerts.py + briefing.py + cli.py
├── models/event.py
├── parser/dayrep_parser.py + multi_file.py + time_parser.py
├── persistence/db.py + runs.py + audit.py + settings.py
├── validation/validator.py
├── visualization/airport_coords.py + gantt.py + map_view.py
├── config.py
└── logging_config.py

app.py                              ← Streamlit entry point
locales/{vi,en}.yaml                ← UI translations
config/users.example.yaml           ← auth template
data/sample/                        ← sample DayRepReport
docker-compose.yml + Dockerfile     ← deployment
docs/                               ← BRD, PRD, Architecture, Run Book, etc.
memory-bank/                        ← Agent knowledge base
tests/                              ← 203 tests
```

## CI Configuration

`.github/workflows/ci.yml`:

| Job | Python | Steps | Gate |
|---|---|---|---|
| `lint` | 3.11 | `ruff check`, `ruff format --check`, `mypy src` | Must pass |
| `test` | 3.10 / 3.11 / 3.12 (matrix) | `pytest tests/ -q` | All three must pass |

A PR is considered ready when all 4 jobs are green.

## Performance Budget

| Scenario | Budget | Local result |
|---|---|---|
| Cascade on 5,000 flights × 3 days × 5 events | < 10 s | 1.56 s |
| UI initial render of result page on sample | < 2 s | observed |
