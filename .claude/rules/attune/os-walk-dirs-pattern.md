# os.walk dirs[:] Pattern

**Created:** 2026-01-26
**Source:** Session evaluation - perf-audit false positive analysis

---

## The Pattern

When using `os.walk()` to filter directories, you MUST use in-place slice assignment:

```python
# CORRECT - modifies dirs in-place, affects traversal
for root, dirs, files in os.walk(path):
    dirs[:] = [d for d in dirs if not excluded(d)]
```

```python
# WRONG - rebinds variable, does NOT affect traversal
for root, dirs, files in os.walk(path):
    dirs = [d for d in dirs if not excluded(d)]  # BUG!
```

---

## Why This Matters

From Python docs:
> When topdown is True, the caller can modify the dirnames list in-place
> (perhaps using del or slice assignment), and walk() will only recurse
> into the subdirectories whose names remain in dirnames.

The `dirs` list is a reference to os.walk's internal state. Rebinding with `=` creates a new list that os.walk ignores. Slice assignment `[:]` modifies the original list in-place.

---

## Scanner False Positive

The memory leak scanner flags `dirs[:]` as "large_list_copy" but this is a **false positive**. The pattern is:
1. Required for correct behavior
2. Not actually a "copy" - it's in-place modification
3. Essential for filtering directory traversal

**Do NOT "fix" this pattern** - it's correct as-is.

---

## Examples in Codebase

- `src/attune/project_index/file_analysis.py:132`
- `src/attune/workflows/code_review_architect.py:99`

Both correctly use `dirs[:]` to filter excluded
directories during traversal.
