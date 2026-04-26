# Product Requirements Document (PRD)
## OCC IROPS Recovery Dashboard

| Field | Value |
|---|---|
| Document version | 1.0 |
| Status | Sprints 1–7 delivered; pilot-ready |
| Owner | Developer (Code Agent) + AIMS PIC |
| Last updated | 26/04/2026 |
| Related docs | [BRD](./BRD.md) · [Architecture](./ARCHITECTURE.md) · [Pilot Run Book](./PILOT_RUN_BOOK.md) |

---

## 1. Product Overview

### 1.1 Vision

A single Streamlit dashboard that gives Vietnam Airlines OCC a **structured, auditable, second-by-second view** of who is affected when an airport closes, how bad the cascade is going to be, what the recovery options look like, and what it will cost — without changing the AIMS workflow upstream.

### 1.2 Positioning statement

> For **OCC Duty Managers and Controllers** who **today read the AIMS DayRepReport manually under time pressure during IROPS**, the **OCC IROPS Recovery Dashboard** is an **automated AIMS report reader** that **identifies affected flights, traces aircraft rotation cascades, quantifies pax/cost impact, and ranks recovery options in seconds**. Unlike **manual Excel filtering or paper printouts**, this product **never modifies AIMS, never claims to make decisions, and keeps the Duty Manager as the final authority** while providing a verifiable audit trail of every analysis.

### 1.3 Anti-positioning (what this is NOT)

- Not an "AI" or "ML decision engine."
- Not an automatic recovery executor.
- Not a replacement for AIMS or for the Duty Manager.
- Not a SaaS — single-tenant only, deployed inside the airline's perimeter.
- Not a real-time AIMS feed (today). The bridge is folder watcher + manual upload; live API is a future sprint.

## 2. Personas

### 2.1 Duty Manager — *Mr. Phong* (primary)

- 20+ years OCC experience. Comfortable with Excel + AIMS. Skeptical of "AI."
- Pressure: must decide within 15 minutes when a closure happens.
- Wants: who is affected, how bad, what are my options, all on one screen, exportable to PDF for the briefing.
- Pain point: today re-creates the impact list by hand for every shift.
- App role: `dm`. Can edit settings, run all analyses, export.

### 2.2 OCC Controller — *Ms. Linh* (secondary)

- Runs the dashboard during her shift, hands a clean briefing to the DM.
- Pressure: the DM is on the phone; he wants the impact list now.
- Wants: a default-config one-click flow. Few keystrokes.
- Pain point: too many steps to filter the right rows out of AIMS.
- App role: `viewer` by default; `dm` if delegated.

### 2.3 AIMS PIC — *Mr. Tuấn* (validator)

- Owns the DayRepReport schema. Validates parser correctness on real data.
- Pressure: needs a way to prove the tool's numbers are right before Phase 1.
- Wants: validation dashboard with predicted vs actual confusion matrix.
- App role: `dm` during Phase 0; can be reduced to `viewer` later.

### 2.4 Senior Manager — *Mr. Hùng* (consumer)

- Wants the bottom line: how many pax, how many flights, how much money.
- Doesn't run the tool himself.
- App role: receives PDF / Excel via email or Teams.

## 3. User Stories & Acceptance Criteria

> Notation: each story has an **ID**, **role**, **goal**, **outcome**, **acceptance criteria** (Given / When / Then), and a **link to delivery sprint**.

### 3.1 Run analysis

#### US-01 — Upload one or more DayRepReport files

- *As an* OCC Controller, *I want to* upload one or more `.xlsx` DayRepReport files, *so that* I can analyse a single day or chain of days at once.
- AC:
  - Given a Streamlit session with valid auth (or `OCC_AUTH_DISABLED=1`)
  - When I drop one or more `.xlsx` files in the sidebar uploader
  - Then the file names appear, the byte size is logged, and the page does not crash.
