# OCC IROPS Recovery Dashboard — Pilot Run Book

This run book describes the day-to-day operating procedure for the
**Pilot Phase** of the OCC IROPS Recovery Dashboard. The goal of the
pilot is to validate that cascade predictions match real operational
outcomes before promoting the tool to production.

## 1. Pre-flight checklist (once per shift)

1. Confirm the dashboard is reachable at the agreed URL (or run
   `streamlit run app.py` locally if running on a developer laptop).
2. Confirm `data/sample/sample_dayrep_24042026.xlsx` is still
   present — used as a smoke-test fixture.
3. Confirm CI is green on `main` (`python -m pytest`, `python -m ruff
   check .`, `python -m mypy src`). 129+ tests must pass.

## 2. Daily run procedure

### 2.1 Inputs

- **Closure-day DayRepReport** — exported from AIMS for the date a
  closure event happened (e.g. 24/04/2026).
- **Next-day DayRepReport** *(recommended)* — the day after the
  closure, to capture overnight cascade. Upload both files together;
  the parser handles them as a multi-file batch.
- **Closure events** — for each concurrent event:
  - airport ICAO/IATA code (e.g. `HAN`, `HPH`)
  - closure date
  - closure window (start/end time, end exclusive)
  - closure type — `airport_closed`, `runway_closed`, or `atc_flow`
    (cosmetic only — does not change detection logic)

### 2.2 Steps

1. Open the dashboard.
2. Upload the DayRepReport file(s) in the sidebar.
3. Set "Number of closure events" — typhoons may close HAN+HPH
   simultaneously; ATC flow restrictions can affect 3+ airports at
   once. Add one event per affected airport.
4. Configure each event (airport, date, window, type).
5. Optionally enable "What-if mode" to compare an alternative
   closure window (e.g. 15:00–16:00 vs 14:00–18:00).
6. Click **Run Analysis**.
7. Read the KPIs:
   - Total / Affected / L1 / L2 / L3+ / Aircraft
   - Pax disrupted (estimate) / Cost impact (USD)
8. Inspect the **Top-10 highlights** cards (pax / cost / cascade
   depth) to identify the worst-impacted flights.
9. Open the **Aircraft Rotation Detail** expanders for any tail you
   want to argue with crew/control — the `impact_explanation` column
   gives a human-readable cause.
10. Download the **1-page PDF Briefing** for shift hand-over and
    management distribution.
11. Download the **Excel Report** if a deeper offline review is
    needed (includes the row-level data quality warnings).

### 2.3 After the closure resolves (T+24 h)

1. Export the day's actuals from AIMS / OCC Ops as a CSV. The CSV
   must contain at minimum:

   ```
   flight_no,actual_outcome
   VN101,cancelled
   VN102,delayed
   VN103,on_time
   ```

   Optional `flight_date` column allows multi-day batches.
   Allowed outcomes: `on_time | delayed | cancelled | diverted`.

2. Re-run the same analysis (same files, same closure events) so
   `df_result` matches what the DM saw in real time.
3. Scroll to **Validation vs Actuals** at the bottom of the page,
   upload the actuals CSV.
4. Inspect the confusion matrix and the per-level metrics table.
   Acceptance criteria for graduating from pilot to production:
   - **Level 1 precision ≥ 0.95** — Level 1 predictions are almost
     never wrong (DMs trust the "must intervene" signal).
   - **Level 1 recall ≥ 0.90** — we rarely miss a flight that was
     directly hit by the closure.
   - **Affected (any) recall ≥ 0.85** — we rarely miss a flight that
     ended up delayed/cancelled/diverted by cascade.

## 3. Failure modes & escalation

| Symptom | Likely cause | First action |
|---|---|---|
| `HEADER_NOT_FOUND` warning, empty result | DayRepReport export uses a column-set we have not seen | Send the file to the dev team; we add the new alias in `src/config.py:HEADER_KEYWORD_MAP`. |
| KPI numbers look wildly different from prior days | Closure window or date entered incorrectly | Re-check sidebar inputs; remember end-time is **exclusive**. |
| Multi-file run double-counts L1 | Same file uploaded twice | The parser does not de-dupe — verify file list before clicking Run Analysis. |
| Validation shows low recall on cascade levels | Aircraft REG normalisation mismatch between predictions and actuals | Inspect `coverage` table; if `unmatched` is high, REG normalisation needs a fixture-driven test. |

## 4. Performance expectations

The cascade detector is benchmarked against a 5,000-flight × 3-day
× 5-concurrent-event fixture and must finish in **< 10 seconds** on
a developer-class machine. CI enforces this via
`tests/test_performance.py`.

## 5. Updating fixtures / parser hardening

When a real AIMS export breaks parsing or produces unexpected
results:

1. Sanitize the file (replace real REGs / pax names with
   placeholders) and add it to `tests/fixtures/aims_real/`.
2. Add a regression test in `tests/test_parser_hardening.py` that
   asserts the expected parse output.
3. Iterate on `src/parser/dayrep_parser.py` /
   `src/parser/time_parser.py` until the test passes.
4. Ensure the existing 129+ test suite still passes.
