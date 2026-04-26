# 04 — Definition of Done

> Source-of-truth checklist. Updated end of Sprint 7 (cumulative merge PR #9 on default branch).

## 1. Priority Action List (post Sprint 7)

The original priorities (Sprint-1 era) are all complete. The current priority list is forward-looking:

| Priority | Item | Status | Block |
|---:|---|---|---|
| 1 | Sprint 4b — real-AIMS fixture validation | pending | 5–10 sanitised real DayRepReport files from AIMS PIC |
| 2 | Phase 0 acceptance gates (precision ≥ 0.95 / recall ≥ 0.90) | pending | Sprint 4b |
| 3 | Phase 1 shadowing (OCC Controller daily runs) | pending | Phase 0 sign-off |
| 4 | Phase 2 parallel run (DM observer) | pending | Phase 1 sign-off |
| 5 | Phase 3 live pilot or tabletop drill | pending | Phase 2 sign-off |
| 6 | Sprint 8 — live AIMS integration | pending | IT credentials |
| 7 | Sprint 9 — crew FDP filter | pending | Duty-time data |
| 8 | Sprint 10 — NOTAM auto-fetch | pending | Endpoint availability |
| 9 | Sprint 11 — ML cancel-probability | pending | Historical actuals (≥ 1 month) |
| 10 | Sprint 12 — SSO migration | pending | Corporate IdP |

## 2. MVP Definition of Done — Status

| Criterion | Target | Result |
|---|---:|---|
| Parser handles all known time formats | 100% | done (Sprint 4) |
| REG normalization creates no phantom aircraft | 0 known errors | done (Sprint 4) |
| Header detection works on real DayRepReports | At least 5 files | **deferred (Sprint 4b)** |
| Expected sample KPI: `358 / 139 / 51 / 41 / 47 / 26` (HAN 14–18 / 24-04-2026) | 100% | done (verified Sprints 1–7 e2e) |
| Pax (est.) | 27,827 | done |
| Cost (est. USD) | 1,898,730 | done |
| OCC Controller can run unaided after week 1 | Yes | **pending (Phase 1)** |
| OCC Controller satisfaction | ≥ 4.0 / 5 | **pending (Phase 1–2)** |
| Tool output produced under 5 minutes | < 5 min | done (perf bench < 10 s for 5,000 flights × 3 days × 5 events; UI render < 2 s) |
| Recommendation match with DM decision | > 70% | **pending (Phase 2 parallel run)** |
| Tabletop drill executed | 1 drill | **pending (Phase 3)** |
| DM says output is useful | Yes | **pending (Phase 3)** |

## 3. Engineering Done Checklist — Status

### Parser

- [x] Raw Excel file can be loaded.
- [x] Dynamic header row can be detected.
- [x] Column aliases map correctly to canonical schema (25+ variants, NFC + NFD).
- [x] Footer rows are skipped.
- [x] Invalid rows logged as `data_quality_warning`.
- [x] All required time formats handled (`HH:MM`, `HHMM`, `HMM`, `+1`, Excel float, `datetime.time`).
- [x] Aircraft registration is normalized.
- [x] Canonical dataframe is returned.
- [x] Multi-file concatenation with file-prefix warning.
- [x] Parser tests pass (Sprint 4 hardening).

### Cascade detector

- [x] Single-event detection (`detect_cascade`).
- [x] Multi-event detection (`detect_cascade_multi`).
- [x] Boundary rule: start inclusive, end exclusive.
- [x] Closure-date filter in Pass 1.
- [x] Pass 2 sorts by `(flight_date, std)`.
- [x] Multiple Level 1 sectors on same aircraft handled.
- [x] Downstream cascade traced by aircraft registration.
- [x] Numeric impact level stored; UI maps ≥ 3 → `3+`.
- [x] `cascade_depth` exposed.
- [x] `priority_score` computed.
- [x] `impact_explanation` per row.
- [x] Cascade tests pass (overnight + multi-event regression suites).

### UI / Streamlit

- [x] Multi-file upload.
- [x] 1–5 closure events with type label.
- [x] One-click Run Analysis with state persistence (Sprint 7 fix).
- [x] KPI bar (Affected / L1 / L2 / L3+ / Aircraft / Pax / Cost).
- [x] Affected flight table with explainer + warnings.
- [x] Top-10 highlight cards.
- [x] Plotly Gantt rotation chart.
- [x] Plotly scattergeo network map.
- [x] What-if simulator with diff panel.
- [x] Decision support expander (recovery + reaccom).
- [x] Network stress test expander.
- [x] Validation vs Actuals expander.
- [x] Recent runs / Settings (DM) / Audit log (DM) expanders.
- [x] Locale toggle VN/EN.
- [x] Excel export (5 sheets).
- [x] PDF briefing (1 page).

### Persistence & Auth

- [x] SQLite `runs` / `settings` / `audit_events`.
- [x] yaml-file users + bcrypt + 2 roles.
- [x] `OCC_AUTH_DISABLED=1` honoured + visible warning banner.
- [x] Audit log CSV download (DM-only).
- [x] DM-only Settings UI.

### Integration & Automation

- [x] AIMS folder watcher.
- [x] Teams webhook alert engine.
- [x] Scheduled briefing CLI.
- [ ] Live AIMS API / SFTP — deferred (Sprint 8).
- [ ] NOTAM auto-fetch — deferred (Sprint 10).

### Decision Support

- [x] Recovery options scoring per L1 (delay / swap_tail / cancel).
- [x] Pax reaccommodation ranking (intl > domestic > pax > depth).
- [x] Network stress test (multi-day what-if).
- [ ] Crew FDP / legality filter — deferred (Sprint 9).
- [ ] ML cancel-probability — deferred (Sprint 11).

### Infrastructure

- [x] GitHub Actions CI: `lint` + `test` matrix (3.10 / 3.11 / 3.12).
- [x] `pyproject.toml` + `ruff` + `ruff format` + `mypy` + pre-commit hooks.
- [x] Dockerfile (non-root) + docker-compose (named volume + healthcheck).
- [x] Structured JSON logging (stdlib only).
- [x] Performance test (`< 10 s` on 5,000 flights × 3 days × 5 events).

### Pilot Readiness

- [x] Pilot Run Book (`docs/PILOT_RUN_BOOK.md`).
- [x] BRD (`docs/BRD.md`).
- [x] PRD (`docs/PRD.md`).
- [x] Architecture (`docs/ARCHITECTURE.md`).
- [x] Production Deploy (`docs/PRODUCTION_DEPLOY.md`).
- [x] Tabletop drill / phase-0 validation / feedback form / pilot plan / known limitations / user guide.
- [ ] 5–10 real DayRepReport files validated.
- [ ] DM signs off Phase 0 acceptance gates.

## 4. Core Conclusion

The hardest part of this project remains:

1. Data quality in real AIMS DayRepReport files (mitigated by Sprint 4 parser hardening; pending real-data validation in Sprint 4b).
2. Change management with OCC Controller and Duty Manager (mitigated by Sprint 4 explainer + Sprint 5 audit log).
3. Building trust through audit trail and controlled pilot rollout (mitigated by Sprint 5 persistence + Sprint 4 validation dashboard).

> Continue to invest more effort in Phase 0 validation and Tabletop Drill than in extra Streamlit features.