- Sprint 2 (multi-file). Sprint 4 hardens the parser for real-AIMS edge cases.

#### US-02 — Configure 1–5 closure events

- *As a* Duty Manager, *I want to* enter up to 5 simultaneous closure events with airport, date, start/end and type, *so that* I can model real-world IROPS where multiple sectors close together.
- AC:
  - Given the sidebar with `Number of closure events 1..5`
  - When I configure two events for HAN and HPH on 2026-04-24
  - Then both events are passed to `detect_cascade_multi`
  - And the L1 set is the **union** of both events with no double-count.
- Sprint 3.

#### US-03 — Run analysis with one click

- *As an* OCC Controller, *I want to* click **Run Analysis** once, *so that* the page renders KPIs, affected table, Gantt, map, top-10 cards, decision support and stress test.
- AC:
  - When I click Run Analysis
  - Then `st.session_state["analysis_active"] = True`
  - And subsequent button clicks (e.g. Run stress test, Settings change) do not wipe the result page.
- Sprint 7 (state persistence fix `d185b11`).

### 3.2 KPIs & Affected list

#### US-04 — Top-line KPIs

- *As a* Duty Manager, *I want to* see Affected, L1, L2, L3+, Aircraft, Pax disrupted (est.), Cost (est. USD) at the top of the page, *so that* I can size the disruption in 5 seconds.
- AC:
  - Default sample HAN 14:00–18:00 / 2026-04-24 produces `358 / 139 / 51 / 41 / 47 / 26`, pax `27,827`, cost `$1,898,730`.
- Sprint 1 (KPI core), Sprint 3 (pax + cost).

#### US-05 — Affected table with explainer

- *As an* OCC Controller, *I want to* see every affected flight with `flight_no`, `aircraft_reg`, route, STD, STA, level, cascade depth, priority score, est_pax, est_cost_usd, **and a per-row `impact_explanation`**, *so that* I can defend the level assignment to the DM.
- AC:
  - L1 row contains text like `STA 17:00 arrives at HAN during airport closed window 14:00–18:00 on 2026-04-24`.
  - L2/3+ row contains text like `Aircraft VN-A501 is tied to root Level 1 flight 289; this is hop 1 (Level 2)`.
- Sprint 4 (explainer).

#### US-06 — Priority ranking

- *As a* Duty Manager, *I want to* see flights sorted by priority, *so that* I focus on the ones that matter most.
- AC:
  - Score = `level_base + cascade_depth × 10 + intl_bonus`.
  - L1 international with deepest cascade is row 1.
- Sprint 2.

#### US-07 — Top-10 highlight cards

- *As a* Duty Manager, *I want to* see Top-10-by-pax, Top-10-by-cost, Top-10-by-cascade-depth without filtering, *so that* I can shortcut to the worst cases.
- AC:
  - Three cards rendered above the affected table.
- Sprint 3.

#### US-08 — Row-level data quality warnings

- *As an* AIMS PIC, *I want to* see parser warnings inline on rows that have data quality issues, *so that* I can spot AIMS schema regressions.
- AC:
  - The Affected table has a `data_quality_warning` column.
  - The Excel "Affected Flights" sheet contains the same column.
- Sprint 1.

### 3.3 Visualisations

#### US-09 — Plotly Gantt rotation chart

- *As an* OCC Controller, *I want to* see one row per affected aircraft with sector bars coloured by impact level and a shaded closure band, *so that* I can read the rotation chain visually.
- AC:
  - Bars are red (L1) / orange (L2) / yellow (L3+).
  - Closure window appears as a vertical shaded band labelled with the airport.
  - Overnight sectors render across midnight without zero-length bars.
- Sprint 2.

#### US-10 — Network map

- *As a* Duty Manager, *I want to* see a map with closed airports (red ✕), affected airports (orange) and others (light blue), *so that* I see the geographic shape of the disruption.
- AC:
  - Plotly scattergeo with 35+ VN/intl airports built in.
  - Multi-event renders one ✕ per event location.
