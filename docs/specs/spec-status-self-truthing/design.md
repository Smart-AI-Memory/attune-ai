# Design — Self-truthing spec status

**Status:** approved
**Phase 1:** [requirements.md](./requirements.md) — locked 2026-05-31
**Decisions:** [decisions.md](./decisions.md) — 3 DECIDEs ratified

Translates Phase 1's three DECIDEs into concrete regex patterns,
`SpecInfo` field shapes, and the `spec_orient` output format. No
new user-facing decisions; this file is the implementation contract.

---

## Files touched

| File | Change kind |
|---|---|
| `plugin/hooks/_state.py` | Add reader + reconciler, extend `SpecInfo` (additive) |
| `plugin/hooks/spec_orient.py` | Render `effective_status` + conflict hint |
| `tests/unit/hooks/test_session_continuity_state.py` | New test class with 5 reconciliation cases |

No new files. No deleted files. No migrations.

---

## Regex contracts

### Terminal-line scan (DECIDE-2)

```python
_TERMINAL_LINE = re.compile(
    r"^\s*(?:Spec\s+)?Status\s*:\s*(closed|complete|retired|superseded)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
```

Matches anywhere in the file (not just header). Case-insensitive,
multiline-anchored. Captures the terminal keyword for source
attribution.

The five recognized terminal keywords from decisions.md DECIDE-2:
`Spec status: closed` | `Status: complete` | `Status: closed` |
`Status: retired` | `Status: superseded`.

### Completion-checklist section (DECIDE-2)

```python
_CHECKLIST_HEADING = re.compile(
    r"^##\s+Completion\s+checklist\s*$",
    re.IGNORECASE | re.MULTILINE,
)

_CHECKLIST_LINE = re.compile(
    r"^\s*-\s*\[([ xX])\]\s+(.*?)\s*$",
    re.MULTILINE,
)

_DEFERRED_MARKERS = re.compile(
    r"(~~.*?~~|\bdeferred\b|\bN/A\b|\bwon't\s+do\b)",
    re.IGNORECASE,
)
```

Extraction rule: find the `## Completion checklist` heading. The
checklist section is everything from that heading to the next `## `
heading or EOF. Within the section, walk every `- [ ]` / `- [x]`
line. A line is *deferred* if it matches `_DEFERRED_MARKERS`
(struck-through, "deferred", "N/A", "won't do"). A line is
*outstanding* if checked-box is empty AND not deferred. The
checklist is complete when no lines are outstanding.

### Edge cases

- **No checklist heading present** → checklist contributes no signal
- **Empty checklist section** → no items, so 0 outstanding =
  complete by vacuous truth. To prevent spurious "done" verdicts
  from empty sections, the reconciler requires at least ONE checked
  item OR a terminal line elsewhere in the file.
- **Malformed checklist (corrupt markdown)** → `_CHECKLIST_LINE`
  matcher returns nothing usable. Treat as no signal; fall back
  to header.

---

## `SpecInfo` field shape

Additive fields. Existing `.status` (raw header) stays for
back-compat — no consumer breaks. Wrap new fields in
`field(default=...)` so the constructor's call signature stays
unchanged.

```python
@dataclass(frozen=True)
class SpecInfo:
    slug: str
    path: Path
    layer: str
    phase: str
    status: str                            # raw header value (unchanged)
    mtime: float

    # New in 2026-06-02 — self-truthing additions
    effective_status: str = ""             # reconciled verdict
    status_source: str = "header"          # "header" | "checklist" | "terminal-line"
    status_conflict: bool = False          # header != effective
```

Defaults ensure existing tests that construct `SpecInfo`
positionally don't break.

---

## Completion-signal reader

```python
def _completion_signal(text: str) -> tuple[str | None, str]:
    """Read terminal markers from a phase file's text.

    Returns:
        (verdict, source) where:
        - verdict is "closed" / "complete" / "retired" / "superseded"
          if a terminal signal exists, else None.
        - source is "terminal-line" or "checklist" when verdict is
          non-None, else "header".
    """
    # 1. Terminal-line scan — short-circuit on first hit
    match = _TERMINAL_LINE.search(text)
    if match:
        return match.group(1).lower(), "terminal-line"

    # 2. Completion-checklist scan
    heading = _CHECKLIST_HEADING.search(text)
    if heading is None:
        return None, "header"

    section_start = heading.end()
    next_heading = re.search(r"^##\s+", text[section_start:], re.MULTILINE)
    section_end = section_start + next_heading.start() if next_heading else len(text)
    section = text[section_start:section_end]

    items = list(_CHECKLIST_LINE.finditer(section))
    if not items:
        return None, "header"

    checked = 0
    outstanding = 0
    for item in items:
        box, body = item.group(1), item.group(2)
        if _DEFERRED_MARKERS.search(body):
            continue  # deferred — not outstanding
        if box.strip().lower() == "x":
            checked += 1
        else:
            outstanding += 1

    # All checked, at least one checked (guards against empty/all-deferred sections)
    if checked > 0 and outstanding == 0:
        return "complete", "checklist"

    return None, "header"
```

