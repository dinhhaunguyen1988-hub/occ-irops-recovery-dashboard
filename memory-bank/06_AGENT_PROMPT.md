# 06 — Agent Prompt

Use this prompt when asking a coding Agent such as Codex to implement or update the project.

---

You are building an MVP named **OCC IROPS Recovery Dashboard**.

The tool supports OCC during airport closure disruptions by reading an AIMS DayRepReport, detecting directly affected flights, tracing downstream aircraft rotation cascade, and producing a structured output for OCC Controller and Duty Manager review.

## Business framing

Do not frame the product as AI or optimization.  
It is an automated AIMS report reader and impact analysis assistant.

Duty Manager remains the final decision maker.

## MVP scope

Implement only Airport Closure scenario.

Do not implement:

- aircraft recovery optimization
- crew legality
- passenger reaccommodation
- automated decision-making
- overnight rotation beyond loaded report
- live AIMS integration
- database persistence unless explicitly requested

## Input

AIMS DayRepReport Excel file.

The report may have:

- title rows before header
- variable column names
- inconsistent time format
- blank times
- `--:--`
- `2400`
- `+1` next-day marker
- footer rows
- inconsistent aircraft registration format

## Parser requirements

Create robust parser that:

1. Detects header dynamically using keyword alias mapping.
2. Requires at least 6 of 8 expected header groups.
3. Maps columns into canonical schema.
4. Removes footer and non-flight rows.
5. Normalizes aircraft registration.
6. Parses AIMS time fields.
7. Emits warnings instead of silently failing.

Canonical fields:

```text
flight_date
flight_no
aircraft_reg
aircraft_type
origin
destination
std
sta
raw_row_number
data_quality_warning
```

## Cascade logic requirements

Use airport closure boundary:

```python
time >= closure_start and time < closure_end
```

Level 1:

- arrival into closed airport, or
- departure from closed airport

Use two-pass detection:

1. Detect all Level 1 flights independently.
2. Trace downstream cascade by aircraft registration sorted by STD.

Store actual numeric level in:

```text
impact_level_numeric
```

Display:

```text
1 -> Level 1
2 -> Level 2
3 or higher -> 3+
```

Add audit reason for each affected flight.

## Required tests

Write tests for:

- all time formats
- header detection
- REG normalization
- footer filtering
- boundary condition start inclusive / end exclusive
- multiple Level 1 flights on same aircraft
- downstream cascade Level 2 and Level 3+
- non-affected aircraft

## UI requirements

Use Streamlit.

Minimum UI:

- upload DayRepReport
- airport code input
- closure date input
- closure start/end time input
- run analysis
- KPI summary
- affected flights table
- data quality warning panel
- export Excel button

Always display this warning:

```text
Cascade detection is limited to flights within the loaded report date range.
Overnight downstream rotations outside the loaded file are not included in MVP.
```

## Delivery priority

Build in this order:

1. `parse_time_field()`
2. aircraft registration normalization
3. dynamic header detection
4. DayRepReport canonical parser
5. two-pass cascade detector
6. test suite
7. Streamlit UI
8. Excel export
9. pilot documentation

## Definition of Done

The MVP is done only when:

- parser handles all known time formats
- header detection works with at least 5 real DayRepReport files
- expected KPI sample result is correct
- cascade logic passes multiple-Level-1 test
- tool output is generated under 5 minutes
- Excel export works
- warnings are visible
- tests pass

Implement the simplest reliable solution.  
Do not expand scope until MVP has passed Phase 0 validation.
