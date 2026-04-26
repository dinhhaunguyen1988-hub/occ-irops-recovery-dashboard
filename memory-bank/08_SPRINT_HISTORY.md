# 08 — Sprint History

> Chronological log of Sprints 1 → 7 + cumulative merge. One entry per sprint with the decisions, deliverables, test outcomes, and open follow-ups. This file is the canonical "how the product was built" record.

| Sprint | PR | Theme | Net source LOC | Tests added | CI |
|---:|---|---|---:|---:|---|
| 1 | [#2](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/2) | P0 hardening | ~250 | +8 (→64) | green |
| 2 | [#3](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/3) | P1 high-ROI | ~300 | +11 (→75) | green |
| 3 | [#4](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/4) | Multi-event + impact | ~750 | +23 (→98) | green |
| 4 | [#5](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/5) | Pilot readiness | ~500 | +31 (→129) | green |
| 5 | [#6](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/6) | Production deploy | ~400 | +29 (→158) | green |
| 6 | [#7](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/7) | Integration & automation | ~350 | +25 (→183) | green |
| 7 | [#8](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/8) | Decision support | ~300 | +19 (→202) | green |
| — | [#9](https://github.com/dinhhaunguyen1988-hub/occ-irops-recovery-dashboard/pull/9) | Cumulative merge to default | (no logic) | +1 (→203) | green |

---

## Sprint 1 — P0 Hardening (PR #2)

### Decisions

- **Stabilise before adding features.** The MVP had a `NameError` on the `affected` variable that fired whenever any flight was actually affected. Fix that first; everything else waits.
- **Pick tooling now, not later.** Adopt `ruff`, `black`-compatible `ruff format`, `mypy`, and pre-commit hooks. Add a CI lint stage in parallel with the test matrix.
- **No new business features in Sprint 1.** Surface row-level `data_quality_warning` (already produced by parser, never displayed) and add structured JSON logging — both are visibility upgrades, not features.

### Deliverables

- `app.py`: moved the `affected = ...` definition to immediately follow `detect_cascade()` so all downstream blocks (timeline, table, export) read a single, consistent DataFrame.
- New: `pyproject.toml`, `.pre-commit-config.yaml`, `requirements-dev.txt`.
- New: `src/logging_config.py` — stdlib JSON formatter; idempotent `setup_logging`.
- New `lint` job in `.github/workflows/ci.yml` (Python 3.11): `ruff check`, `ruff format --check`, `mypy src`.
- 8 new tests (total 64): AST regression guard for the `affected` bug, end-to-end Excel export check, JSON formatter shape.

### Open follow-ups

- Apply the env-config suggestion (install dev deps, register pre-commit hook, register lint/test/format/run-app commands) so future agent sessions don't re-discover the toolchain.

---

## Sprint 2 — Overnight Cascade + Visualisations (PR #3)

### Decisions

- **Overnight cascade is the highest-ROI feature.** Real IROPS rarely confine themselves to one date — a 14:00–18:00 closure today routinely strands aircraft into tomorrow's first wave.
- **Pass 1 must filter by `event.closure_date`.** Otherwise loading D + D+1 mis-flags next-day arrivals into HAN as L1.
- **Pass 2 must sort by `(flight_date, std)`.** Sorting by `std` alone breaks rotation continuity at midnight.
- **Adopt Plotly for visualisations.** The Gantt rotation chart is the most-requested OCC artefact; it must render as the same picture mental model that controllers already use.
- **Priority ranking should stay rule-based and transparent.** No ML. Score = `level_base + cascade_depth × 10 + intl_bonus`. The DM can defend it.

### Deliverables

- `src/cascade/cascade_detector.py`: closure-date filter in Pass 1; `(flight_date, std)` sort in Pass 2; new `cascade_depth` column.
- `src/parser/multi_file.py`: `parse_multiple_dayrep_reports`; warning prefix `file#N:`.
- `src/visualization/gantt.py`: Plotly Gantt; one row per affected aircraft; level-coloured sectors; closure shaded band; overnight-aware bars.
- `app.py`: multi-file uploader; what-if simulator (sidebar checkbox + alt window inputs; diff panel `Newly Affected / No Longer Affected / Unchanged`).
- `src/cascade/ranking.py::compute_priority` — new module, transparent score.
- 11 new tests (total 75): overnight cascade D + D+1 case, what-if subset window, priority ranking (intl bonus), Gantt rendering smoke.

### End-to-end test (Sprint 2 e2e)

- T1 single-file regression vs Sprint 1 baseline → pass.
- T2 priority-ranked table → pass.
- T3 Plotly Gantt + closure band → pass.
- **T4 multi-file overnight cascade (flagship)** → pass.
- T5 What-if 15:00–16:00 (subset) → pass (`Newly Affected = 0`, `No Longer Affected > 0`).
- T6 Excel export → pass.

### Open follow-ups

- The `data/sample/generate_sample_dayrep.py` docstring still cites the *original* baseline KPIs (`87/39/23/25/24`). Real generator output is `139/51/41/47/26`. Fix in Sprint 3.

---

## Sprint 3 — Multi-Event + Impact Quantification (PR #4)

### Decisions

- **Bundle three improvements (A multi-event, B pax/cost impact, C PDF + map) into one PR.** User opted for a larger PR because the three are mutually reinforcing — pax/cost impact only matters if multi-event closures are accurately detected, and PDF briefing only matters if there is a quantified result.
- **Multi-event must be union-of-masks in Pass 1, single Pass 2.** No per-event Pass 2 — that would double-count downstream sectors when two events affect the same aircraft.
- **Closure type is cosmetic.** `airport_closed / runway_closed / atc_flow` is a label and a colour; no logic branching. This keeps the L1 detection rule (BR-01) untouched.
- **Pax / cost defaults must be config-driven.** Hard-coding 0.85 load factor and $0.50/pax/min is fine for v1, but the values must be overridable (Sprint 5 settings UI later).
- **Network map needs a built-in airport coordinate table.** No live geocoding lookups; ship the coords for 35+ VN/intl airports.

### Deliverables

- `src/cascade/cascade_detector.py::detect_cascade_multi` — multi-event entry point. Original `detect_cascade` becomes a thin shim → byte-for-byte same KPIs for single-event input.
- `src/impact/pax_estimator.py` — `est_pax`, `est_cost_usd`. Sample HAN run: 27,827 pax, $1,898,730.
- `src/export/pdf_briefing.py` — reportlab 1-page PDF. Header + 6 KPIs + Top-10 priority flights + footer disclaimer.
- `src/visualization/map_view.py` + `airport_coords.py` — Plotly scattergeo.
- Top-10 cards in `app.py`: by pax, by cost, by cascade depth.
- Refresh `data/sample/generate_sample_dayrep.py` docstring baseline `139/51/41/47/26`.
- 23 new tests (total 98).

### End-to-end test (Sprint 3 e2e)

- T1 single-event HAN baseline (regression vs Sprint 2): `358 / 139 / 51 / 41 / 47 / 26`, pax `27,827`, cost `$1,898,730` → pass.
- **T2 multi-event HAN+HPH union (flagship)**: KPIs jump 139→143, L1 51→54, L3+ 47→48, Aircraft 26→27, pax 28,811, cost $1,988,880; **L2 stays 41** (no double-count) → pass.
- T3 closure type cosmetic-only invariant (Runway closed): KPIs identical to T1 → pass.
- T4 Top-10 highlight cards → pass.
- T5 1-page PDF briefing (3,559 bytes, magic %PDF, 1 page, 10 flight rows) → pass.
- T6 network map → pass.

---

## Sprint 4 — Pilot Readiness (PR #5)

### Decisions

- **Pilot blockers fall into 4 buckets**: explainability, parser robustness, performance, validation. Address all four in one sprint so Phase 0 can begin without further engineering.
- **Discrepancy explainer must be free-text and human-readable.** Numerical levels are not enough — DMs need a sentence they can paste into an email.
- **Performance budget is hard.** 5,000 flights × 3 days × 5 events must complete in < 10 s. Profile-and-fix, not "we'll see in prod".
- **Validation dashboard accepts a CSV `actuals.csv`** with `(flight_no, actual_outcome, optional flight_date)`. No bespoke schema; AIMS PIC can produce the file from any spreadsheet.
- **Sprint 4b is a deliberate split.** Real-AIMS regression fixtures wait on data the developer doesn't have. Document the split as a deferred sprint, don't pretend Sprint 4 covers it.

### Deliverables

- `src/cascade/cascade_detector.py`: builds `impact_explanation` per row. L1 references the event(s) that triggered it; L2/3+ references the rotation root and hop count.
- `src/parser/dayrep_parser.py`: 25+ alias headers (Vietnamese accented, NFC + NFD); `normalize_reg` covers `VN A517 / VN/A517 / VNA517 / VN-A517`.
- `src/parser/time_parser.py`: handles Excel fractional float (0.5833 → 14:00), `datetime.time`, `+1`/`+2` markers with optional space, trailing `.0`.
- `tests/test_performance.py`: synthetic fixture, asserts < 10 s. Local: 1.56 s.
- `src/validation/validator.py` + UI section "Validation vs Actuals": confusion matrix, per-level precision / recall / F1, "Affected (any)" aggregate, coverage table.
- `docs/PILOT_RUN_BOOK.md`: pre-flight check, daily run procedure, T+24h validation flow, failure-mode table, performance budget, fixture-update process; explicit acceptance gates for Phase 1 / 2 / 3.
- 31 new tests (total 129).

### Open follow-ups

- Sprint 4b pending real DayRepReport files from AIMS PIC.
- Recommend gating CI on `pytest --cov` ≥ 85% for cascade + decision modules (not yet done).

---

## Sprint 5 — Production Deploy (PR #6)

### Decisions

- **Yaml-file users for MVP.** User explicitly chose this over SSO/OIDC for the pilot. Migrate later.
- **SQLite is enough.** No need for Postgres at single-tenant scale; the named volume in Docker compose handles persistence.
- **Schema is additive.** All new fields go in JSON columns inside `kpis` / `event_config`. No migration tool required.
- **`OCC_AUTH_DISABLED=1` is honoured but loud.** A visible amber sidebar banner reminds operators that the bypass is active.
- **DM-only sections** (Settings, Audit log) are gated by `user.role == "dm"`, not by hidden routes.

### Deliverables

- `src/auth/users.py`: `streamlit-authenticator 0.3.x` + bcrypt; `require_login()`; `is_auth_disabled()`.
- `src/persistence/{db,runs,audit,settings}.py`: 3-table SQLite (`runs`, `settings`, `audit_events`).
- `app.py`: 3 new expanders — Recent runs (history), Settings (DM-only), Audit log (DM-only) with CSV download.
- `Dockerfile`: drop to UID 1000 non-root; `docker-compose.yml`: named volume + healthcheck on `/_stcore/health`.
- `docs/PRODUCTION_DEPLOY.md`: deployment steps, bcrypt hash generation, DB backup, TLS guidance.
- 29 new tests (total 158).

### Open follow-ups

- Document retention policy for `data/runs.db` and `audit_events`. Compliance question Q5 in PRD §9.

---

## Sprint 6 — Integration & Automation (PR #7)

### Decisions

- **Build everything config-driven.** AIMS PIC may not have credentials yet — code paths must skip silently if `OCC_TEAMS_WEBHOOK_URL` / `OCC_FOLDER_WATCH_DIR` are unset.
- **i18n is a UI concern only.** Never translate canonical column names or log keys.
- **Folder watcher is the AIMS bridge for now.** Drop file in inbox → trigger CLI run → produce PDF + persist run. No live API until Sprint 8.
- **Threshold alerts must be aggregated KPI only.** Never include flight-level pax names in webhook payload (BR-14).

### Deliverables

- `src/i18n/translator.py` + `locales/{vi,en}.yaml`: locale toggle in header.
- `src/integration/watcher.py`: poll-based folder watcher.
- `src/integration/alerts.py`: Teams webhook alert engine; payload limited to KPI dict.
- `src/integration/briefing.py` + `cli.py`: scheduled PDF briefing entry point.
- 25 new tests (total 183).

### Open follow-ups

- NOTAM auto-fetch deferred (Sprint 10) — needs official VATM / ICAO endpoint.
- SMTP email sending for `briefing.py` is implemented but disabled pending corporate SMTP details.

---

## Sprint 7 — Decision Support (PR #8)

### Decisions

- **Recovery options stay rule-based and transparent.** `score = w_pax × pax + w_cost × cost + w_op × op_penalty`. Defaults are minimal, tunable, and labelled. No ML.
- **`swap_tail` requires a free aircraft on the same day.** If there is none, omit that row rather than fabricate one.
- **Pax reaccommodation ranking respects regulatory norms** — intl > domestic, then pax count, then cascade depth. Rationale text rendered for every row.
- **Stress test replays the same closure config across N days.** Multi-airport closures replicate per day; aggregate KPI shows worst-day and total.
- **The result page must survive widget interactions.** Found and fixed a Streamlit state-loss bug during T3: `Run stress test` button click triggered rerun → sidebar `Run Analysis` button returned `False` (Streamlit buttons return `True` only on the click frame) → `if not run_analysis: st.stop()` fired → entire result page wiped. Fix: persist intent in `st.session_state["analysis_active"]` and add an AST regression guard.

### Deliverables

- `src/decision/recovery.py`: `compute_recovery_options(affected, **kwargs)`. Output table: 3 × |L1| rows in baseline.
- `src/decision/reaccommodation.py`: `rank_for_reaccommodation(affected)`.
- `src/decision/stress.py`: `network_stress_test(df, events, n_days)`.
- `app.py`: 2 new expanders — "Decision support" (recovery + reaccom) and "Network stress test (multi-day what-if)".
- `app.py`: state-loss fix `d185b11` — `analysis_active` in `st.session_state`.
- `tests/test_app_smoke.py::test_analysis_state_persists_via_session_state` — AST-level regression guard.
- 19 new tests (total 202).

### End-to-end test (Sprint 7 e2e)

- T1 Recovery: flight 198 → `swap_tail (1498) < delay (14213) < cancel (21503)` → pass.
- T2 Reaccom: rank 1 = `145 / VN-A534 / HKG→VDH / pax 259 / "International; High pax load"` → pass.
- T3 Stress test 3-day HAN: per-day rows = 3, totals `417 / 83,481 / $5,696,190`, worst-day `$1,898,730` → pass (after state-loss fix).

### Escalation (resolved in this sprint)

- Streamlit state-loss bug fixed in commit `d185b11`. CI 4/4 green after fix. Pattern locked in by `tests/test_app_smoke.py`.

---

## PR #9 — Cumulative Merge to Default Branch

### Why this PR exists

Sprint 1–7 PRs were stacked. When the user requested all PRs to be merged so they could test locally, the agent ran `gh pr merge --auto` on each PR sequentially. GitHub's auto-merge merged each stacked PR into its **parent branch**, not into the repo's default branch. The result was that the default branch (`devin/1777174450-occ-irops-dashboard`) only contained Sprint 1 — the user's local clone hit Python 3.13 LogRecord errors from Sprint 1's `extra={"filename": ...}` (which collides with `LogRecord.filename`).

### Fix

PR #9 takes Sprint 7's branch tip (which contains the cumulative result of Sprints 2 → 7) and merges it directly into the default branch with `-X ours` to resolve trivial conflicts in favour of Sprint 7's evolved files. One follow-up commit `eddeb02` removed two duplicate insertions left over from the merge (a redundant `setup_logging()` call and a stale `parse_completed` log that referenced the deleted `file_hash` singular variable).

### Side effect — Python 3.13 fix

Sprint 2 had already renamed the structured-logging key from `filename` → `filenames` (because multi-file upload added a list). That change was therefore part of PR #9's payload. After PR #9 merged, the dashboard runs cleanly on Python 3.13 in addition to 3.10–3.12.

### Process learning

The agent should have used `--merge` instead of `--auto`, and merged stacked PRs in order so each merge updated the next PR's base correctly. See [09_LESSONS_LEARNED.md](./09_LESSONS_LEARNED.md#stacked-pr-merge-procedure).
