# 01 — Cascade Detection Logic

## 1. Objective

Implement airport-closure impact detection and downstream cascade tracing for aircraft rotations.

The cascade logic must be deterministic, explainable, and auditable.

## 2. Boundary Condition — Time Window

### Rule

Airport closure time window must use:

```python
time >= closure_start AND time < closure_end
```

This means:

- Start boundary is inclusive.
- End boundary is exclusive.

### Reason

If airport closure is `14:00–18:00`, then:

- A flight arriving at `14:00:00` is affected.
- A flight arriving at `17:59` is affected.
- A flight arriving at `18:00:00` is not automatically affected because airport is assumed reopened.

### Example

| Flight | STA | Affected? | Explanation |
|---|---:|---|---|
| VN-A | 13:59 | No | Arrives before closure |
| VN-B | 14:00:00 | Yes | Exactly at closure start |
| VN-C | 17:59 | Yes | Within closure window |
| VN-D | 18:00:00 | No | End boundary is exclusive |

## 3. Level 1 Detection

### Level 1 arrival rule

A flight is Level 1 if destination airport is closed at scheduled arrival time:

```python
dest_affected = (
    (df["destination"] == event.airport) &
    (df["sta"] >= event.start_time) &
    (df["sta"] < event.end_time)
)
```

### Level 1 departure rule

A flight is Level 1 if origin airport is closed at scheduled departure time:

```python
orig_affected = (
    (df["origin"] == event.airport) &
    (df["std"] >= event.start_time) &
    (df["std"] < event.end_time)
)
```

### Combined Level 1 rule

```python
df.loc[dest_affected | orig_affected, "impact_level"] = 1
```

## 4. Level 2 and Downstream Cascade

After Level 1 flights are detected, downstream sectors on the same aircraft are assigned increasing impact levels.

Example:

| Correct level | Flight | Route | STD | STA | Reason |
|---:|---|---|---:|---:|---|
| 1 | 1504 | DAD → HAN | 12:40 | 14:00 | Cannot land — destination closed |
| 1 | 1505 | HAN → DAD | 14:35 | 15:55 | Cannot depart — origin closed |
| 2 | 637 | DAD → SGN | 16:40 | 18:00 | Aircraft misplaced |
| 3 | 1801 | SGN → BLR | 19:20 | 22:35 | Downstream cascade |

## 5. Critical Rule — Multiple Level 1 Flights on Same Aircraft

Do not implement cascade logic in a single naive loop.

Problem:

- The same aircraft may have more than one direct Level 1 impacted sector.
- If the code only starts cascade from the first Level 1, it may incorrectly assign levels after the second direct impact.

## 6. Required Algorithm — Two-Pass Detection

### Pass 1 — Detect all Level 1 flights independently

```python
df["impact_level_numeric"] = None

df.loc[dest_affected | orig_affected, "impact_level_numeric"] = 1
```

### Pass 2 — Trace downstream by aircraft

```python
for reg, group in df.groupby("aircraft_reg"):
    sorted_group = group.sort_values("std")
    cascade_level = None

    for idx, row in sorted_group.iterrows():
        if row["impact_level_numeric"] == 1:
            cascade_level = 2
        elif cascade_level is not None:
            if row["impact_level_numeric"] is None:
                df.at[idx, "impact_level_numeric"] = cascade_level
            cascade_level += 1
```

## 7. Level 3+ Display Rule

Store actual numeric level internally, but display Level 3 and above as `3+`.

| Stored numeric level | UI display | Purpose |
|---:|---|---|
| 1 | Level 1 | Direct impact |
| 2 | Level 2 | First downstream sector |
| 3 | 3+ | Grouped downstream display |
| 4 | 3+ | Grouped downstream display |
| 5+ | 3+ | Grouped downstream display |

### Recommended implementation

```python
def display_impact_level(level: int | None) -> str:
    if level is None:
        return "Not affected"
    if level == 1:
        return "Level 1"
    if level == 2:
        return "Level 2"
    return "3+"
```

## 8. Overnight Rotation Limitation

MVP limitation:

> Cascade detection is limited to flights within the loaded report date range.

If the DayRepReport only contains flights for 24/04, the tool will not detect downstream impact on 25/04.

### Required warning in README and UI

```text
Cascade detection is limited to flights within the loaded report date range.
Overnight downstream rotations outside the loaded file are not included in MVP.
```

## 9. Audit Trail Requirement

Each affected flight should include a reason field.

Examples:

| Impact level | Reason |
|---|---|
| Level 1 | Arrival into closed airport |
| Level 1 | Departure from closed airport |
| Level 2 | Downstream aircraft rotation after Level 1 impact |
| 3+ | Extended downstream cascade |
