# Business Requirements Document (BRD)
## OCC IROPS Recovery Dashboard

| Field | Value |
|---|---|
| Document version | 1.0 |
| Status | Approved for pilot (Phase 0–3) |
| Owner | OCC IROPS programme (AIMS PIC + Developer) |
| Last updated | 26/04/2026 (post Sprint 7) |
| Related docs | [PRD](./PRD.md) · [Architecture](./ARCHITECTURE.md) · [Pilot Run Book](./PILOT_RUN_BOOK.md) · [Production Deploy](./PRODUCTION_DEPLOY.md) |

---

## 1. Executive Summary

Vietnam Airlines OCC currently relies on manual reading of the AIMS *DayRepReport* during irregular operations (IROPS) — primarily airport closures triggered by weather, ATC flow control, runway incidents, or aircraft-on-ground (AOG) events. The Duty Manager (DM) and OCC Controller must, under time pressure, identify (a) flights directly affected by the closure window, (b) downstream sectors blocked by aircraft rotation, and (c) the resulting passenger and cost exposure. Today, that work is done with paper printouts, mental rotation tracing, and Excel ad-hoc filters. The result is slow, error-prone, and not auditable.

The **OCC IROPS Recovery Dashboard** is a lightweight Python/Streamlit tool that ingests the same DayRepReport file the DM already exports from AIMS and produces, within seconds, a structured impact list (Level 1 / Level 2 / Level 3+), pax/cost estimates, recovery-option scoring, passenger reaccommodation ranking, a network stress test, a 1-page PDF briefing, and an Excel export — all without altering AIMS, without storing operational decisions automatically, and without claiming to be "AI" or "auto-recovery."

The DM remains the final decision maker. The tool is positioned as an **automated AIMS report reader**, not a replacement for human judgement.

## 2. Business Objectives

| # | Objective | Measure | Target |
|---:|---|---|---|
| O1 | Cut time to identify all affected flights during a closure event | Minutes from closure notice → affected list ready | < 5 minutes (vs ~20–30 today) |
| O2 | Cut time to prepare DM briefing | Minutes from closure notice → 1-page briefing PDF | < 15 minutes (vs ~45 today) |
| O3 | Improve cascade detection accuracy on real AIMS data | L1 precision / L1 recall / Affected recall vs actual outcomes | ≥ 0.95 / ≥ 0.90 / ≥ 0.85 |
| O4 | Quantify business impact during IROPS so management can prioritise resources | KPI: Affected, L1, L2, L3+, Aircraft, Pax disrupted, Cost exposure (USD) | Surface on every run |
| O5 | Provide auditable history of every analysis run | Persisted run record per (user, timestamp, config, KPI) | 100% of runs |
| O6 | Stay within OCC's existing AIMS-centric workflow | No change to upstream AIMS process; DM exports DayRepReport as today | No new training upstream |
| O7 | Be deployable internally with auth, persistence and Docker | One-command deploy via `docker compose up` | Achieved at Sprint 5 |

## 3. Stakeholders

| Stakeholder | Interest | Engagement model |
|---|---|---|
| **Duty Manager (DM)** | Make recovery decisions faster and with quantified impact. Final decision authority. | Primary user (`dm` role). Reviews tool output, signs off recovery decisions. |
| **OCC Controller** | Run the tool, review affected flights, brief the DM. | Secondary user (`viewer` role can run analysis when DM delegates). |
| **AIMS PIC** | Owns DayRepReport schema. Validates parser correctness. | Phase 0 validation lead. Signs off pilot acceptance gates. |
| **Network Control Centre / Crew Scheduling** | Receive structured handoff for swap/cancel decisions, pax reaccommodation list. | Consumer of tool output. Future integration target. |
| **Customer Service / Reaccommodation Desk** | Get prioritised pax list when cancellations happen. | Consumer of "Pax reaccommodation" panel + Excel export. |
| **OCC Manager / Senior Management** | Visibility on disruption cost & operational risk. | Read-only consumer of PDF briefing + KPI dashboard. |
| **IT / Security / Compliance** | Auth, audit trail, deployment safety, data residency. | Owns Docker deployment, `users.yaml`, audit-log retention. |
| **Developer / Code Agent** | Maintains, extends, runs CI. | Author of stack PRs #2–#9. |

## 4. Business Scope

### In scope (current release — Sprints 1–7)