- Sprint 3.

### 3.4 Exports & briefings

#### US-11 — Excel export

- *As an* OCC Controller, *I want to* download an Excel workbook with sheets for `Summary KPIs`, `All Flights`, `Affected Flights`, `Cascade Tree`, `Warnings`, *so that* I can share a complete dump with crew scheduling and management.
- AC:
  - 5 sheets present.
  - `Affected Flights` sheet includes `data_quality_warning`, `impact_explanation`, `cascade_depth`, `priority_score`, `est_pax`, `est_cost_usd`.
- Sprints 1, 2, 3, 4.

#### US-12 — 1-page PDF briefing

- *As a* Duty Manager, *I want to* download a 1-page PDF with the closure header, 6 KPIs and Top-10 priority flights, *so that* I can hand the page to senior management or attach to an email.
- AC:
  - Magic `%PDF`, exactly 1 page, contains "OCC IROPS Recovery Briefing", 6 KPI rows, ≥ 5 flight rows.
- Sprint 3.

### 3.5 What-if & validation

#### US-13 — What-if alternate window

- *As a* Duty Manager, *I want to* enter an alternate closure window and see the diff (Newly Affected / No Longer Affected / Unchanged), *so that* I can simulate "what if the runway reopens at 16:00."
- AC:
  - Subset window (15:00–16:00 inside 14:00–18:00) produces `Newly Affected = 0` and `No Longer Affected > 0`.
- Sprint 2.

#### US-14 — Validation vs actuals

- *As an* AIMS PIC, *I want to* upload an `actuals.csv` with `(flight_no, actual_outcome, optional flight_date)` and see a confusion matrix + per-level precision/recall/F1, *so that* I can verify model accuracy before Phase 1.
- AC:
  - Confusion matrix renders.
  - Aggregate "Affected (any)" row is computed.
  - Coverage table shows matched / unmatched.
- Sprint 4.

### 3.6 Decision support

#### US-15 — Recovery options for each L1

- *As a* Duty Manager, *I want to* see, for each L1 root, three recovery options (`delay`, `swap_tail`, `cancel`) with computed score, *so that* I can pick the cheapest viable mitigation.
- AC:
  - Table has exactly `3 × |L1|` rows for the sample (153 for the baseline).
  - For flight 198 the rows order on score is `swap_tail (1498) < delay (14213) < cancel (21503)`.
  - `swap_tail` includes `swap_to=<reg>` of a free aircraft on the same day.
- Sprint 7.

#### US-16 — Pax reaccommodation ranking

- *As a* Customer Service lead, *I want to* see cancelled / heavily delayed flights ranked for reaccommodation, *so that* I prioritise rebookings correctly.
- AC:
  - Ranking is intl > domestic, then by pax count, then by cascade depth.
  - Rationale text is rendered ("International; High pax load").
  - For sample, rank 1 is `145 / VN-A534 / HKG→VDH / pax 259`.
- Sprint 7.

#### US-17 — Network stress test

- *As a* Duty Manager, *I want to* replay the current closure config across N consecutive days, *so that* I see the cumulative cost if the closure persists.
- AC:
  - For 3-day HAN baseline: per-day rows = 3, each `affected=139, L1=51, pax=27,827, cost=$1,898,730`; aggregate `Total affected=417, pax=83,481, cost=$5,696,190, worst-day=$1,898,730`.
- Sprint 7.

### 3.7 Persistence & governance

#### US-18 — Auth + RBAC

- *As an* IT Security officer, *I want to* enforce login with bcrypt-hashed passwords and two roles (`dm`, `viewer`), *so that* the tool is safe to deploy on the corporate network.
- AC:
  - `config/users.yaml` stores users; `config/users.example.yaml` is the template.
  - `dm` role can edit settings; `viewer` cannot.
  - `OCC_AUTH_DISABLED=1` is honoured for local dev only and shows a visible warning banner.
