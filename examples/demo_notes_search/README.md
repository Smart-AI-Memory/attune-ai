# Notes search — the tutorial demo fixture

Demo data for attune-ai tutorials and dry runs. Every tutorial
works on this same small, offline module so takes are repeatable
and start from identical state.

Scoped live via the dynamic-forms session on 2026-07-24
(`resp-20260724-105201`) and **frozen that day** — change it only
by re-scoping, not in passing cleanups.

## What's here

| File | What |
|------|------|
| `notes_search.py` | The module under demo: load, index, search notes |
| `sample_notes.md` | Five generic notes (no real names, keys, or services) |
| `test_notes_search.py` | The fixture's test suite |

## Seeded on purpose — do not "fix" outside a tutorial

- **One failing test** — `test_search_is_case_insensitive` fails
  because `_tokenize` keeps token case (the seeded bug is marked in
  the source). The fix-test tutorial fixes it live; the fix is one
  line.
- **Coverage gaps** — `remove()`, `snippet()`, and `stats()` have no
  tests. The smart-test tutorial finds and closes them.

Everything else passes and stays green.

## Running it

The repo's pytest config only collects `tests/`, so this suite never
runs in CI. Run it directly:

```bash
pytest examples/demo_notes_search/test_notes_search.py -p no:cacheprovider -o addopts=
```

Expected before the tutorial: 1 failed, 8 passed. After the
fix-test tutorial: 9 passed.

## Reset after a take

```bash
git checkout -- examples/demo_notes_search/
```