| Capability | Source sprint | Notes |
|---|---|---|
| Detect flights directly affected by an airport closure (Level 1) | Sprint 1 / pre-existing | STA / STD inside `[start, end)` window of closure date. |
| Trace cascade by aircraft rotation (Level 2 → Level 3+) | Sprint 1 / pre-existing | Two-pass algorithm; `cascade_depth` exposed since Sprint 2. |
| **Overnight cascade** across multi-day data | Sprint 2 | `(flight_date, std)` sort prevents loss of next-day downstream sectors. |
| **Multi-airport / multi-event closure** (up to 5 simultaneous) | Sprint 3 | Union-of-masks in Pass 1 + single Pass 2 over merged L1 set. |
| **Closure type label** (`airport_closed` / `runway_closed` / `atc_flow`) | Sprint 3 | Cosmetic only — no logic branching. |
| **Pax & cost impact estimation** | Sprint 3 | Configurable load factor and $/pax/min cost rate. |
| **Top-10 highlight cards** (pax / cost / cascade depth) | Sprint 3 | Surfaces highest-impact flights without filtering. |
| **Plotly Gantt rotation chart** with closure shading | Sprint 2 | One row per aircraft, level-coloured sectors. |
| **Network map view** | Sprint 3 | Plotly scattergeo of affected airports. |
| **1-page PDF briefing** | Sprint 3 | reportlab; designed for paper / email handoff. |
| **What-if simulator** (alternative closure window) | Sprint 2 | Diff vs baseline: Newly Affected / No Longer Affected / Unchanged. |
| **Discrepancy explainer** (`why_l1`, `why_l2`) | Sprint 4 | Per-row natural-language reason. |
| **Validation dashboard** (predicted vs actuals CSV) | Sprint 4 | Confusion matrix + per-level precision / recall / F1. |
| **Performance budget** | Sprint 4 | 5,000 flights × multi-day × 5 events < 10s. |
| **Auth + RBAC** (`dm` / `viewer`) | Sprint 5 | yaml-file users, bcrypt; `OCC_AUTH_DISABLED=1` for local dev only. |
| **Run history & SQLite persistence** | Sprint 5 | Sidebar "Recent runs" + reload prior config. |
| **Audit log** | Sprint 5 | Every login / run / export logged; CSV download for SIEM. |
| **Settings UI (DM-only)** | Sprint 5 | Load factor, cost-per-pax-min, capacity table editable from UI. |
| **Docker compose + healthcheck** | Sprint 5 | Single-command deploy, named volume for DB persistence. |
| **i18n VN/EN** | Sprint 6 | Locale toggle in header; locale files at `locales/{vi,en}.yaml`. |
| **AIMS folder watcher** | Sprint 6 | Drop-in inbox folder → auto trigger analysis. |
| **Threshold alerts** (Teams webhook) | Sprint 6 | Fires when Affected > X or Cost > $Y. |
| **Scheduled morning briefing CLI** | Sprint 6 | Cron-friendly job that emits PDF + KPI snapshot. |
| **Recovery options scoring** | Sprint 7 | For each L1: `delay`, `swap_tail`, `cancel` ranked by `w_pax × pax + w_cost × cost + w_op × op_penalty`. |
| **Pax reaccommodation ranking** | Sprint 7 | Intl > domestic; then by pax count; then by cascade depth. |
| **Network stress test** | Sprint 7 | Multi-day what-if replay with same airports closed each day. |

### Out of scope (deferred or future)

- **Live AIMS API / SFTP integration.** Blocked on IT credentials. Folder watcher is the bridge.
- **Crew FDP / legality check.** Blocked on duty-time data source. Sprint 7 placeholder uses op-penalty weights only.
- **ML-based cancel-probability prediction.** Blocked on ≥ 1 month of historical actuals.
- **NOTAM auto-fetch.** Blocked on official VATM / ICAO endpoint.
- **SSO / LDAP / OIDC.** MVP uses yaml-file users; migrate post-pilot.
- **Mobile / tablet-optimised UI.** Streamlit's responsive layout is adequate for the OCC desktop floor.
- **Multi-tenant SaaS.** Single-tenant only. Data resides in the same VM/host as AIMS export drops.

## 5. Business Rules

> These are the rules that *must* be enforced by the tool and cannot be overridden by configuration. They define correctness of impact analysis.

