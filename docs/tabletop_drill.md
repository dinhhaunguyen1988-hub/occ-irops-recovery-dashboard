# Tabletop Drill Script — OCC IROPS Recovery Dashboard

## Drill Overview

| Item | Value |
|---|---|
| Scenario | HAN airport closure |
| Closure window | 14:00 – 18:00 local |
| Date | 24/04/2026 |
| Total duration | 1.5 hours |
| Required participants | OCC Controller, Duty Manager, AIMS PIC / Developer |

## Purpose

Validate the OCC IROPS Recovery Dashboard in a controlled scenario before live deployment. The Duty Manager acts as the real decision maker, not facilitator.

## Pre-Drill Preparation

### Facilitator (AIMS PIC or Developer)

- [ ] Prepare DayRepReport file for 24/04/2026 (use sample or real data)
- [ ] Ensure dashboard is running and accessible
- [ ] Print feedback forms for each participant
- [ ] Prepare backup Excel export in case of tool issues
- [ ] Brief participants on drill format (5 minutes before start)

### Environment

- [ ] Dashboard running on OCC workstation
- [ ] DayRepReport file ready for upload
- [ ] Internet/network connectivity confirmed
- [ ] Printer available for Excel export

---

## Drill Timeline

### T-5 min — Briefing (5 minutes)

**Facilitator reads aloud:**

> "We are running a tabletop drill to test the OCC IROPS Recovery Dashboard.
> The scenario is a hypothetical HAN airport closure from 14:00 to 18:00 today.
> The OCC Controller will use the tool to analyze impact.
> The Duty Manager will review the output and make decisions as in real IROPS.
> This is not a test of people — it is a test of the tool."

---

### T+0 — Receive Closure Notice (Setup: 30 minutes)

**Facilitator announces:**

> "NOTAM received: HAN airport closed from 14:00 to 18:00 due to [military exercise / weather / runway maintenance]. All arrivals and departures at HAN are suspended during this period."

**OCC Controller actions:**

1. [ ] Open the OCC IROPS Recovery Dashboard
2. [ ] Upload the DayRepReport file
3. [ ] Enter closure parameters:
   - Airport: HAN
   - Date: 24/04/2026
   - Start: 14:00
   - End: 18:00
4. [ ] Click "Run Analysis"
5. [ ] Review data quality warnings (if any)

**Facilitator observes:**

- Can the Controller complete upload and analysis without assistance?
- How long from upload to results?
- Any confusion or errors?

---

### T+5 — Tool Output Ready (Scenario Handling: 45 minutes)

**OCC Controller reviews:**

1. [ ] Check KPI summary
   - Total flights affected?
   - How many Level 1 (direct)?
   - How many Level 2 (downstream)?
   - How many Level 3+ (extended cascade)?
   - How many aircraft affected?

2. [ ] Review affected flights table
   - Are the flights realistic and expected?
   - Do the impact reasons make sense?

3. [ ] Check aircraft rotation view
   - Select 2–3 affected aircraft
   - Verify the cascade chain is logical

**Discussion questions (Facilitator leads):**

- "Does this list match your operational understanding?"
- "Are there any flights you expected to see but don't?"
- "Are there any flights listed that you think should NOT be affected?"

---

### T+10 — Duty Manager Review

**OCC Controller forwards results to Duty Manager:**

1. [ ] Walk through KPI summary with DM
2. [ ] Highlight key affected flights
3. [ ] Point out any data quality warnings

**Duty Manager decides:**

- [ ] Review the affected flights list
- [ ] Approve, reject, or modify the impact assessment
- [ ] Identify any operational decisions needed
- [ ] Note any flights requiring manual handling

**Discussion:**

- "Is this output format useful for your decision-making?"
- "What additional information would you need?"
- "Would you trust this output in real IROPS?"

---

### T+15 — Export Excel Report

**OCC Controller:**

1. [ ] Click "Download Excel Report"
2. [ ] Open the Excel file
3. [ ] Review each sheet:
   - Parameters
   - KPI Summary
   - Affected Flights
   - All Flights
   - Data Quality Warnings

**Duty Manager reviews Excel:**

- "Is this format suitable for management briefing?"
- "What changes would make it more useful?"

---

### T+30 — Management Briefing Simulation

**OCC Controller or Duty Manager presents:**

Using the Excel export, simulate a 5-minute briefing:

1. "HAN closure from 14:00 to 18:00"
2. "X flights directly affected"
3. "Y aircraft impacted across the network"
4. "Key affected routes: [list from tool]"
5. "Recommended actions: [DM decisions]"

---

### T+45 — Debrief (15 minutes)

**Facilitator leads debrief discussion:**

1. **Tool accuracy**: Did the tool correctly identify affected flights?
2. **Usability**: Was the workflow smooth for OCC Controller?
3. **Speed**: How long from notice to briefing-ready output?
4. **Value**: Does this tool add value to current IROPS process?
5. **Improvements**: What should be fixed or added?

**Each participant completes feedback form.**

---

## Post-Drill Actions

| Action | Owner | Deadline |
|---|---|---|
| Collect all feedback forms | Facilitator | Same day |
| Document discrepancies found | Developer | +1 day |
| Fix any tool issues discovered | Developer | +3 days |
| Share drill summary with management | AIMS PIC | +2 days |
| Update known limitations doc | Developer | +3 days |

---

## Pass / Fail Criteria

| Criterion | Pass | Fail |
|---|---|---|
| Controller can run tool without help | Yes by T+5 | Needs help after T+10 |
| Results available within 5 minutes | Yes | No |
| DM finds output useful | Useful or Very useful | Not useful |
| No critical tool errors during drill | Zero crashes | Any crash |
| Excel export works | Successful download | Failed |