- Sprint 5.

#### US-19 — Run history

- *As an* OCC Controller, *I want to* see the last 10 analysis runs in the sidebar with `(timestamp, user, KPIs, file hashes)`, *so that* I can reload yesterday's analysis or compare days.
- AC:
  - SQLite table `runs` accumulates one row per Run Analysis click.
  - "Recent runs" expander lists 10 most recent.
- Sprint 5.

#### US-20 — Audit log

- *As a* Compliance officer, *I want to* see and download an audit log of every login, run, settings change and export, *so that* I can satisfy regulatory inquiries.
- AC:
  - SQLite table `audit_events`.
  - Audit log expander is DM-only and exposes "Download CSV".
- Sprint 5.

#### US-21 — Settings UI

- *As a* Duty Manager, *I want to* edit load factor, $/pax/min and aircraft capacity table from the UI, *so that* I tune the tool without engineering involvement.
- AC:
  - Form is DM-only; values persist to `settings` table; subsequent runs use the new values.
- Sprint 5.

#### US-22 — Docker + healthcheck

- *As an* IT operator, *I want to* run `docker compose up --build` and have a healthchecked, persistent-volume container, *so that* deployment is one command.
- AC:
  - `/_stcore/health` returns `ok`.
  - Named volume `occ_irops_dashboard_data` survives container restart.
- Sprint 5.

### 3.8 Integration & automation

#### US-23 — i18n VN/EN

- *As a* Vietnamese-speaking OCC Controller, *I want to* toggle the UI between Tiếng Việt and English, *so that* I read in my preferred language.
- AC:
  - Locale toggle in header.
  - All hard-coded UI strings come from `locales/{vi,en}.yaml`.
- Sprint 6.

#### US-24 — Folder watcher

- *As an* IT operator, *I want to* drop a DayRepReport into a watched folder and have the tool auto-trigger analysis, *so that* I bridge AIMS without an API.
- AC:
  - `src/integration/folder_watcher.py` polls the configured folder and triggers a CLI run on each new file.
- Sprint 6.

#### US-25 — Threshold alerts

- *As a* Duty Manager, *I want to* receive a Teams message when Affected > X or Cost > $Y, *so that* I am told about big disruptions even if I'm not at the desk.
- AC:
  - `src/integration/alerts.py` sends an aggregated KPI payload (no flight-level pax data) to a configured webhook.
- Sprint 6.

#### US-26 — Scheduled morning briefing

- *As a* OCC Manager, *I want to* receive a 06:00 PDF briefing of all active closure events, *so that* I start my day informed.
- AC:
  - CLI entry point `python -m src.integration.scheduled_briefing` outputs PDF and (optionally) emails it.
- Sprint 6.

## 4. Functional Requirements

> One-line cross-reference back to the user stories above.

| ID | Function | Source |
|---|---|---|
| F-01 | Multi-file `.xlsx` upload | US-01 |
| F-02 | 1–5 simultaneous closure events with type | US-02 |
| F-03 | One-click Run Analysis with state persistence | US-03 |
| F-04 | KPI bar (Affected / L1 / L2 / L3+ / Aircraft / Pax / Cost) | US-04 |
| F-05 | Affected table with explainer + warnings | US-05, US-08 |
| F-06 | Priority ranking | US-06 |
| F-07 | Top-10 highlight cards | US-07 |
| F-08 | Plotly Gantt rotation chart | US-09 |
| F-09 | Plotly scattergeo network map | US-10 |
| F-10 | Excel export (5 sheets) | US-11 |
| F-11 | 1-page PDF briefing | US-12 |
| F-12 | What-if alternate window with diff | US-13 |
| F-13 | Validation dashboard (actuals.csv) | US-14 |
| F-14 | Recovery options per L1 with score | US-15 |
| F-15 | Pax reaccommodation ranking | US-16 |
| F-16 | Network stress test (multi-day replay) | US-17 |
| F-17 | Auth + RBAC | US-18 |
| F-18 | Run history (SQLite) | US-19 |
| F-19 | Audit log + CSV export | US-20 |
| F-20 | Settings UI (load factor / cost / capacity) | US-21 |
| F-21 | Docker compose + healthcheck | US-22 |
| F-22 | i18n VN/EN | US-23 |
| F-23 | Folder watcher | US-24 |
| F-24 | Threshold alerts (Teams webhook) | US-25 |
| F-25 | Scheduled morning briefing CLI | US-26 |

