# Spec: Telemetry System

## Phase 3: Tasks

**Status**: complete

### Implementation order

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Create `UsageTracker` class in `src/attune/telemetry/usage_tracker.py`. Constructor takes `storage_path`, `retention_days`, `max_file_size_mb`; ensures `storage_path` exists. | attune-ai | done | Phase 1 — Core Tracking. |
| 2 | Implement `UsageTracker.track()` with all schema fields; SHA-256 hash for `user_id`; round `cost` to 6 decimals; include `stage` only when set. | attune-ai | done | |
| 3 | Implement atomic append in `_append_entry()` — write to `usage.jsonl.tmp`, then `rename()` to `usage.jsonl`. Newline-terminated single-line JSON, no whitespace separators. | attune-ai | done | POSIX atomic rename guarantees no torn writes. |
| 4 | Implement `_rotate_if_needed()` — when current file exceeds `max_file_size_mb`, rotate `usage.jsonl` → `usage.jsonl.1`, shifting older numbered files up to `.9`. | attune-ai | done | Rotation cap prevents unbounded growth. |
| 5 | Integrate `UsageTracker` into `BaseWorkflow._call_llm()` (`src/attune/workflows/base.py`). Track on every LLM response with `enable_telemetry` flag (default True). Capture cache hit/type from existing cache check. | attune-ai | done | Single hook covers all workflows. |
| 6 | Implement `UsageTracker.get_entries(since, until)` — read all `usage.jsonl*` files (current + rotated), filter by ISO timestamp range. Skip malformed lines with a warning. | attune-ai | done | Reader for the CLI commands. |
| 7 | Implement `UsageTracker.calculate_savings(since)` — total actual cost, baseline cost (`$0.45 × call count`), tier distribution, cache hit rate. Returns dict for the `savings` CLI. | attune-ai | done | Phase 2 — CLI Commands. |
| 8 | CLI command `attune telemetry show` — last-N-days summary table (calls, cost, avg cost, tier breakdown, top workflows, cache stats). Use rich formatting. | attune-ai | done | |
| 9 | CLI command `attune telemetry savings` — render `calculate_savings()` output with role estimate + total savings vs. baseline. | attune-ai | done | |
| 10 | CLI command `attune telemetry reset` — confirm prompt, delete `usage.jsonl` + all rotations. | attune-ai | done | |
| 11 | CLI command `attune telemetry compare` — two-period diff with absolute and percentage deltas across calls, cost, tier mix, cache hit rate. | attune-ai | done | Phase 3 — Advanced Features. |
| 12 | CLI command `attune telemetry export` — `--format csv|json`, optional `--from` / `--to` date range, optional `--output` path. | attune-ai | done | |
| 13 | Configuration loader at `~/.empathy/telemetry/config.json` — `enabled`, `retention_days`, `max_file_size_mb`, `user_id`, privacy toggles. Defaults applied if file missing. | attune-ai | done | |
| 14 | Privacy audit pass — grep for prompts/responses/file paths in tracked dict; document the audit in CLAUDE.md or a dedicated privacy-compliance section. | attune-ai | done | |
| 15 | Run real workflows for 1 week; validate `savings` output against manual computation; test rotation under 10 MB; document findings. | attune-ai | done | Phase 4 — Testing & Validation. |

### Dependencies

```
Task 1 → Tasks 2, 3, 4   (the class shell before its methods)
Task 2 → Task 5          (track() must exist before workflow hook)
Tasks 3, 4 → Task 6      (storage stable before reader)
Task 6 → Tasks 7, 8       (reader before aggregators)
Task 7 → Task 9           (savings calc before savings CLI)
Tasks 5–9 → Tasks 11, 12  (advanced features need basic flow working)
Task 13 independent
Task 14 → Task 15         (audit before live-run validation)
```

### Testing strategy

#### Unit tests — `tests/unit/telemetry/test_usage_tracker.py`

```python
async def test_track_entry():
    tracker = UsageTracker(storage_path=tmp_path)
    await tracker.track(
        workflow="code-review",
        tier="CAPABLE",
        model="claude-sonnet-4.5",
        provider="anthropic",
        cost=0.015,
        tokens={"input": 1500, "output": 500},
        cache={"hit": False},
        duration_ms=2340,
    )
    entries = await tracker.get_entries()
    assert len(entries) == 1
    assert entries[0]["tier"] == "CAPABLE"
```

Required cases:
- Track + read round-trip (every required field)
- `stage` omitted vs. provided
- Cost rounding to 6 decimals
- `user_id` SHA-256 hashing
- Atomic append: simulated mid-write crash leaves no partial entries
- Rotation triggers at threshold; numbered files shift correctly
- Retention prunes older than `retention_days`
- Reader filters `since` / `until` correctly
- Reader skips malformed lines without crashing

#### Integration tests — `tests/integration/test_telemetry_integration.py`

```python
async def test_workflow_tracks_usage():
    workflow = CodeReviewWorkflow(enable_telemetry=True)
    await workflow.execute(diff="...", files_changed=["test.py"])

    tracker = UsageTracker()
    entries = await tracker.get_entries()
    assert len(entries) > 0
    assert entries[0]["workflow"] == "CodeReviewWorkflow"
```

- End-to-end: workflow execution writes a real entry.
- `enable_telemetry=False` writes nothing.
- `calculate_savings()` over a seeded log returns expected percentages.

### Rollback plan

Telemetry is additive and can be disabled at three layers:

- **Per-workflow:** `enable_telemetry=False` in workflow construction.
- **Globally:** `enabled: false` in `~/.empathy/telemetry/config.json`.
- **At source:** revert the integration commit in `BaseWorkflow._call_llm()`.

The storage layer never affects workflow correctness — `track()` failures should be caught and logged, never re-raised. If a bug surfaces post-release, the global disable flag stops collection without a code change.

---

## Phase 4: Implementation

**Status**: complete

### Completion checklist

- [x] All tasks marked done
- [x] Tests pass (unit + integration in `tests/unit/telemetry/`)
- [x] Privacy audit completed; no prompts/responses/paths/credentials tracked
- [x] CLI commands shipped: `show`, `savings`, `compare`, `reset`, `export`
- [x] Integrated into `BaseWorkflow._call_llm()` — all workflows track automatically
- [x] Released in attune-ai v3.8.0
- [x] Documented in `docs/SECURITY_REVIEW.md` / privacy-compliance docs