| ID | Rule | Owner | Verified by |
|---|---|---|---|
| BR-01 | Closure window is **start inclusive, end exclusive**: `time >= start AND time < end`. | AIMS PIC | `tests/test_cascade_detector.py::test_boundary_*` |
| BR-02 | Level 1 detection is restricted to `event.closure_date`. Same-time-of-day on a different date is *not* L1. | AIMS PIC | `tests/test_overnight_cascade.py` (Sprint 2 regression). |
| BR-03 | Cascade Pass 2 sorts each aircraft group by `(flight_date, std)` so downstream propagation works across midnight. | Developer | `tests/test_overnight_cascade.py`. |
| BR-04 | Multiple Level 1 sectors on the same aircraft must each independently trigger their own downstream chain. Pass 2 runs once over the merged L1 set; no double-counting. | Developer | `tests/test_cascade_detector.py::test_multiple_level1_*`, `tests/test_multi_event_cascade.py`. |
| BR-05 | Multi-event closure: a flight already L1 from event A is not "downgraded" if event B also affects it. The L1 set is a union across all events. | Developer | `tests/test_multi_event_cascade.py`. |
| BR-06 | Internal numeric `level` field is preserved. UI maps any level ≥ 3 to the display label `3+` to avoid noisy granularity. | Developer | `src/cascade/cascade_detector.py`. |
| BR-07 | Impact explanation (`why_l1` / `why_l2`) must reference the specific event(s) that triggered each affected row, in human-readable form. | Developer | `tests/test_impact_explanation.py`. |
| BR-08 | Closure type (`airport_closed` / `runway_closed` / `atc_flow`) is **labelling only**. It does not change which flights are detected as affected. | AIMS PIC | T3 cosmetic-invariant test (Sprint 3). |
| BR-09 | The DM is the final decision maker. All recovery options, reaccommodation rankings and stress-test outputs are **suggestions** — the tool never executes a recovery action. | OCC governance | UX copy: "Suggestion only — Duty Manager decides." |
| BR-10 | Auth is mandatory in production. Local dev may set `OCC_AUTH_DISABLED=1` and the UI MUST display a visible warning banner. | Security | `src/auth/users.py::is_auth_disabled` + sidebar banner. |
| BR-11 | Every analysis run is persisted to `data/runs.db` with `(user, timestamp, file_hashes, closure_config, kpi_snapshot)`. | Compliance | Sprint 5 persistence layer. |
| BR-12 | Audit log records every login, run, settings change and export. CSV exportable. | Compliance | Sprint 5 audit log. |
| BR-13 | The tool never modifies the AIMS DayRepReport file. Uploaded files are written to a temp path, parsed, then discarded. | Security | `app.py` upload handling. |
| BR-14 | The tool never sends data outside the OCC perimeter unless an outbound integration (Teams webhook, SMTP, folder watcher target) is explicitly configured by an authorised admin. | Security | Sprint 6 alert/briefing engines are opt-in via config. |

## 6. Success Metrics

### Operational metrics (per IROPS event)

| Metric | Source | Target |
|---|---|---|
| Time from closure notice → affected list visible | UI timestamp | < 5 minutes |
| Time from closure notice → 1-page PDF in DM inbox | PDF generation timestamp | < 15 minutes |
| L1 precision vs actual delays/cancels | Validation dashboard | ≥ 0.95 |
| L1 recall vs actual delays/cancels | Validation dashboard | ≥ 0.90 |
| Affected (any level) recall | Validation dashboard | ≥ 0.85 |
| Run completes within performance budget | App log | 100% under 10s for ≤ 5,000 flights |

### Adoption metrics (per pilot phase)

| Metric | Source | Target |
|---|---|---|
| OCC Controller can run unaided after Phase 1 week 1 | Feedback form | Yes |
| OCC Controller satisfaction | Feedback form | ≥ 4.0 / 5 |
| DM uses tool output as briefing input | DM interview | Yes |
| Recovery-option recommendation matches DM decision | Phase 2 parallel run | > 70% |
| Tabletop drill executed within 1.5 h | Drill log | Yes |

### Engineering metrics (per release)

| Metric | Source | Target |
|---|---|---|
| Unit + integration tests passing | CI matrix (3.10 / 3.11 / 3.12) | 100% (currently 203 / 203) |
| Lint clean (`ruff check`, `ruff format`) | CI lint stage | 0 errors |
| Type-check clean (`mypy src`) | CI lint stage | 0 errors |
| Branch coverage of cascade & decision modules | pytest-cov | ≥ 85% |
| End-to-end UI test executed each sprint | Recording + report on PR | Yes (Sprints 2, 3, 4–7) |