---

## Reconciler

```python
def _reconcile_status(
    header_status: str, phase_text: str
) -> tuple[str, str, bool]:
    """Reconcile header status against completion signals.

    Returns:
        (effective_status, status_source, status_conflict)
    """
    verdict, source = _completion_signal(phase_text)
    if verdict is None:
        # No terminal signal — fall back to header
        return header_status, "header", False

    # Terminal signal exists. Per DECIDE-1, terminal wins.
    is_header_terminal = header_status in {"closed", "complete", "retired", "superseded"}
    return verdict, source, not is_header_terminal
```

---

## Integration into `_phase_for_dir`

`_phase_for_dir` currently returns `(phase, status, mtime)`. Extend
to return reconciled fields. Callers update accordingly.

```python
def _phase_for_dir(spec_dir: Path) -> tuple[str, str, str, str, bool, float] | None:
    """Returns (phase, raw_status, effective_status, source, conflict, mtime)."""
    ...
    if chosen is None:
        return None
    phase, raw_status, phase_text = chosen
    effective, source, conflict = _reconcile_status(raw_status, phase_text)
    return phase, raw_status, effective, source, conflict, latest_mtime
```

`_phase_for_dir` now needs the phase file's TEXT (not just status)
to feed the reconciler. Refactor `_read_status` callers to read
once and pass both the parsed status and the full text. Simplest
shape: a helper `_read_phase(path) -> tuple[str, str]` returning
`(status, text)`.

---

## Integration into `_is_in_flight`

Existing signature stays, but now consults the reconciled verdict
when called:

```python
def _is_in_flight(phase: str, effective_status: str) -> bool:
    """Pass the reconciled effective_status, not the raw header.

    Terminal effective statuses (closed/complete/retired/superseded)
    mark the spec done regardless of phase.
    """
    if effective_status in {"closed", "complete", "retired", "superseded"}:
        return False
    return True
```

Callers in `_state.py:206` pass `effective_status` instead of the
raw header `status`.

---

## `spec_orient` output format (DECIDE-3)

When `status_conflict` is True, append a parenthetical hint to the
spec line. Format:

```
- attune-ai/specs/architecture-realignment/  (tasks closed — header still says "draft", worth fixing)
```

Implementation in `_format_phase`:

```python
def _format_phase(spec: SpecInfo) -> str:
    phase_label = {
        "requirements": "requirements",
        "design": "design",
        "tasks": "tasks",
    }.get(spec.phase, spec.phase)
    effective = spec.effective_status or spec.status or "no status"
    base = f"{phase_label} {effective}"
    if spec.status_conflict:
        source_label = {"checklist": "tasks closed per checklist",
                        "terminal-line": "marked terminal in body"}.get(
                            spec.status_source, spec.status_source)
        raw = spec.status or "no header"
        return f"{base} — {source_label}; header says \"{raw}\", worth fixing"
    return base
```

The conflict hint never exceeds one line and never breaks the
existing markdown list structure.

---

## Test plan

Five new test cases in
`tests/unit/hooks/test_session_continuity_state.py` (new
`TestStatusReconciliation` class), all using fixture spec dirs
constructed under `tmp_path`:

1. **`test_architecture_realignment_shape`** — draft header +
   closed checklist with deferred rows. Asserts
   `effective_status == "complete"`, `status_source == "checklist"`,
   `status_conflict is True`, `_is_in_flight()` returns False.

2. **`test_approved_header_with_partial_checklist`** — header
   `approved`, checklist mid-progress. Asserts
   `effective_status == "approved"`, no conflict, in-flight.

3. **`test_no_checklist_no_terminal_line`** — header-only
   behavior. Asserts `effective_status == raw status`,
   `status_source == "header"`, no conflict.

4. **`test_malformed_checklist_falls_back`** — checklist heading
   present, body corrupted (e.g. raw text, no `- [ ]` lines).
   Asserts no crash, no conflict, fallback to header.

5. **`test_terminal_line_overrides_stale_header`** — header
   `approved`, body contains `Status: complete`. Asserts
   `effective_status == "complete"`,
   `status_source == "terminal-line"`,
   `status_conflict is True`.

A sixth test verifies `_format_phase` rendering for both
conflict-True and conflict-False cases — guards against output
regressions.

---

## Rollback strategy

Single PR. Revert restores header-only `_is_in_flight`. Additive
`SpecInfo` fields don't appear in any persisted state; no
migration. Existing tests reading `.status` are unaffected since
`.status` retains its raw-header meaning.

---

## Performance budget

The reconciler runs once per spec at SessionStart. With ~50 specs
× ~10 KB per file × `_TERMINAL_LINE` short-circuit on first match,
expected total cost: well under 100ms across all specs combined.
Heaviest case is a spec whose tasks.md has no terminal line and a
long completion checklist; even then a single regex scan over
~10 KB is sub-millisecond. No performance regression risk.

---

## Phase 3: Tasks — *(not started; will be authored after design approval if needed; XML prompt at `~/.attune/next_session_xml_prompts.md` already decomposes implementation)*
