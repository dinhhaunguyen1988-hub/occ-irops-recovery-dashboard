# 00 — Project Context

## 1. Project Name

**OCC IROPS Recovery Dashboard**

## 2. Business Context

OCC needs a lightweight tool to support disruption impact analysis during IROPS, especially airport closure scenarios. After Sprints 1 → 7 the tool covers single- and multi-event closures, pax/cost quantification, decision support (recovery options, pax reaccommodation, network stress test), production deploy (auth + persistence + Docker), integration & automation hooks (folder watcher, Teams alerts, scheduled briefing, i18n VN/EN), and a validation dashboard for predicted-vs-actual confusion matrix.

The framing remains:

> An automated AIMS report reader that reads the AIMS DayRepReport, calculates the impact structure, ranks recovery options, and prepares a review list for OCC. The Duty Manager remains the final decision maker.

Avoid presenting the tool as AI / auto-recovery / AIMS replacement.

## 3. Reference Scenario (sample data)

| Item | Value |
|---|---|
| Airport | HAN |
| Closure start | 14:00 |
| Closure end | 18:00 |
| Date | 24/04/2026 |
| Boundary logic | Start inclusive, end exclusive (`time >= start AND time < end`) |
| Closure-date filter | Pass 1 restricts L1 to `event.closure_date` |
| Sample file | `data/sample/sample_dayrep_24042026.xlsx` |

### Baseline KPIs (memorise — used as regression assertion)

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

### Multi-event reference (HAN + HPH)

Adding a second event for HPH on the same date and window changes the KPI to `143 / 54 / 41 / 48 / 27`, pax `28,811`, cost `$1,988,880`. Crucially, **L2 stays 41** — that is the proof-of-correctness for the multi-event union-of-masks Pass 1 + single Pass 2 design.

## 4. Inputs

- **Primary**: AIMS `DayRepReport` exported as `.xlsx` (single or multiple files).
- **Secondary (validation)**: `actuals.csv` with columns `flight_no, actual_outcome, optional flight_date`.
- **Configuration**: `config/users.yaml` (auth), settings stored in SQLite via DM-only Settings UI.

## 5. Outputs

- KPI bar (7 metrics).
- Affected flight table with `level`, `cascade_depth`, `priority_score`, `est_pax`, `est_cost_usd`, `impact_explanation`, `data_quality_warning`.
- Plotly Gantt rotation chart.
- Plotly scattergeo network map.
- Top-10 highlight cards (pax / cost / depth).
- What-if simulator panel.
- Decision support: recovery options table + pax reaccommodation ranking.
- Network stress test (multi-day what-if).
- Validation vs Actuals confusion matrix.
- 1-page PDF briefing.
- 5-sheet Excel workbook.
- Recent runs (history).
- Audit log (DM-only, CSV downloadable).

## 6. Users and Roles

| Role | App role | Responsibility |
|---|---|---|
| Developer / Code Agent | n/a | Build and maintain. |
| AIMS PIC | `dm` (Phase 0) → `viewer` later | Validate parser, lead Phase 0 acceptance. |
| OCC Controller | `viewer` (default) or `dm` if delegated | Run tool during shift. |
| Duty Manager | `dm` | Final decision authority. |
| Senior Manager | n/a (PDF / email recipient) | Read briefings. |

## 7. Core Framing

> Automated AIMS report reader → structured impact list → decision support suggestions → DM decides.

The tool never executes a recovery action. Every estimated number is labelled `(est.)`. The DM is always in the loop.

## 8. Current Boundaries (post-Sprint 7)

### What the tool **does** today

- Single- and multi-event airport closure impact analysis (up to 5 simultaneous events).
- Overnight cascade across multi-day data.
- Quantified pax and cost impact (rule-based estimator, configurable load factor + cost rate).
- Recovery options scoring (delay / swap_tail / cancel) with transparent formula.
- Pax reaccommodation ranking (intl > domestic > pax > cascade depth).
- Network stress test (multi-day replay).
- What-if alternate window simulator.
- Validation vs actuals (confusion matrix + per-level precision/recall/F1).
- Auth (yaml-file users, bcrypt, 2 roles), SQLite persistence, audit log, Docker compose.
- AIMS folder watcher, Teams alert engine, scheduled briefing CLI, i18n VN/EN.

### What the tool **does NOT** do (deferred)

- No live AIMS API / SFTP integration (folder watcher is the bridge).
- No crew FDP / legality enforcement on recovery options.
- No ML cancel-probability prediction.
- No NOTAM auto-fetch.
- No SSO / OIDC.
- No mobile / tablet-optimised UI.
- No multi-tenant SaaS deployment.

For the deferred-sprint catalogue see [PRD §7](../docs/PRD.md#7-future-sprints-deferred-not-in-current-scope).

## 9. Related Docs

- [BRD](../docs/BRD.md) — business case, stakeholders, business rules, success metrics.
- [PRD](../docs/PRD.md) — product spec, user stories, functional / non-functional requirements.
- [Architecture](../docs/ARCHITECTURE.md) — module layout, data flow, deployment.
- [Pilot Run Book](../docs/PILOT_RUN_BOOK.md) — daily run procedure + acceptance gates.
- [Production Deploy](../docs/PRODUCTION_DEPLOY.md) — Docker / auth / TLS guidance.
- [Sprint History](./08_SPRINT_HISTORY.md) — chronological log.
- [Lessons Learned](./09_LESSONS_LEARNED.md) — engineering patterns.