## 7. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| AIMS DayRepReport schema drifts (new column / Vietnamese accent variant). | Medium | Parser silently drops rows. | Sprint 4 alias map covers 25+ variants (NFC + NFD); parser emits `data_quality_warning`; AST-level regression test ensures `affected` is computed for every read path; Pilot Run Book mandates fixture refresh on schema change. |
| OCC adopts the tool then loses trust because predictions diverge from reality. | Medium | Pilot stalls. | Sprint 4 validation dashboard surfaces precision / recall vs actual outcomes; Pilot Run Book defines explicit acceptance gates before Phase 1 / 2 / 3. |
| Streamlit state-loss bug pattern reappears (button clicks wipe page). | Low (locked by regression test) | Critical UX failure. | Sprint 7 fix persists `analysis_active` in `st.session_state`; AST regression guard in `tests/test_app_smoke.py` fails CI if pattern is broken. |
| Python version drift (3.13 LogRecord field collision). | Low (fixed) | Runtime crash. | Sprint 9 cumulative merge renamed `extra={"filename": ...}` → `"filenames"`; CI matrix includes 3.10–3.12 (3.13 to be added once Streamlit fully supports). |
| Cost / pax assumptions wrong → wrong management decisions. | Medium | Misallocated resources. | Settings UI lets DM-role override defaults; values stored per-tenant in SQLite; PDF briefing labels every estimated number with "(est.)". |
| Config file `users.yaml` leaks bcrypt hashes. | Low | Auth compromise. | `users.yaml` is gitignored; `users.example.yaml` is the only file committed; deployment doc instructs file-mode 0600. |
| Outbound webhook (Teams) leaks PII. | Low | Compliance breach. | Webhook payload contains aggregated KPI only — no flight-level pax names. Sprint 6 alert engine documented in BR-14. |
| Operator runs analysis with `OCC_AUTH_DISABLED=1` in production. | Low | Unauthenticated access. | Visible amber banner in sidebar; environment variable name is intentionally explicit. |
| Aircraft rotation chain split across two DayRepReport files (D + D+1). | Medium | Missed downstream cascade. | Sprint 2 multi-file upload + overnight Pass 2 sort by `(flight_date, std)`. Pilot Run Book recommends always uploading D + D+1. |

## 8. Assumptions

- AIMS DayRepReport remains exportable as `.xlsx` with the column groups currently aliased in `src/parser/dayrep_parser.py`.
- Every flight has an `aircraft_reg`. Without REG, cascade tracing is impossible — Sprint 4 parser emits a row-level `data_quality_warning` and excludes such rows from L2+ tracing.
- The DM has at least Excel-paper-PDF literacy. No SQL or coding required.
- The OCC desktop runs Chromium-class browser and can reach the dashboard host on the corporate network.
- Hosting is on a single-tenant Linux VM inside the airline perimeter.

## 9. Constraints

- Must be deployable with **stdlib + open-source Python** dependencies only (no commercial license).
- Must not require modifications to AIMS.
- Must support Vietnamese-accented column headers in DayRepReport (real AIMS output uses both NFC and NFD).
- Must run on Python ≥ 3.10 to keep parity with airline IT's existing Python footprint.
- All passenger-level numbers shown in the UI are **estimates** (`est_pax`, `est_cost_usd`) until Phase 2 collects actual pax data; UI must label them as such.

## 10. Glossary

| Term | Meaning |
|---|---|
| **OCC** | Operations Control Centre. |
| **IROPS** | Irregular Operations — any disruption to the published schedule. |
| **AIMS** | Airline Information Management System (the airline's schedule / rotation system of record). |
| **DayRepReport** | The daily-operations Excel report exported from AIMS. Primary tool input. |
| **DM** | Duty Manager — final decision authority during IROPS. |
| **Cascade** | Downstream impact propagated through aircraft rotation when an upstream flight (Level 1) is delayed or cancelled. |
| **Level 1** | Flight directly affected by the closure event (STA / STD inside the closure window on the closure date). |
| **Level 2 / 3+** | Flight downstream of a Level 1 by aircraft rotation. Numeric internal level; UI groups ≥ 3 as `3+`. |
| **Cascade depth** | Number of hops from a Level 1 root flight along the same aircraft's rotation. |
| **What-if** | Simulator that recomputes affected flights under an alternate closure window and shows the delta. |
| **Stress test** | Multi-day what-if that replays the same closure config across N consecutive days. |
| **Recovery option** | One of {`delay`, `swap_tail`, `cancel`} suggested by the tool for each L1 root, scored against pax / cost / op-penalty. |
| **Reaccommodation** | The process of rebooking pax onto alternate flights when the primary is cancelled / heavily delayed. |
| **Score** | Sprint 7 recovery score: `w_pax × pax + w_cost × cost + w_op × op_penalty`. Lower is better. |
