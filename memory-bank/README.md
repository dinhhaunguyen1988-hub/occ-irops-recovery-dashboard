# OCC IROPS Recovery Dashboard — Memory Bank

> Source-of-truth knowledge base for the project. Read this folder before touching the code or running the tool. Updated end of Sprint 7 (cumulative merge PR #9).

## 1. Purpose

This Markdown pack is the agent-ready project knowledge base. It is designed so a future coding agent or developer can understand the project context, business rules, implementation patterns, and the deliverable history of Sprints 1 → 7 without reading any prior chat or PR description.

The complementary **product / business documentation** lives in `../docs/`:
- [BRD](../docs/BRD.md) — Business Requirements Document.
- [PRD](../docs/PRD.md) — Product Requirements Document.
- [Architecture](../docs/ARCHITECTURE.md) — Technical layout & deployment.
- [Pilot Run Book](../docs/PILOT_RUN_BOOK.md), [Production Deploy](../docs/PRODUCTION_DEPLOY.md), and other operator docs.

## 2. Recommended Read Order

| # | File | When to read |
|---:|---|---|
| 1 | [`00_PROJECT_CONTEXT.md`](./00_PROJECT_CONTEXT.md) | Always — first 5 minutes. |
| 2 | [`ACTIVE_CONTEXT.md`](./ACTIVE_CONTEXT.md) | Always — current state of the project. |
| 3 | [`PROGRESS.md`](./PROGRESS.md) | Always — done / pending checklist + milestones. |
| 4 | [`08_SPRINT_HISTORY.md`](./08_SPRINT_HISTORY.md) | Always — chronological sprint log. |
| 5 | [`09_LESSONS_LEARNED.md`](./09_LESSONS_LEARNED.md) | Before writing code — engineering patterns + anti-patterns. |
| 6 | [`TECH_STACK.md`](./TECH_STACK.md) | Before installing dependencies. |
| 7 | [`01_CASCADE_DETECTION_LOGIC.md`](./01_CASCADE_DETECTION_LOGIC.md) | Before modifying `src/cascade/`. |
| 8 | [`02_DATA_PARSING_STRATEGY.md`](./02_DATA_PARSING_STRATEGY.md) | Before modifying `src/parser/`. |
| 9 | [`03_PILOT_ROLLOUT_PLAN.md`](./03_PILOT_ROLLOUT_PLAN.md) | Before pilot activities (also see `../docs/PILOT_RUN_BOOK.md`). |
| 10 | [`04_DEFINITION_OF_DONE.md`](./04_DEFINITION_OF_DONE.md) | Before declaring a feature done. |
| 11 | [`05_AGENT_IMPLEMENTATION_GUIDE.md`](./05_AGENT_IMPLEMENTATION_GUIDE.md) | Before opening a new sprint. |
| 12 | [`06_AGENT_PROMPT.md`](./06_AGENT_PROMPT.md) | If you need to bootstrap an agent. |
| 13 | [`07_TEST_CASES_AND_ACCEPTANCE.md`](./07_TEST_CASES_AND_ACCEPTANCE.md) | When extending the test suite. |
| 14 | [`99_MASTER_AGENT_CONTEXT.md`](./99_MASTER_AGENT_CONTEXT.md) | Optional one-shot import for an agent. |

## 3. File Categories

```
Always-read (orientation):
  00_PROJECT_CONTEXT.md
  ACTIVE_CONTEXT.md
  PROGRESS.md
  08_SPRINT_HISTORY.md  ← new (Sprints 1-7 log)

Patterns & anti-patterns:
  09_LESSONS_LEARNED.md ← new (engineering patterns)

Domain logic:
  01_CASCADE_DETECTION_LOGIC.md
  02_DATA_PARSING_STRATEGY.md

Process & rollout:
  03_PILOT_ROLLOUT_PLAN.md
  04_DEFINITION_OF_DONE.md
  07_TEST_CASES_AND_ACCEPTANCE.md

Agent bootstrap:
  05_AGENT_IMPLEMENTATION_GUIDE.md
  06_AGENT_PROMPT.md
  99_MASTER_AGENT_CONTEXT.md

Project meta:
  README.md (this file)
  TECH_STACK.md
```

## 4. Core Project Principle

Do not pitch this as AI or optimization. Pitch it as an **automated AIMS report reader**:

> Read DayRepReport(s) from AIMS → parse schedule data → detect airport-closure cascade impact (single or multi-event, with overnight propagation) → quantify pax + cost → suggest recovery options and pax reaccommodation order → export PDF / Excel for OCC review.

The Duty Manager remains the final decision maker. Recovery options, reaccommodation rankings, and stress-test outputs are **suggestions only** — the tool never executes a recovery action. Every estimated number is labelled `(est.)`.

## 5. Boundaries (post-Sprint 7)

### Does today

- Single- and multi-event closure detection (up to 5 simultaneous events).
- Overnight cascade across multi-day data.
- Quantified pax + cost.
- Recovery options scoring (delay / swap_tail / cancel).
- Pax reaccommodation ranking.
- Network stress test (multi-day what-if).
- What-if alternate window simulator.
- Validation vs actuals.
- Auth + persistence + audit log + Docker compose.
- Folder watcher + Teams alerts + scheduled briefing + i18n VN/EN.

### Deferred

- Live AIMS API / SFTP integration → Sprint 8.
- Crew FDP filter → Sprint 9.
- NOTAM auto-fetch → Sprint 10.
- ML cancel-probability → Sprint 11.
- SSO / OIDC → Sprint 12.

## 6. Reference KPIs (sample dataset)

The HAN 14:00–18:00 / 2026-04-24 baseline on `data/sample/sample_dayrep_24042026.xlsx` must always produce:

```
Total : 358   Affected : 139
L1: 51   L2: 41   L3+: 47   Aircraft: 26
Pax (est.) : 27,827   Cost (est. USD) : 1,898,730
```

Any deviation = a regression. Investigate before merging.

## 7. Output Expected from an Agent

When an agent picks up this project, it should be able to help produce or update:

- Parser (real AIMS quirks: NFC + NFD VN headers, REG variants, time formats).
- Cascade detector (single + multi-event, overnight Pass 2 ordering).
- Decision support (recovery scoring, reaccom ranking, stress test).
- Validation dashboard.
- Streamlit UI (with state persistence pattern).
- Excel + PDF exports.
- SQLite persistence (runs / settings / audit).
- Auth + Docker compose + healthcheck.
- Integrations (folder watcher, alerts, briefing, i18n).
- Tests (adversarial, exact-numeric assertions).
- Pilot artefacts (run book, drill scenario, feedback form).
