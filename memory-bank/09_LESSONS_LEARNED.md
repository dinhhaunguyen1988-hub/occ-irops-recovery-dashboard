# 09 — Lessons Learned

> Engineering patterns, anti-patterns, and process insights extracted from Sprints 1–7. Read this file before adding to the codebase or before extending Sprint 8+.

## 1. Streamlit state must survive widget interactions

### Anti-pattern

```python
run_analysis = st.sidebar.button("Run Analysis", type="primary")
if not run_analysis:
    st.info("Configure parameters in the sidebar and click Run Analysis.")
    st.stop()

# … hundreds of lines of result rendering …
if st.button("Run stress test"):
    show_stress_test()
```

Streamlit buttons return `True` **only on the rerun where they were clicked**. Any subsequent widget interaction inside the result block (e.g. clicking "Run stress test", changing a select-box, editing settings) triggers a script rerun. On that rerun, the sidebar `Run Analysis` button returns `False` again, the `st.stop()` fires, and the entire result page disappears.

This is the bug that broke Sprint 7 T3 testing.

### Pattern

```python
run_analysis_clicked = st.sidebar.button("Run Analysis", type="primary")
if run_analysis_clicked:
    st.session_state["analysis_active"] = True
analysis_active = bool(st.session_state.get("analysis_active"))

if not analysis_active:
    st.info("Configure parameters in the sidebar and click Run Analysis.")
    st.stop()
```

The button is a one-shot signal. The persistent state is in `st.session_state["analysis_active"]`. Subsequent reruns find `analysis_active == True` and continue rendering the result page.

### Regression guard

`tests/test_app_smoke.py::test_analysis_state_persists_via_session_state` asserts both lines exist in `app.py`. CI fails if anyone re-introduces the anti-pattern.

### Generalisation

Any Streamlit button whose effect must outlive a single rerun (e.g. "Run analysis", "Apply settings", "Open advanced panel") must be paired with a `st.session_state` flag.

---

## 2. Python 3.13 reserves more `LogRecord` field names

### Anti-pattern

```python
logger.info("upload_received", extra={"filename": uploaded_file.name})
```

`filename` is a built-in `LogRecord` attribute (the Python source file the log call was made from). On Python 3.13, `Logger.makeRecord` raises `KeyError("Attempt to overwrite 'filename' in LogRecord")`. Earlier versions silently overwrote.

### Pattern

```python
logger.info("upload_received", extra={"filenames": [f.name for f in uploaded_files]})
```

Avoid keys that collide with `LogRecord` reserved attrs:

```
name, msg, args, levelname, levelno, pathname, filename, module,
exc_info, exc_text, stack_info, lineno, funcName, created, msecs,
relativeCreated, thread, threadName, processName, process, message,
asctime, taskName
```

Plural / role-prefixed names (`filenames`, `upload_filename`, `source_filename`) are safe.

### Reference

The full reserved-keys set is encoded in `src/logging_config.py::_RESERVED_KEYS`. It is filtered out of every JSON record in `JsonFormatter.format`.

---

## 3. Two-pass cascade with closure-date filter

### Anti-pattern

Pass 1 detects L1 by time-of-day only:
```python
mask = (df["sta"].between(event.start, event.end))
```

When the user uploads D + D+1, this incorrectly flags D+1 arrivals into HAN at 14:30 even if the closure was on D.

### Pattern

```python
mask = (
    (df["flight_date"] == event.closure_date)
    & (df["sta"] >= event.start)
    & (df["sta"] <  event.end)
)
```

`flight_date == closure_date` is the gating clause. Boundary is **start inclusive, end exclusive** (`>= start, < end`).

### Pass 2 ordering

Sort each aircraft group by `(flight_date, std)`, not just `std`. Otherwise overnight rotations break at midnight (a 23:00 sector and a 01:00 sector look "out of order" if you only compare `std`).

### Verified by

`tests/test_overnight_cascade.py` constructs a D + D+1 fixture with one shared registration that has a Level 1 on D and a downstream sector on D+1. The test asserts the D+1 sector becomes Level 2 (cascade hop = 1).

---

## 4. Multi-event union, single Pass 2

### Anti-pattern

Run Pass 1 + Pass 2 once per event and union the results. This double-counts downstream sectors when two events affect the same aircraft.

### Pattern

```python
def detect_cascade_multi(df, events):
    union_l1_mask = reduce(or_, (mask_event(df, e) for e in events))
    df.loc[union_l1_mask, "level"] = 1
    propagate_pass2(df, root_mask=union_l1_mask)
```

Pass 2 walks the rotation chain **once** starting from the union of L1 masks. Each downstream sector is visited once.

### Verified by

`tests/test_multi_event_cascade.py` and the Sprint 3 e2e T2 (HAN + HPH). KPI L2 stays at 41 when adding HPH; only L1 and L3+ change.

---

## 5. Closure type is cosmetic — never branch logic on it

### Anti-pattern

```python
if event.closure_type == "runway_closed":
    use_a_different_l1_rule()
```

This breaks BR-08 and produces silent KPI drift when DM toggles the type for a paper-only label change.

### Pattern

`closure_type` is only used in:
- the Gantt closure-band annotation,
- the network-map hover text,
- the PDF briefing header.

KPI logic ignores it.

### Verified by

Sprint 3 e2e T3: changing closure type from `airport_closed` to `runway_closed` for an otherwise-identical event must produce **byte-for-byte identical KPIs**. T3 is part of every future sprint's regression checklist.

---

## 6. Recovery scoring must be defendable on paper

### Anti-pattern

Train an opaque ML model that produces a score the DM can't explain.

