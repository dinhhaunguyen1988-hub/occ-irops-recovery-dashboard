# 04 — Definition of Done

## 1. Priority Action List

Implementation priority is based on operational risk.

| Priority | Item | Related area | Required action |
|---:|---|---|---|
| 1 | `parse_time_field()` | Data Parsing | Write and test with all known time formats first |
| 2 | REG normalization | Data Parsing | Apply `str.strip().str.upper()` immediately after load |
| 3 | Two-pass cascade detection | Cascade Logic | Pass 1 Level 1; Pass 2 downstream |
| 4 | Boundary condition | Cascade Logic | Use exclusive end: `< closure_end` |
| 5 | `HEADER_KEYWORD_MAP` | Data Parsing | Use fuzzy/alias match, at least 6/8 groups |
| 6 | Overnight limitation warning | Cascade Logic | Show warning in README and UI |
| 7 | Phase 0 validation | Pilot | Test with 5–10 real DayRepReport files before users |

## 2. MVP Definition of Done

| Criterion | Target | Validation phase |
|---|---:|---|
| Parser handles all known time formats | 100% | Phase 0 |
| REG normalization creates no phantom aircraft | 0 known errors | Phase 0 |
| Header detection works with real DayRepReports | At least 5 files | Phase 0 |
| Expected KPI: `358/87/39/23/25/24` | 100% accurate | Phase 0 |
| OCC Controller can run tool without support | By week 2 | Phase 1 |
| OCC Controller satisfaction | ≥ 4.0/5 | Phase 1–2 |
| Tool output generated in under 5 minutes | < 5 minutes | Phase 2 |
| Recommendation matches DM decision | > 70% | Phase 2 |
| Tabletop Drill completed | 1 drill | Phase 3 |
| DM says output is useful | Yes | Phase 3 |

## 3. Engineering Done Checklist

### Parser

- [ ] Raw Excel file can be loaded.
- [ ] Dynamic header row can be detected.
- [ ] Column aliases map correctly to canonical schema.
- [ ] Footer rows are skipped.
- [ ] Invalid rows are logged as warnings.
- [ ] All required time formats are handled.
- [ ] Aircraft registration is normalized.
- [ ] Canonical dataframe is returned.
- [ ] Parser tests pass.

### Cascade detector

- [ ] Airport closure event can be configured.
- [ ] Boundary rule uses start inclusive, end exclusive.
- [ ] Arrival Level 1 detection works.
- [ ] Departure Level 1 detection works.
- [ ] Multiple Level 1 flights on same aircraft are handled.
- [ ] Downstream cascade is traced by aircraft registration.
- [ ] Numeric impact level is stored.
- [ ] UI display level maps 3 and above to `3+`.
- [ ] Reason field is generated for each affected flight.
- [ ] Cascade tests pass.

### UI / Streamlit

- [ ] User can upload DayRepReport.
- [ ] User can enter airport closure event.
- [ ] Tool displays summary KPI.
- [ ] Tool displays affected flight table.
- [ ] Tool shows data quality warnings.
- [ ] Tool shows MVP overnight limitation warning.
- [ ] User can export Excel report.

### Pilot readiness

- [ ] 5–10 real DayRepReport files tested.
- [ ] Known discrepancies documented.
- [ ] Tabletop Drill scenario prepared.
- [ ] Feedback form prepared.
- [ ] Duty Manager briefing output prepared.

## 4. Core Conclusion

The hardest part of this project is not business logic.

Cascade detection itself is relatively simple.

The real challenges are:

1. Data quality in real AIMS DayRepReport files.
2. Change management with OCC Controller and Duty Manager.
3. Building trust through audit trail and controlled pilot rollout.

Therefore:

> Invest more effort in Phase 0 validation and Tabletop Drill than in extra Streamlit features.
