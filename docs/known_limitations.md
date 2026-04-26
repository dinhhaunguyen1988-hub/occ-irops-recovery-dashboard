# Known Limitations — OCC IROPS Recovery Dashboard (MVP)

## 1. Overnight Rotation

Cascade detection is limited to flights within the loaded report date range.
Overnight downstream rotations outside the loaded file are not included in MVP.

If the DayRepReport only contains flights for 24/04, the tool will not detect downstream impact on 25/04.

## 2. Scenario Scope

MVP is limited to **Airport Closure** scenario only.

Not implemented:
- Aircraft recovery optimization
- Crew legality checks
- Passenger reaccommodation
- Weather-based disruption analysis
- Multi-airport closure scenarios
- Automated decision-making

## 3. Data Limitations

- Parser relies on dynamic header detection matching at least 6 of 8 expected keyword groups
- Unusual AIMS export formats may not parse correctly
- Time parsing handles common formats but may miss exotic edge cases
- Registration normalization assumes VN-prefix pattern

## 4. Performance

- Designed for single-file analysis (not batch processing)
- No database persistence — each session is stateless
- Large files (>5000 rows) may take longer to process

## 5. Integration

- No live AIMS integration — manual file upload only
- No notification or alerting system
- No multi-user collaboration features

## 6. Decision Authority

This tool is an analysis assistant only. It does **not**:
- Make operational decisions
- Replace the Duty Manager's judgment
- Automatically recover aircraft
- Generate binding recommendations
