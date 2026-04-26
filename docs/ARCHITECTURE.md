# Technical Architecture
## OCC IROPS Recovery Dashboard

| Field | Value |
|---|---|
| Document version | 1.0 |
| Status | Reflects code at end of Sprint 7 + cumulative merge (PR #9) |
| Owner | Developer (Code Agent) |
| Last updated | 26/04/2026 |
| Related docs | [BRD](./BRD.md) · [PRD](./PRD.md) · [Pilot Run Book](./PILOT_RUN_BOOK.md) · [Production Deploy](./PRODUCTION_DEPLOY.md) |

---

## 1. System Context

```
                    ┌────────────────────────┐
                    │  AIMS (system of       │
                    │  record — unchanged)   │
                    └───────────┬────────────┘
                                │ exports DayRepReport (.xlsx) on demand
                                ▼
   ┌─────────────────┐  ┌─────────────────────────────────────────┐
   │ DM / Controller │──│  OCC IROPS Recovery Dashboard           │
   │  (browser)      │  │  (Streamlit + SQLite + Python core)     │
   └─────────────────┘  └────┬───────────────────────────┬────────┘
                              │ outputs                   │ outputs
                              ▼                           ▼
                    ┌─────────────────┐         ┌─────────────────────┐
                    │ Excel / PDF     │         │ Teams webhook /     │
                    │ briefing        │         │ scheduled email     │
                    └─────────────────┘         └─────────────────────┘
```

The product is a **single-tenant, single-process Streamlit application** with a small SQLite store for runs and audit logs. It does not call external services unless the operator opts into Sprint 6 integrations (Teams webhook, scheduled briefing CLI, folder watcher).

## 2. Module Layout

```
occ-irops-recovery-dashboard/
├── app.py                          ← Streamlit entry point (UI orchestrator)
├── src/
│   ├── auth/
│   │   └── users.py                ← yaml-file users + bcrypt; OCC_AUTH_DISABLED
│   ├── cascade/
│   │   ├── cascade_detector.py     ← two-pass cascade (single + multi event)
│   │   └── ranking.py              ← priority score
│   ├── decision/
│   │   ├── recovery.py             ← Sprint 7 recovery options (delay/swap/cancel)
│   │   ├── reaccommodation.py      ← Sprint 7 pax reaccom ranking
│   │   └── stress.py               ← Sprint 7 multi-day stress test
│   ├── export/
│   │   ├── excel_exporter.py       ← 5-sheet workbook
│   │   └── pdf_briefing.py         ← reportlab 1-page PDF
│   ├── i18n/
│   │   └── translator.py           ← yaml-driven VN/EN locale toggle
│   ├── impact/
│   │   └── pax_estimator.py        ← est_pax + est_cost_usd
│   ├── integration/
│   │   ├── alerts.py               ← Teams webhook alert engine
│   │   ├── briefing.py             ← scheduled morning briefing helper
│   │   ├── cli.py                  ← entry points for cron / scheduler
│   │   └── watcher.py              ← folder watcher (drop-in inbox)
│   ├── models/
│   │   └── event.py                ← AirportClosureEvent dataclass
│   ├── parser/
│   │   ├── dayrep_parser.py        ← AIMS DayRepReport reader
│   │   ├── multi_file.py           ← multi-file concatenation
│   │   └── time_parser.py          ← parse_time_field
│   ├── persistence/
│   │   ├── audit.py                ← audit_events table
│   │   ├── db.py                   ← SQLite connection + init_db
│   │   ├── runs.py                 ← runs table (history)
│   │   └── settings.py             ← settings table (load factor, capacity)
│   ├── validation/
│   │   └── validator.py            ← predicted-vs-actuals confusion matrix
│   ├── visualization/
│   │   ├── airport_coords.py       ← built-in 35+ airport coordinate table
│   │   ├── gantt.py                ← Plotly rotation chart
│   │   └── map_view.py             ← Plotly scattergeo network map
│   ├── config.py                   ← canonical schema + regex constants
│   └── logging_config.py           ← stdlib JSON formatter + setup_logging
├── tests/                          ← 203 tests (pytest)
├── locales/{vi,en}.yaml            ← UI translations
├── config/users.example.yaml       ← auth template (real users.yaml is gitignored)
├── data/sample/                    ← sample DayRepReport for demo / tests
├── docs/                           ← BRD, PRD, Architecture, Run Book, etc.
├── memory-bank/                    ← Agent knowledge base
├── docker-compose.yml              ← single-service deployment
├── Dockerfile                      ← non-root, healthcheck-friendly
├── pyproject.toml                  ← ruff / black / mypy / pytest config
├── requirements.txt                ← runtime deps
├── requirements-dev.txt            ← lint / test / type deps
└── .pre-commit-config.yaml         ← pre-commit hooks
```

## 3. Data Flow

### 3.1 Happy path — single closure on a single day

```
DayRepReport.xlsx (uploaded)
  │
  ▼
src/parser/dayrep_parser.py::parse_dayrep_report
  │  (alias header map → canonical schema; REG / time normalisation)
  │  emits row-level data_quality_warning where applicable
  ▼
src/parser/multi_file.py::parse_multiple_dayrep_reports
  │  (concat + warning prefix file#N:)
  ▼
DataFrame with canonical columns
  │
  ▼
src/cascade/cascade_detector.py::detect_cascade_multi
  │  Pass 1 — union of L1 masks across events
  │  Pass 2 — single rotation trace over merged L1 set, sorted by (flight_date, std)
  │  emits internal numeric `level`, `cascade_depth`, `impact_explanation`
  ▼
src/cascade/ranking.py::compute_priority
  │  priority_score = level_base + cascade_depth × 10 + intl_bonus
  ▼
src/impact/pax_estimator.py::estimate_pax_and_cost
  │  est_pax = capacity[type] × load_factor
  │  est_cost_usd = est_pax × delay_min × cost_per_pax_min
  ▼
src/cascade/cascade_detector.py::compute_kpis
  │  total / level counts / aircraft / pax / cost
  ▼
Streamlit UI:
  • KPI bar
  • Top-10 highlight cards (pax / cost / depth)
  • Affected table (with explainer + warnings)
  • Plotly Gantt rotation chart
  • Plotly scattergeo network map
  • What-if simulator (re-runs detect_cascade_multi against alt window)
  • Decision support expander → recovery.py + reaccommodation.py
  • Network stress test expander → stress.py
  │
  ▼
Excel / PDF / SQLite persistence (run + audit) / optional Teams alert
```

### 3.2 Multi-event union (Sprint 3)

```
events = [HAN closed 14:00–18:00, HPH ATC flow 14:00–18:00]
  │
  ▼
Pass 1 (per event): mask_event_i = is_l1(df, event_i)
union_l1_mask = OR(mask_event_i for all events)
  │
  ▼
Pass 2: walk rotation chains starting from union_l1_mask
no double-counting because Pass 2 runs once on merged L1
  │
  ▼
impact_explanation lists every event that triggered each L1 row
```

### 3.3 What-if (Sprint 2)

```
result_baseline = detect_cascade_multi(df, events_baseline)
result_whatif   = detect_cascade_multi(df, events_whatif)

newly_affected   = whatif_affected - baseline_affected
no_longer_aff    = baseline_affected - whatif_affected
unchanged        = baseline_affected ∩ whatif_affected
```

### 3.4 Recovery scoring (Sprint 7)

```
For each L1 root:
  delay      = (pax × cost_per_pax_min × default_delay_min) + 0
  swap_tail  = (pax × cost_per_pax_min × swap_overhead)     + (1 × w_op)
  cancel     = (pax × cancel_penalty)                        + (3 × w_op)

score = w_pax × pax + w_cost × cost + w_op × op_penalty
op_penalty = {delay: 0, swap_tail: 1, cancel: 3}
defaults   = {w_pax: 1.0, w_cost: 0.5, w_op: 100.0}

swap_to: first free aircraft on the same day (no overlap).
If no free tail exists, swap_tail row is omitted (table size <153 expected).
```

## 4. Domain Model

```
AirportClosureEvent  (src/models/event.py)
  airport: str
  closure_date: date
  start_time: time
  end_time: time
  closure_type: Literal["airport_closed", "runway_closed", "atc_flow"]
```

Canonical flight schema (output of parser):

```
flight_date          date
flight_no            str
aircraft_reg         str    (canonical: "VN-A517")
aircraft_type        str    (e.g. "A321", "B787")
origin               str    (IATA code)
destination          str
std                  time
sta                  time
data_quality_warning str    (free text, may be empty)
```

After cascade detection, additional columns are appended:

```
level                int    (0=unaffected, 1=direct, 2..N=downstream)
cascade_depth        int
priority_score       float
impact_explanation   str
est_pax              int
est_cost_usd         float
```

## 5. Persistence

SQLite database at `data/runs.db` (mounted volume in Docker).

| Table | Columns | Purpose |
|---|---|---|
| `runs` | `id, user, ts, file_hashes (json), event_config (json), kpis (json)` | History dropdown, "compare with last 7 days" |
| `settings` | `key, value, updated_by, updated_at` | DM-editable load factor / cost rate / capacity table |
| `audit_events` | `ts, user, action, payload (json)` | Login / run / settings / export trail |

Schema is **additive only** — no migrations. New columns added as JSON blobs inside `kpis` / `event_config`.

## 6. Auth

| Component | Mechanism |
|---|---|
| User store | `config/users.yaml` (gitignored). Template at `config/users.example.yaml`. |
| Hashing | bcrypt via `streamlit-authenticator`. |
| Roles | `dm` (full access), `viewer` (run + view, no settings / audit). |
| Bypass | `OCC_AUTH_DISABLED=1` env var, **only honoured if explicitly set**. UI shows amber banner. |
| Logout | sidebar logout button clears `st.session_state` and authenticator cookie. |

## 7. Observability

- **Structured logs**: `src/logging_config.py` emits one JSON line per event to stdout (Docker captures it). Events: `upload_received`, `parse_completed`, `cascade_completed`, `whatif_completed`, `validation_completed`, `persistence_failed`, etc.
- **Audit log**: every login, run, settings change and export written to `audit_events`. CSV downloadable from the DM-only Audit log expander.
- **Healthcheck**: Streamlit's built-in `/_stcore/health` endpoint returns `ok`. Used by Docker compose healthcheck and external probes.
- **Performance log**: Sprint 4 perf benchmark captured in `tests/test_performance.py`; budget < 10 s on synthetic 5,000-flight × 3-day × 5-event input.

## 8. Deployment

### 8.1 Local dev

```
git clone https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard.git
cd occ-irops-recovery-dashboard
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
OCC_AUTH_DISABLED=1 streamlit run app.py
```

### 8.2 Docker (production-ish)

```
docker compose up --build
```

- Single service `app`.
- Named volume `occ_irops_dashboard_data` mounts at `/app/data` (holds `runs.db`).
- Healthcheck polls `/_stcore/health` every 30 s.
- Container runs as non-root user (UID 1000).

### 8.3 Production deploy notes

See [docs/PRODUCTION_DEPLOY.md](./PRODUCTION_DEPLOY.md). Highlights:

- Generate bcrypt hashes for `config/users.yaml` (instructions in deploy doc).
- Front with nginx + TLS (sample config in deploy doc).
- Back up `data/runs.db` daily.
- Optional: configure `OCC_TEAMS_WEBHOOK_URL`, `OCC_FOLDER_WATCH_DIR`, `OCC_BRIEFING_SCHEDULE_CRON` to enable Sprint 6 integrations.

## 9. CI / CD

`.github/workflows/ci.yml`:

| Job | Python | Steps |
|---|---|---|
| `lint` | 3.11 | `ruff check`, `ruff format --check`, `mypy src` |
| `test` | 3.10 / 3.11 / 3.12 (matrix) | `pytest tests/ -q` |

All four jobs must be green for the PR to be considered ready. End-to-end UI tests are run **manually per sprint** by the Devin agent and attached to the PR (recording + report).

## 10. Coding Conventions

- **Type hints everywhere in `src/`.** `mypy src` is gated in CI.
- **Ruff is the formatter and linter.** No black; `ruff format` is the canonical formatter.
- **Tests live in `tests/`.** One file per source module where practical (`test_parser_*.py`, `test_cascade_*.py`, `test_recovery.py`, etc.).
- **Adversarial test data**. Most tests use small synthetic frames whose expected KPIs are computed by hand and asserted exactly (e.g. `swap_tail.score == 1498.0`). This catches regressions that aggregate-only assertions would miss.
- **No `Any`, `getattr`, or duck-typing in production code**. Where dynamic access is unavoidable (e.g. settings JSON), an explicit `cast` + comment.
- **Streamlit state**: any UI element that should survive widget interactions inside the result block must be persisted in `st.session_state`. See [docs/PRODUCTION_DEPLOY.md](./PRODUCTION_DEPLOY.md) and Sprint 7 fix `d185b11`.

## 11. Known Limitations

See [docs/known_limitations.md](./known_limitations.md). Headline items:

- No live AIMS integration (folder watcher only).
- Pax / cost numbers are estimates until Phase 2 actuals collected.
- Recovery options ignore crew duty legality (Sprint 9 future).
- Validation dashboard requires DM to upload `actuals.csv` manually.

## 12. Change Log (Architecture-Affecting)

| Date | Sprint / PR | Change |
|---|---|---|
| 26/04/2026 | Sprint 1 / #2 | Bug `affected` fixed; pyproject + pre-commit + ruff + mypy; structured logging. |
| 26/04/2026 | Sprint 2 / #3 | Multi-file parsing; overnight cascade Pass 1 closure-date filter + Pass 2 (flight_date, std) sort; Plotly Gantt. |
| 26/04/2026 | Sprint 3 / #4 | `detect_cascade_multi` (union-of-masks); pax/cost estimator; PDF briefing; map view. |
| 26/04/2026 | Sprint 4 / #5 | Discrepancy explainer; parser hardening (VN headers, REG, time variants); validation module. |
| 26/04/2026 | Sprint 5 / #6 | SQLite persistence (runs / settings / audit); auth; Docker compose. |
| 26/04/2026 | Sprint 6 / #7 | i18n module; folder watcher; alerts; scheduled briefing CLI. |
| 26/04/2026 | Sprint 7 / #8 | Decision module (recovery / reaccommodation / stress); state-loss fix in `app.py`. |
| 26/04/2026 | PR #9 | Cumulative merge of Sprints 2–7 to default branch + Python 3.13 LogRecord field rename. |
