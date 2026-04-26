# User Guide — OCC IROPS Recovery Dashboard

## 1. Getting Started

### Launch the Tool

```bash
streamlit run app.py
```

The tool opens in your default web browser.

## 2. Workflow

### Step 1: Upload DayRepReport

1. In the **sidebar**, click "Upload DayRepReport (Excel)"
2. Select your AIMS DayRepReport Excel file (.xlsx or .xls)
3. The parser will automatically detect the header row and column mapping

### Step 2: Configure Closure Event

Fill in the sidebar fields:

| Field | Description | Example |
|---|---|---|
| Airport Code | IATA code of the closed airport | HAN |
| Closure Date | Date of the closure event | 24/04/2026 |
| Closure Start Time | Start of closure (inclusive) | 14:00 |
| Closure End Time | End of closure (exclusive) | 18:00 |

### Step 3: Run Analysis

Click **Run Analysis** to execute cascade detection.

### Step 4: Review Results

The dashboard displays:

1. **MVP Limitation Warning** — reminder about overnight rotation limitation
2. **Data Quality Warnings** — any parser issues (expandable panel)
3. **KPI Summary** — total flights, affected flights, Level 1/2/3+ counts
4. **Affected Flights Table** — full list with impact level and reason
5. **Aircraft Rotation View** — per-aircraft flight chain showing cascade

### Step 5: Export

Click **Download Excel Report** to export results. The Excel file contains:

- Parameters sheet (closure event details)
- KPI Summary sheet
- Affected Flights sheet
- All Flights sheet
- Data Quality Warnings sheet

## 3. Understanding Impact Levels

| Level | Meaning | Example |
|---|---|---|
| Level 1 | Direct impact from airport closure | Flight arriving at HAN during closure |
| Level 2 | First downstream sector on same aircraft | Next flight using the same aircraft |
| 3+ | Extended downstream cascade | Further flights on the aircraft chain |

## 4. Boundary Rules

- Closure **start time is inclusive**: a flight arriving exactly at closure start IS affected
- Closure **end time is exclusive**: a flight arriving exactly at closure end is NOT affected

## 5. Troubleshooting

| Issue | Possible Cause | Solution |
|---|---|---|
| "Cannot detect header row" | Unusual column names in report | Check that the Excel has standard AIMS headers |
| Time parse warnings | Non-standard time format | Review warnings panel for specific rows |
| No affected flights | Wrong airport or time window | Verify closure parameters |
| Missing aircraft in cascade | REG format issue | Check for non-standard registration formats |
