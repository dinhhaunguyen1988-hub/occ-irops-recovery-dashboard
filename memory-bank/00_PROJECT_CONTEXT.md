# 00 — Project Context

## 1. Project Name

**OCC IROPS Recovery Dashboard**

## 2. Business Context

OCC needs a lightweight tool to support disruption impact analysis during IROPS, especially airport closure scenarios.

The tool should help OCC quickly identify:

- Directly affected flights.
- Downstream affected rotations.
- Aircraft registration chains.
- Impact levels.
- Summary KPIs.
- Exportable briefing output for Duty Manager / management.

## 3. MVP Scenario

The standard demo and tabletop scenario is:

| Item | Value |
|---|---|
| Airport | HAN |
| Closure start | 14:00 |
| Closure end | 18:00 |
| Date | 24/04/2026 |
| Boundary logic | Start inclusive, end exclusive |
| Rule | `time >= closure_start AND time < closure_end` |

## 4. MVP Input

Primary input file:

- AIMS `DayRepReport`

The parser must handle real AIMS exports, not only ideal sample data.

## 5. MVP Output

Expected MVP output includes:

- List of affected flights.
- Impact level: Level 1, Level 2, Level 3+.
- Actual numeric level stored internally.
- Aircraft registration.
- Route.
- STD / STA.
- Reason for impact.
- Exportable Excel report.
- Warnings for parser or data limitations.

## 6. Users and Roles

| Role | Responsibility |
|---|---|
| Developer / Code Agent | Build parser, cascade detector, UI, export, tests |
| AIMS PIC | Provide real DayRepReport, validate AIMS logic, coordinate pilot |
| OCC Controller | Run tool, review output, compare with operational understanding |
| Duty Manager | Use output as briefing input and make final operational decisions |
| Management | Review business value after pilot |

## 7. Core Framing

The correct framing for adoption:

> This is an automated AIMS report reader that reads the AIMS DayRepReport, calculates the impact structure, and prepares a review list for OCC.

Avoid presenting it as:

- AI decision-making.
- Automatic aircraft recovery.
- Replacement for AIMS.
- Replacement for OCC Controller or Duty Manager judgment.