### Pattern

```
score = w_pax  × pax
      + w_cost × cost
      + w_op   × op_penalty
op_penalty = {delay: 0, swap_tail: 1, cancel: 3}
defaults  = {w_pax: 1.0, w_cost: 0.5, w_op: 100.0}
```

Three terms, three weights, three op-penalties. Anyone in OCC can verify the score by hand.

### Test pattern

Adversarial unit tests assert exact numeric outputs (e.g. `swap_tail.score == 1498.0`) so any change to the formula or weights surfaces immediately as a CI failure.

---

## 7. Rule-based pax reaccommodation ranking

### Pattern

```
1. International first (FAA / IATA reaccom priority)
2. Then by descending pax count
3. Then by descending cascade depth (deeper chains = more affected pax)
```

Rationale string is rendered next to each row ("International; High pax load") so the DM can defend the order.

### Verified by

Sprint 7 e2e T2: rank 1 must be `145 / VN-A534 / HKG→VDH / pax 259 / "International; High pax load"` on the sample dataset.

---

## 8. Performance budget enforcement

### Pattern

Add a synthetic fixture test marked `@pytest.mark.performance`:

```python
@pytest.mark.performance
def test_5000_flight_perf_budget():
    df = build_synthetic_dayrep(n=5000, days=3)
    events = [build_event() for _ in range(5)]
    t0 = time.perf_counter()
    detect_cascade_multi(df, events)
    assert time.perf_counter() - t0 < 10.0
```

Local run: 1.56 s. Budget: 10 s. CI runs it on every push. Marker lets developers `pytest -m "not performance"` for fast local iteration.

---

## 9. Adversarial test data over aggregate-only assertions

### Anti-pattern

```python
result = detect_cascade(df, event)
assert len(result.affected) > 0
```

This passes whenever the algorithm returns *any* output. It catches almost no regressions.

### Pattern

```python
result = detect_cascade(df, event)
assert len(result.affected) == 139           # exact baseline
assert result.kpi["est_pax"] == 27_827        # exact pax
assert result.kpi["est_cost_usd"] == 1_898_730  # exact cost
assert result.affected.iloc[0]["flight_no"] == "198"  # priority-ranked top
```

Tests assert exact numeric values pinned by hand-calculated expectations. Any KPI drift fails the test.

Adversarial test fixtures are why Sprint 2 caught the docstring-baseline mismatch and Sprint 3 caught the multi-event double-count risk.

---

## 10. Streamlit one-click flow > complex multi-step wizards

OCC controllers have ~30 seconds to brief the DM. Don't make them click through 5 panels.

- Sidebar collects inputs.
- One **Run Analysis** button.
- Result page renders all expanders (Decision support, Stress test, Recent runs, Settings, Audit log) at once.
- Defaults are pre-filled to the most recent run config (Sprint 5 Recent runs panel reuses prior config).

---

## 11. Estimates must be labelled as estimates

Every estimated number in the UI is labelled `(est.)`:

- KPI: "Pax disrupted (est.)", "Cost impact (est. USD)".
- Column headers: `est_pax`, `est_cost_usd`.
- PDF briefing footer: "All passenger and cost figures are estimates based on configured load factor and cost rate."

This protects the DM from accidentally citing tool numbers as actuals in a regulatory or media context.

---

## 12. Stacked PR merge procedure

### What went wrong

`gh pr merge --auto` was used to merge PRs #2 → #8 sequentially. Auto-merge merged each stacked PR into its **parent branch**, not into the default branch. Result: only Sprint 1 reached the default branch; user's clone hit Python 3.13 LogRecord crash.

### Correct procedure

When merging a stack of N PRs to the default branch:

1. **Option A (preferred when stack is small)** — merge tip-of-stack PR directly into default with `-X ours` after fetching default. Close the intermediate PRs with a comment pointing to the cumulative merge PR.
2. **Option B** — merge in stack order using `--merge` (not `--auto`):
   - Merge PR #2 (base = default) → default branch updated.
   - GitHub auto-retargets PR #3 to default.
   - Merge PR #3 → default branch updated.
   - …repeat.
3. **Avoid `--auto`** — it queues merges that fire when CI passes on the *current base*. With stacked PRs and concurrent retargets, this races and merges into the wrong branch.

### Cleanup if it goes wrong

- Open a new PR from the stack tip → default with `-X ours` to resolve the resulting conflicts, removing duplicate insertions in any merge artefacts (see PR #9 follow-up commit `eddeb02`).

---

## 13. Documentation discipline

- Memory-bank files use sequential numeric prefixes (`00_…`, `01_…`, `08_…`). Do not insert in the middle; append.
- Every new feature gets a one-line entry in `PROGRESS.md` and a row in `08_SPRINT_HISTORY.md`.
- Each sprint produces a recording + report for end-to-end UI testing; the recording link goes in the PR comment, the report goes in the PR body / docs folder.
- BRD / PRD / Architecture are versioned. Bump the document version when scope or contracts change, not when wording changes.

---

## 14. Process — what to do at the start of every sprint

1. Run `pytest tests/ -q` on the current branch and confirm green before touching any code.
2. Run `streamlit run app.py` against the sample DayRepReport and confirm the baseline KPI (`358 / 139 / 51 / 41 / 47 / 26`, pax `27,827`, cost `$1,898,730`).
3. Write the sprint plan into `08_SPRINT_HISTORY.md` *before* coding. Include intended deliverables and adversarial test ideas.
4. Open the PR as soon as basic tests pass. Don't sit on a working branch.
5. Drive end-to-end UI tests after CI is green. Attach the recording + report to the PR comment.
