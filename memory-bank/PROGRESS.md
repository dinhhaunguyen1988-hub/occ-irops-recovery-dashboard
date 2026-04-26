# Progress Log — OCC IROPS Recovery Dashboard

## Headline status

- **Phase**: Sprints 1 → 7 delivered. Pilot-ready (Phase 0 gating).
- **Default branch**: `devin/1777174450-occ-irops-dashboard` — contains all Sprint 1–7 features after PR #9 cumulative merge.
- **CI**: 4/4 green on default (lint + test 3.10 / 3.11 / 3.12).
- **Tests**: **203 passed** (was 56 at MVP).
- **Open follow-ups**: Sprint 4b (real-AIMS fixtures), Sprint 8+ (live AIMS API, crew FDP, ML, NOTAM, SSO).

## Sprint Map (PR → Theme → Status)

| Sprint | PR | Theme | Status |
|---:|---|---|---|
| 1 | [#2](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/2) | P0 hardening | merged |
| 2 | [#3](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/3) | Overnight cascade + Gantt + what-if + ranking | merged |
| 3 | [#4](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/4) | Multi-event + pax/cost + PDF + map | merged |
| 4 | [#5](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/5) | Pilot readiness | merged |
| 5 | [#6](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/6) | Production deploy | merged |
| 6 | [#7](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/7) | Integration & automation | merged |
| 7 | [#8](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/8) | Decision support | merged |
| — | [#9](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/9) | Cumulative merge to default | merged |

For sprint-level details see [08_SPRINT_HISTORY.md](./08_SPRINT_HISTORY.md).

## Definition-of-Done Checklist (post-Sprint 7)

### Parser
- [x] Raw Excel file can be loaded.
- [x] Dynamic header row can be detected.
- [x] Column aliases map correctly to canonical schema (25+ variants, NFC + NFD).
- [x] Footer rows are skipped.
- [x] Invalid rows are logged as warnings (`data_quality_warning` column).
- [x] All required time formats are handled (`HH:MM`, `HHMM`, `HMM`, `+1`, Excel float, `datetime.time`).
- [x] Aircraft registration is normalized (`VN-A517` from any input variant).
- [x] Canonical dataframe is returned.
- [x] Multi-file concatenation with `file#N:` warning prefix.

### Cascade Detector
- [x] Single-event detection (`detect_cascade`).
- [x] Multi-event detection (`detect_cascade_multi`, union-of-masks Pass 1).
- [x] Boundary rule: start inclusive, end exclusive.
- [x] Closure-date filter in Pass 1 (overnight cascade).
- [x] Pass 2 sorts by `(flight_date, std)`.
- [x] Multiple Level 1 sectors on same aircraft handled correctly.
- [x] `cascade_depth` exposed.
- [x] `priority_score` computed.
- [x] `impact_explanation` per row (Sprint 4 explainer).
- [x] UI displays level ≥ 3 as `3+`; internal numeric level preserved.

### UI / Streamlit
- [x] Multi-file upload.
- [x] 1–5 closure events with type label.
- [x] One-click Run Analysis with state persistence.
- [x] KPI bar (7 metrics).
- [x] Affected table with explainer + warnings.
- [x] Top-10 highlight cards (pax / cost / depth).
- [x] Plotly Gantt rotation chart.
- [x] Plotly scattergeo network map.
- [x] What-if simulator with diff panel.
- [x] Decision support expander (recovery + reaccom).
- [x] Network stress test expander (multi-day).
- [x] Validation vs Actuals expander.
- [x] Recent runs / Settings (DM) / Audit log (DM) expanders.
- [x] Locale toggle VN/EN.

### Exports
- [x] Excel workbook (5 sheets) with Sprint 4 explainer columns.
- [x] 1-page PDF briefing.

### Persistence & Auth
- [x] SQLite `runs` / `settings` / `audit_events`.
- [x] yaml-file users + bcrypt + 2 roles (`dm`, `viewer`).
- [x] `OCC_AUTH_DISABLED=1` honoured + visible warning banner.
- [x] Audit log CSV download (DM-only).
- [x] DM-only Settings UI for load factor / cost / capacity.

### Integration & Automation (config-driven, opt-in)
- [x] AIMS folder watcher (`src/integration/watcher.py`).
- [x] Teams webhook alert engine (`src/integration/alerts.py`).
- [x] Scheduled briefing CLI (`src/integration/briefing.py` + `cli.py`).
- [ ] AIMS live API / SFTP — deferred (Sprint 8).
- [ ] NOTAM auto-fetch — deferred (Sprint 10).

### Decision Support
- [x] Recovery options scoring (delay / swap_tail / cancel) per L1.
- [x] Pax reaccommodation ranking (intl > domestic > pax > depth).
- [x] Network stress test (multi-day what-if).
- [ ] Crew FDP / legality filter — deferred (Sprint 9).
- [ ] ML cancel-probability augmentation — deferred (Sprint 11).

### Infrastructure
- [x] GitHub Actions CI: `lint` + `test` matrix (3.10 / 3.11 / 3.12).
- [x] `pyproject.toml` + `ruff` + `ruff format` + `mypy` + pre-commit hooks.
- [x] Dockerfile (non-root) + docker-compose (named volume + healthcheck).
- [x] Structured JSON logging (stdlib only).
- [x] Performance test (`< 10 s` on 5,000 flights × 3 days × 5 events).

### Pilot Readiness
- [x] Pilot Run Book (`docs/PILOT_RUN_BOOK.md`) with Phase 0/1/2/3 gates.
- [x] BRD (`docs/BRD.md`).
- [x] PRD (`docs/PRD.md`).
- [x] Architecture doc (`docs/ARCHITECTURE.md`).
- [x] Production deploy doc (`docs/PRODUCTION_DEPLOY.md`).
- [x] Tabletop drill scenario, feedback form, phase 0 validation checklist.
- [ ] 5–10 real DayRepReport files validated (Sprint 4b — pending AIMS PIC).
- [ ] DM signs off Phase 0 acceptance gates.

## Milestone Timeline

| Date | Milestone |
|---|---|
| 26/04/2026 | MVP code complete (56 tests). |
| 26/04/2026 | E2E test passed (6/6). |
| 26/04/2026 | Sprint 1 merged — P0 hardening (64 tests). |
| 26/04/2026 | Sprint 2 merged — overnight cascade + Gantt (75 tests; e2e 6/6). |
| 26/04/2026 | Sprint 3 merged — multi-event + pax/cost + PDF (98 tests; e2e 6/6). |
| 26/04/2026 | Sprint 4 merged — pilot readiness (129 tests). |
| 26/04/2026 | Sprint 5 merged — production deploy (158 tests). |
| 26/04/2026 | Sprint 6 merged — integration & automation (183 tests). |
| 26/04/2026 | Sprint 7 merged — decision support (202 tests; e2e 3/3 after state-loss fix). |
| 26/04/2026 | PR #9 cumulative merge to default (203 tests; Python 3.13 fix included). |
| TBD | Sprint 4b — real-AIMS fixture validation. |
| TBD | Phase 0 — internal validation gates. |
| TBD | Phase 1 — shadowing. |
| TBD | Phase 2 — parallel run. |
| TBD | Phase 3 — live pilot or tabletop drill. |

## Baseline KPI Reference (sample dataset)

When validating any future change, the **HAN 14:00–18:00 / 2026-04-24** scenario on `data/sample/sample_dayrep_24042026.xlsx` must produce:

```
Total flights : 358
Affected      : 139
  Level 1     :  51
  Level 2     :  41
  Level 3+    :  47
Aircraft      :  26
Pax (est.)    : 27,827
Cost (est. USD): 1,898,730
```

A regression in any of these numbers means a Pass 1 / Pass 2 / boundary / pax-cost change.
