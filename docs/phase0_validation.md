# Phase 0 — Internal Validation Checklist

## Objective

Validate the OCC IROPS Recovery Dashboard against real DayRepReport files before any OCC end user handles it.

**Participants:** Developer + AIMS PIC only. No OCC end user yet.

---

## Pre-Validation Setup

- [ ] Dashboard installed and running
- [ ] All tests passing (`python -m pytest tests/ -v`)
- [ ] Sample data demo completed successfully
- [ ] AIMS PIC has prepared 5–10 real DayRepReport files

---

## File Collection

| # | File name | Date | Source | Flights | Collected |
|---|---|---|---|---|---|
| 1 | | | | | [ ] |
| 2 | | | | | [ ] |
| 3 | | | | | [ ] |
| 4 | | | | | [ ] |
| 5 | | | | | [ ] |
| 6 | | | | | [ ] |
| 7 | | | | | [ ] |
| 8 | | | | | [ ] |
| 9 | | | | | [ ] |
| 10 | | | | | [ ] |

---

## Validation Tests Per File

For each DayRepReport file, complete this checklist:

### File: __________________ (Date: __________)

#### Parser Validation

- [ ] File loads without crash
- [ ] Header row detected correctly (row #: ____)
- [ ] All 8 canonical columns mapped correctly
- [ ] Flight count matches expectation: ____ parsed / ____ expected
- [ ] Footer rows properly filtered
- [ ] No phantom flights created from footer/title rows
- [ ] Data quality warnings reviewed and reasonable

#### Time Parsing

- [ ] All STD values parsed (or warned)
- [ ] All STA values parsed (or warned)
- [ ] No silent time parsing failures
- [ ] Time format variants found: ____________________

#### Registration Normalization

- [ ] All REG values normalized
- [ ] No split aircraft chains (same physical aircraft = same REG)
- [ ] REG format variants found: ____________________

#### Cascade Detection (HAN 14:00-18:00 scenario)

- [ ] Level 1 flights identified correctly
- [ ] Level 1 count: ____ (expected: ____)
- [ ] Downstream cascade traced correctly
- [ ] Level 2 count: ____ (expected: ____)
- [ ] Level 3+ count: ____ (expected: ____)
- [ ] No false positives (unaffected flights marked as affected)
- [ ] No false negatives (affected flights missed)

#### Rotation Chain Verification

Pick 3 aircraft with cascade impact and verify chain:

**Aircraft 1: ____________**
| Flight | Route | STD | STA | Tool Level | Manual Check | Match? |
|---|---|---|---|---|---|---|
| | | | | | | [ ] |
| | | | | | | [ ] |
| | | | | | | [ ] |
| | | | | | | [ ] |

**Aircraft 2: ____________**
| Flight | Route | STD | STA | Tool Level | Manual Check | Match? |
|---|---|---|---|---|---|---|
| | | | | | | [ ] |
| | | | | | | [ ] |
| | | | | | | [ ] |
| | | | | | | [ ] |

**Aircraft 3: ____________**
| Flight | Route | STD | STA | Tool Level | Manual Check | Match? |
|---|---|---|---|---|---|---|
| | | | | | | [ ] |
| | | | | | | [ ] |
| | | | | | | [ ] |
| | | | | | | [ ] |

#### Excel Export

- [ ] Excel download works
- [ ] Parameters sheet correct
- [ ] KPI Summary sheet correct
- [ ] Affected Flights sheet correct
- [ ] All Flights sheet correct
- [ ] Warnings sheet correct

---

## Summary Results

| Metric | Target | Actual | Pass? |
|---|---|---|---|
| Files loaded without crash | 100% | ____% | [ ] |
| Rotation match rate | > 95% | ____% | [ ] |
| Time formats parsed correctly | 100% | ____% | [ ] |
| No phantom aircraft from REG issues | 0 errors | ____ errors | [ ] |
| KPI accuracy vs manual check | 100% | ____% | [ ] |

---

## Discrepancies Log

| # | File | Issue | Severity | Resolution |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |

---

## Phase 0 Sign-Off

| Role | Name | Sign-off | Date |
|---|---|---|---|
| Developer | | [ ] Approved | |
| AIMS PIC | | [ ] Approved | |

**Phase 0 result:** [ ] PASS — proceed to Phase 1  /  [ ] FAIL — fix issues first