## 5. Non-Functional Requirements

| ID | Category | Requirement | Target | Verified by |
|---|---|---|---|---|
| NFR-01 | Performance | Cascade detection on 5,000 flights × 3 days × 5 events | < 10 s | `tests/test_performance.py::test_5000_flight_perf_budget` |
| NFR-02 | Performance | UI initial render of result page on sample | < 2 s | Recording / observed in Sprint 2–7 e2e tests |
| NFR-03 | Reliability | Tests pass on Python 3.10, 3.11, 3.12 | 100% | CI matrix |
| NFR-04 | Reliability | App runs on Python 3.13 | 100% | Verified post Sprint 9 cumulative merge (LogRecord field rename) |
| NFR-05 | Code quality | `ruff check`, `ruff format --check`, `mypy src` | 0 errors | CI lint stage |
| NFR-06 | Test coverage | Cascade + decision + parser modules | ≥ 85% branch coverage | `pytest --cov` (recommended; not yet gated in CI) |
| NFR-07 | Security | Auth mandatory in production | bcrypt + yaml file users | `src/auth/users.py` + `OCC_AUTH_DISABLED` warning banner |
| NFR-08 | Security | No PII in webhook payloads | Aggregated KPI only | `src/integration/alerts.py` payload schema |
| NFR-09 | Compatibility | Supports VN-accented headers (NFC + NFD) | 100% of known variants | `tests/test_parser_hardening.py` |
| NFR-10 | Compatibility | Supports REG variants `VN-A517 / VNA517 / VN A517 / VN/A517` | All normalise to `VN-A517` | `tests/test_parser_hardening.py::test_normalize_reg` |
| NFR-11 | Compatibility | Supports time fields `HH:MM`, `HHMM`, `HMM`, `+1`/`+2` markers, Excel float | All round-trip correctly | `tests/test_time_parser.py` |
| NFR-12 | Observability | Every analysis run produces a structured JSON log line | 100% | `src/logging_config.py` + `app.py` logger calls |
| NFR-13 | Auditability | Every login / run / settings-change / export is recorded | 100% | `audit_events` table + UI Audit log expander |
| NFR-14 | Deployment | One-command Docker deploy | `docker compose up --build` | `docker-compose.yml`, `docs/PRODUCTION_DEPLOY.md` |
| NFR-15 | Internationalisation | UI text is locale-driven (no hard-coded VN/EN strings) | 100% of user-facing copy | `locales/vi.yaml` + `locales/en.yaml`; `src/i18n/__init__.py` |
| NFR-16 | UX | Post-analysis widget interactions must NOT wipe the result page | 100% of widgets in result block | Sprint 7 regression test in `tests/test_app_smoke.py` |
| NFR-17 | UX | Estimated values are labelled `(est.)` in UI | All `est_pax` / `est_cost_usd` columns and KPIs | UI copy review |

## 6. Release / Sprint Roadmap

