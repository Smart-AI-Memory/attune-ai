# Per-file resolution decisions — `--ignore`-d test files

Append-only log. One section per file as it's resolved. See `requirements.md`,
`design.md`, `tasks.md` for the framework.

---

## `tests/unit/workflows/test_orchestrated_release_prep.py`

**Date:** 2026-05-09
**Initial classification:** R1 REPAIR (5/35 fail, 14%)
**Final classification:** **R3 RETIRE — no salvage**
**Action:** File deleted.

**Why the reclassification.** A 30-minute read of
`src/attune/workflows/orchestrated_release_prep.py` surfaced what the
audit didn't: the production module is **explicitly deprecated**.
Header at lines 3–5 reads ".. deprecated:: 5.2.0 — use
`ReleasePrepTeamWorkflow` from `attune.agents.release`. Remove in v6.0."
Current attune-ai is **v6.6.0** (`pyproject.toml`), so the module is
six minor versions past its scheduled removal date and still around for
backwards-compat re-exports.

**Why no salvage.**

- The replacement, `ReleasePrepTeamWorkflow`, exists at
  `src/attune/agents/release/release_prep_team.py:359` and has its
  own tests at `tests/unit/agents/test_release_prep_team.py`.
- The dataclasses being tested (`QualityGate`, `ReleaseReadinessReport`)
  are **duplicated** in `src/attune/agents/release/release_models.py`
  with their own tests at `tests/unit/agents/release/test_release_models.py`.
  The deprecated module re-exports the old copies; the new copies are
  the live ones.
- The 30 "passing" tests were therefore not unique coverage — they
  test code that's on the way out, with parallel coverage already
  in place for the live equivalents.

**Recovering passing tests as active coverage** (G3 from
requirements.md) is moot here: the tests assert the API of a
deprecated module. Rewriting them against the new module would
duplicate `tests/unit/agents/release/test_release_models.py` and
`tests/unit/agents/test_release_prep_team.py`. Better to delete.

**Out-of-scope follow-up:** the production module itself is overdue
for removal (deprecated v5.2.0 → "Remove in v6.0" → we are at v6.6.0).
That deletion is **not** part of this spec — flagging it for a
separate task. Risk to be aware of if removed: the re-exports at
`src/attune/workflows/__init__.py:160` and `src/attune/agents/__init__.py`
must be updated, and downstream consumers may import from the
deprecated path.
