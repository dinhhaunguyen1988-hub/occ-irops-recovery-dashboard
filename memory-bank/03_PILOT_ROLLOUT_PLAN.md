# 03 — Pilot Rollout Plan

## 1. Pilot Principle

The project should be piloted carefully to support real OCC adoption.

Do not introduce the tool as AI, optimization, or automated decision-making.

Use this framing:

> The tool is an automated AIMS report reader that reads the DayRepReport, calculates affected flights, and prepares a structured list for review.

Duty Manager remains final decision maker.

## 2. Pilot Phases Overview

| Phase | Name | Duration | Main objective |
|---:|---|---|---|
| 0 | Internal Validation | 1 week before pilot | Confirm the tool works with real AIMS data |
| 1 | Shadowing | Week 1–2 | Let OCC Controller learn workflow |
| 2 | Parallel Run | Week 3–4 | Compare tool output with real process |
| 3 | Live Pilot | Week 5–6 | Evaluate actual business value |

## 3. Phase 0 — Internal Validation

### Participants

- Developer
- AIMS PIC

No OCC end user yet.

### Objective

Validate the tool against real DayRepReport files before any OCC user handles it.

### Activities

| Activity | Details |
|---|---|
| Collect real DayRepReport files | Use 5–10 recent operational days |
| Run parser | Record errors, warnings, edge cases |
| Compare with AIMS | Validate rotation chain and affected flights |
| Fix parser edge cases | Resolve all discovered data variants |
| Validate sample KPI | Confirm expected KPI values from sample |
| Document discrepancies | Record all mismatch cases |

### Pass criteria

| Pass condition | Fail condition |
|---|---|
| Tool loads all sample DayRepReport files | Tool crashes with any real file |
| Rotation match rate > 95% | Match rate < 90% |
| Expected sample KPI is correct | KPI differs by more than 5% |
| All known time formats parse correctly | Any known time format fails |

## 4. Phase 1 — Shadowing

### Duration

Week 1–2.

### Participants

- 1 OCC Controller
- 1 AIMS PIC

No Duty Manager pressure yet.

### Activities

| Item | Details |
|---|---|
| Frequency | Daily during working days for 2 weeks |
| Main task | Load same-day DayRepReport and run hypothetical HAN closure scenario |
| Comparison | OCC Controller compares output with own operational mental model |
| Feedback | Fill 5-minute feedback form after each session |
| Process impact | No change to current operation |

### Feedback form

| Question | Scale |
|---|---|
| Can you load file and run tool by yourself? | Yes / No / Need support |
| Does output match your understanding of impact? | 1–5 |
| Is UI easy to read and understand? | 1–5 |
| What is confusing or missing? | Free text |
| Would you use this tool in real IROPS? | Yes / Maybe / No |

### Phase 1 pass criteria

- OCC Controller can run the tool without support after week 1.
- Average satisfaction score is at least 3.5/5.

## 5. Phase 2 — Parallel Run

### Duration

Week 3–4.

### Participants

- OCC Controller
- Duty Manager as observer

### Objective

Use the tool in parallel with the current AIMS/OCC process.  
The tool does not replace official decisions.

### Trigger

Use when there is a real minor delay or small disruption.

### Activities

| Item | Details |
|---|---|
| Process | OCC runs tool in parallel with existing workflow |
| Timing | Record time from disruption notice to tool output |
| Comparison | Compare tool recommendation with Duty Manager decision |
| Restriction | Tool output is not official decision basis yet |

### Metrics

| Metric | Baseline | Target |
|---|---|---|
| Time to identify affected flights | Measured in Phase 0 | < 5 minutes |
| Time to prepare Duty Manager briefing | Measured in Phase 0 | < 15 minutes |
| Tool output error vs AIMS | — | < 5% |
| Recommendation match with DM decision | — | > 70% |
| OCC Controller satisfaction | — | ≥ 4.0/5 |

### Phase 2 pass criteria

- Tool output generated in under 5 minutes.
- Duty Manager says output is useful or very useful.
- Recommendation match rate is above 70%.

## 6. Phase 3 — Live Pilot

### Duration

Week 5–6.

### Participants

- Full OCC team
- Duty Manager
- AIMS PIC / Developer support

### Rule

If real IROPS happens, use the tool as primary impact analysis support.  
If no real IROPS happens, conduct mandatory tabletop drill.

## 7. Tabletop Drill Scenario

### Scenario

HAN closure from 14:00 to 18:00 on 24/04/2026.

### Format

| Item | Duration |
|---|---:|
| Setup | 30 minutes |
| Scenario handling | 45 minutes |
| Debrief | 15 minutes |
| Total | 1.5 hours |

### Facilitator

AIMS PIC or developer facilitates.  
Duty Manager should act as the real decision maker, not facilitator.

### Script

| Time | Event | Required action |
|---|---|---|
| T+0 | Receive HAN closure notice 14:00–18:00 | Load DayRepReport and run tool |
| T+5 | Tool output is ready | OCC reviews affected flights and forwards to DM |
| T+10 | DM reviews decision list | DM approves/rejects recommendations |
| T+15 | Export Excel report | Prepare management briefing |
| T+30 | Management briefing | Use Excel output from tool |

## 8. Pilot Risks and Mitigation

| Risk | Severity | Mitigation |
|---|---|---|
| DayRepReport format changes suddenly | High | Test many real files in Phase 0; show clear header-detection error |
| Duty Manager has no time during real IROPS | Very high | Mandatory tabletop drill before live usage |
| OCC Controller does not trust output | Medium | Show audit trail: why flight X is Level 1, why Y is Level 2 |
| Scope creep during pilot | High | Limit pilot to Airport Closure only |
| Tool runs slowly with large file | Low | Performance test with 500+ rows before Phase 1 |
| User resistance due to workflow change | Medium | Frame as automated AIMS reader, not replacement for AIMS or DM judgment |