| Sprint | PR | Theme | Headline outputs | Status |
|---:|---|---|---|---|
| 1 | [#2](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/2) | P0 hardening | Bug `affected` fixed; pyproject + ruff + black + mypy + pre-commit; row-level warnings; structured JSON logging; +8 tests | merged |
| 2 | [#3](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/3) | P1 ROI | Multi-file upload; overnight cascade; Plotly Gantt; what-if simulator; priority ranking; +11 tests | merged |
| 3 | [#4](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/4) | Multi-event + impact | Multi-airport closure; closure type label; pax + cost estimator; Top-10 cards; PDF briefing; network map; +23 tests | merged |
| 4 | [#5](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/5) | Pilot readiness | Discrepancy explainer; parser hardening; perf benchmark < 10 s; validation dashboard; Pilot Run Book; +31 tests | merged |
| 5 | [#6](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/6) | Production deploy | Auth (`dm`/`viewer`); SQLite persistence; audit log; Settings UI; Docker compose; healthcheck; +29 tests | merged |
| 6 | [#7](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/7) | Integration & automation | i18n VN/EN; folder watcher; alert engine; scheduled briefing CLI; +25 tests | merged |
| 7 | [#8](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/8) | Decision support | Recovery options scoring; pax reaccommodation; network stress test; state-loss fix `d185b11`; +19 tests | merged |
| 9 | [#9](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/9) | Cumulative merge to default | All Sprint 2–7 features brought to default branch in one merge; Python 3.13 LogRecord fix incl. | merged |

> Sprint 8 was reserved for the Sprint 4b real-AIMS validation block (waits on real DayRepReport files from AIMS PIC) and was deliberately not opened.

## 7. Future Sprints (deferred, not in current scope)

| Sprint | Working name | Block on | One-liner |
|---:|---|---|---|
| 4b | Real-AIMS fixture validation | 5–10 sanitised real AIMS files | Build fixture-driven regression tests + actual precision/recall numbers. |
| 8 | Live AIMS integration | IT credentials (SFTP / API) | Replace folder watcher with active pull; eliminate manual upload. |
| 9 | Crew FDP & legality | Duty-time data source | Filter recovery options by crew duty legality. |
| 10 | NOTAM auto-fetch | Official VATM / ICAO endpoint | Auto-suggest closure events from NOTAMs. |
| 11 | ML cancel-probability | ≥ 1 month of historical actuals | XGBoost augmentation of Sprint 7 rule-based scoring. |
| 12 | SSO / OIDC | Corporate IdP availability | Migrate from yaml-file users to enterprise SSO. |

## 8. Acceptance & Pilot Gates

The product is **pilot-ready** if and only if:

1. CI is green on the default branch (lint + tests on 3.10 / 3.11 / 3.12).
2. End-to-end UI tests for Sprints 2, 3, 4, 5, 6, 7 each have a recording + report attached to their PR.
3. The Pilot Run Book ([docs/PILOT_RUN_BOOK.md](./PILOT_RUN_BOOK.md)) Phase 0 acceptance gates are met:
   - L1 precision ≥ 0.95 on at least one real AIMS day.
   - L1 recall ≥ 0.90 on the same day.
   - Affected (any) recall ≥ 0.85.
   - Performance budget < 10 s on the largest day in the fixture set.
4. A DM and an OCC Controller have run the dashboard unaided once each.
5. The audit log is exportable as CSV and reviewed by IT Security.

## 9. Open Questions

| # | Question | Owner | Required by |
|---:|---|---|---|
| Q1 | Will OCC accept yaml-file auth as the production auth model, or do we need SSO before Phase 3? | IT Security | Before Phase 3 |
| Q2 | Are the default load factor (0.85) and $/pax/min (0.50) acceptable for management reporting, or should DM adjust per-route? | DM | Phase 0 |
| Q3 | Which Teams channel receives threshold alerts? | OCC Manager | Phase 1 |
| Q4 | Will an AIMS API or SFTP feed become available, or does folder watcher remain the bridge indefinitely? | AIMS PIC + IT | Sprint 8 (deferred) |
| Q5 | Retention period for `data/runs.db` and `audit_events`? | Compliance | Sprint 5 follow-up |
