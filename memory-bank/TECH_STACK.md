# Tech Stack — OCC IROPS Recovery Dashboard

## Language & Runtime

- Python 3.10+

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| streamlit | ≥1.30.0 | Dashboard UI |
| pandas | ≥2.0.0 | Data manipulation and parsing |
| openpyxl | ≥3.1.0 | Reading Excel files (.xlsx) |
| xlsxwriter | ≥3.1.0 | Writing Excel exports |
| pytest | ≥7.0.0 | Test framework |

## Architecture

```
Input: AIMS DayRepReport (Excel .xlsx/.xls)
  → Parser (dynamic header, column mapping, time parsing, REG normalization)
    → Canonical DataFrame
      → Cascade Detector (two-pass: Level 1 → downstream)
        → Augmented DataFrame with impact levels
          → Streamlit UI (KPI, tables, rotation view)
          → Excel Exporter (5-sheet workbook)
```

## Key Design Patterns

1. **Canonical schema** — all raw AIMS columns normalized to standard names
2. **Two-pass detection** — prevents cascade errors with multiple Level 1 on same aircraft
3. **Warning accumulation** — parser never silently fails; warnings collected and displayed
4. **Stateless sessions** — no database; each analysis run is independent
5. **Separation of concerns** — parser, detector, exporter, UI are independent modules

## File Layout

```
src/config.py              — global constants and configuration
src/models/event.py        — AirportClosureEvent dataclass
src/parser/time_parser.py  — AIMS time field parsing
src/parser/dayrep_parser.py — DayRepReport Excel parsing + REG normalization
src/cascade/cascade_detector.py — two-pass cascade detection + KPI computation
src/export/excel_exporter.py — Excel workbook export
app.py                     — Streamlit application entry point
```
