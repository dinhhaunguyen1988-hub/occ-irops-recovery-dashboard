# Active Context — OCC IROPS Recovery Dashboard

> Use this file to know the **current state** of the project at any point. Updated at end of every sprint.

## Current Phase

**Sprints 1 → 7 delivered. Cumulative merge to default branch complete (PR #9). Pilot-ready (Phase 0 acceptance gates pending).**

## Default Branch

`devin/1777174450-occ-irops-dashboard` — contains all features from Sprints 1 → 7 plus the Python 3.13 LogRecord fix.

## Test Status

- **203 / 203 passing** on Python 3.10, 3.11, 3.12.
- Lint: `ruff check`, `ruff format --check`, `mypy src` — all clean.
- Performance: cascade on 5,000 flights × 3 days × 5 events: 1.56 s (budget 10 s).

## What Has Been Built

### Core modules
| Module | File | Status |
|---|---|---|
| Time Parser | `src/parser/time_parser.py` | Sprint 4 hardening complete |
| DayRepReport Parser | `src/parser/dayrep_parser.py` | Sprint 4 hardening complete |
| Multi-file Parser | `src/parser/multi_file.py` | Sprint 2 |
| Cascade Detector | `src/cascade/cascade_detector.py` | Sprint 3 multi-event + Sprint 4 explainer |
| Priority Ranking | `src/cascade/ranking.py` | Sprint 2 |
| Pax / Cost Estimator | `src/impact/pax_estimator.py` | Sprint 3 |
| Recovery Options | `src/decision/recovery.py` | Sprint 7 |
| Pax Reaccommodation | `src/decision/reaccommodation.py` | Sprint 7 |
| Network Stress Test | `src/decision/stress.py` | Sprint 7 |
| Excel Exporter | `src/export/excel_exporter.py` | Sprint 4 columns |
| PDF Briefing | `src/export/pdf_briefing.py` | Sprint 3 |
| Plotly Gantt | `src/visualization/gantt.py` | Sprint 2 |
| Plotly Map | `src/visualization/map_view.py` | Sprint 3 |
| Auth | `src/auth/users.py` | Sprint 5 |
| SQLite Persistence | `src/persistence/{db,runs,audit,settings}.py` | Sprint 5 |
| i18n | `src/i18n/translator.py` + `locales/{vi,en}.yaml` | Sprint 6 |
| Folder Watcher | `src/integration/watcher.py` | Sprint 6 |
| Alert Engine | `src/integration/alerts.py` | Sprint 6 |
| Scheduled Briefing | `src/integration/briefing.py` + `cli.py` | Sprint 6 |
| Validation | `src/validation/validator.py` | Sprint 4 |
| Structured Logging | `src/logging_config.py` | Sprint 1 |
| Streamlit App | `app.py` | Sprint 7 + state-loss fix |

### Documentation
| File | Status |
|---|---|
| `docs/BRD.md` | New (this commit) |
| `docs/PRD.md` | New (this commit) |
| `docs/ARCHITECTURE.md` | New (this commit) |
| `docs/PILOT_RUN_BOOK.md` | Sprint 4 |
| `docs/PRODUCTION_DEPLOY.md` | Sprint 5 |
| `docs/known_limitations.md` | Existing |
| `docs/phase0_validation.md` | Existing |
| `docs/pilot_plan.md` | Existing |
| `docs/tabletop_drill.md` | Existing |
| `docs/feedback_form.md` | Existing |
| `docs/user_guide.md` | Existing |

### Memory bank
| File | Status |
|---|---|
| `00_PROJECT_CONTEXT.md` | Refreshed (this commit) |
| `01_CASCADE_DETECTION_LOGIC.md` | Existing — still valid; multi-event addition documented in `08_SPRINT_HISTORY.md` |
| `02_DATA_PARSING_STRATEGY.md` | Existing — still valid; Sprint 4 hardening documented in `08_SPRINT_HISTORY.md` |
| `03_PILOT_ROLLOUT_PLAN.md` | Existing — superseded operationally by `docs/PILOT_RUN_BOOK.md` |
| `04_DEFINITION_OF_DONE.md` | Refreshed with real KPIs (this commit) |
| `05_AGENT_IMPLEMENTATION_GUIDE.md` | Existing |
| `06_AGENT_PROMPT.md` | Existing |
| `07_TEST_CASES_AND_ACCEPTANCE.md` | Existing |
| `08_SPRINT_HISTORY.md` | New (this commit) |
| `09_LESSONS_LEARNED.md` | New (this commit) |
| `99_MASTER_AGENT_CONTEXT.md` | Existing — to be regenerated when adopting Sprint 8+ |
| `ACTIVE_CONTEXT.md` | This file |
| `PROGRESS.md` | Refreshed (this commit) |
| `TECH_STACK.md` | Refreshed (this commit) |
| `README.md` | Refreshed (this commit) |

## Open Items

| Item | Owner | Block on |
|---|---|---|
| Sprint 4b — real-AIMS fixture validation | Developer | 5–10 sanitised real DayRepReport files from AIMS PIC |
| Phase 0 acceptance gates | AIMS PIC | Sprint 4b |
| Phase 1 shadowing | OCC Controller | Phase 0 sign-off |
| Sprint 8 — live AIMS integration | Developer | IT credentials (SFTP / API) |
| Sprint 9 — crew FDP | Developer | Duty-time data source |
| Sprint 10 — NOTAM auto-fetch | Developer | Official VATM / ICAO endpoint |
| Sprint 11 — ML cancel-probability | Developer | ≥ 1 month historical actuals |
| Sprint 12 — SSO / OIDC | IT Security | Corporate IdP availability |

## How to Resume Work

If you (a future agent or developer) are picking this up:

1. Read [docs/BRD.md](../docs/BRD.md) for business context, [docs/PRD.md](../docs/PRD.md) for product spec, [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) for technical layout.
2. Read [08_SPRINT_HISTORY.md](./08_SPRINT_HISTORY.md) for what was done and why.
3. Read [09_LESSONS_LEARNED.md](./09_LESSONS_LEARNED.md) for engineering patterns to follow and anti-patterns to avoid.
4. Validate environment: `pytest tests/ -q` should report **203 passing**. `OCC_AUTH_DISABLED=1 streamlit run app.py` should render the dashboard at `http://localhost:8501`.
5. Run the baseline scenario (HAN 14:00–18:00 / 2026-04-24 on `data/sample/sample_dayrep_24042026.xlsx`) and confirm KPI = `358 / 139 / 51 / 41 / 47 / 26`, pax `27,827`, cost `$1,898,730`. Any deviation means a regression — stop and investigate.
6. When starting a new sprint, follow the procedure in [09_LESSONS_LEARNED.md §14](./09_LESSONS_LEARNED.md#14-process--what-to-do-at-the-start-of-every-sprint).
