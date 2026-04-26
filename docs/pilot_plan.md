# Pilot Rollout Plan — OCC IROPS Recovery Dashboard

## Pilot Principle

The tool is an automated AIMS report reader that reads the DayRepReport, calculates affected flights, and prepares a structured list for review.

Duty Manager remains final decision maker.

## Pilot Phases

| Phase | Name | Duration | Objective |
|---:|---|---|---|
| 0 | Internal Validation | 1 week | Confirm tool works with real AIMS data |
| 1 | Shadowing | Week 1–2 | OCC Controller learns workflow |
| 2 | Parallel Run | Week 3–4 | Compare tool output with real process |
| 3 | Live Pilot | Week 5–6 | Evaluate actual business value |

## Phase 0 — Internal Validation

### Participants
- Developer + AIMS PIC only

### Activities
- Collect 5–10 real DayRepReport files
- Run parser and record errors/warnings
- Compare with AIMS rotation chains
- Fix parser edge cases
- Validate sample KPI results

### Pass Criteria
- Tool loads all sample files without crash
- Rotation match rate > 95%
- All known time formats parse correctly

## Phase 1 — Shadowing

### Participants
- 1 OCC Controller + 1 AIMS PIC

### Activities
- Daily run for 2 weeks with same-day DayRepReport
- HAN closure hypothetical scenario
- OCC Controller compares with mental model
- 5-minute feedback form after each session

### Feedback Form

| Question | Scale |
|---|---|
| Can you load file and run tool by yourself? | Yes / No / Need support |
| Does output match your understanding? | 1–5 |
| Is UI easy to read? | 1–5 |
| What is confusing or missing? | Free text |
| Would you use this in real IROPS? | Yes / Maybe / No |

### Pass Criteria
- Controller can run tool without support after week 1
- Average satisfaction ≥ 3.5/5

## Phase 2 — Parallel Run

### Participants
- OCC Controller + Duty Manager (observer)

### Activities
- Use tool in parallel with existing AIMS/OCC process
- Record time from disruption notice to tool output
- Compare tool output with DM decision

### Metrics

| Metric | Target |
|---|---|
| Time to identify affected flights | < 5 minutes |
| Time to prepare DM briefing | < 15 minutes |
| Tool output error vs AIMS | < 5% |
| Recommendation match with DM | > 70% |
| Controller satisfaction | ≥ 4.0/5 |

## Phase 3 — Live Pilot

### Participants
- Full OCC team + Duty Manager + AIMS PIC / Developer

### Rule
If real IROPS happens, use tool as primary impact analysis support.
If no real IROPS, conduct mandatory tabletop drill.

## Tabletop Drill Scenario

HAN closure from 14:00 to 18:00 on 24/04/2026.

| Time | Event | Action |
|---|---|---|
| T+0 | Receive HAN closure notice | Load DayRepReport and run tool |
| T+5 | Tool output ready | OCC reviews and forwards to DM |
| T+10 | DM reviews | DM approves/rejects recommendations |
| T+15 | Export Excel | Prepare management briefing |
| T+30 | Management briefing | Use Excel output from tool |

## Phase 0 Validation Checklist

- [ ] 5–10 real DayRepReport files collected
- [ ] Parser processes all files
- [ ] Rotation chains match AIMS
- [ ] KPI values verified
- [ ] Known discrepancies documented
- [ ] Time format edge cases resolved
- [ ] REG normalization validated
