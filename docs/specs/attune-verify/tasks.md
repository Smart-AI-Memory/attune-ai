# Tasks: attune-verify — Generation Fact-Checker

**Status:** in progress (2026-06-09) — **library SHIPPED, /verify skill
SHIPPED; one task (T7) remains.** The `attune-verify` package is published
to PyPI as v0.1.0 (`Smart-AI-Memory/attune-verify`): T1 (skeleton), T2
(model), T3 (deterministic checkers + the author-#351 regression fixture),
T4 (semantic Judge), T5 (rag adapter), T8 (publish) **done**. On the
attune-ai side: `attune-verify>=0.1.0,<0.2` is now a **core dependency**
(stdlib-only, zero transitive deps) and the **T6 `/verify` skill** is
shipped (`plugin/skills/verify/`, all three plugin gates green:
skill-count, attune-hub reference row, `.agents` mirror sync). The status
once said "draft" only because the library work landed in a sibling repo
the spec-status reconciler can't see (caught 2026-06-09 spec triage — the
status-lies trap across a repo boundary).
**Remaining:** T7 attune-author polish integration (sibling repo, now
unblocked — verify is on PyPI so author CI can exercise it, not
`importorskip`).
**Design:** [design.md](design.md) · **Requirements:**
[requirements.md](requirements.md)

> Independently shippable units. Order respects dependencies.
> Two units are **await-Patrick** (repo creation, PyPI publish) per
> the autonomous guardrails — flagged ⛔.

---

## Dependency order

```text
T1 (repo skeleton ⛔) ─▶ T2 (model) ─▶ T3 (deterministic checkers)
                                    └─▶ T4 (Judge + semantic plumbing)
                                              └─▶ T5 (rag adapter)
T2,T3 ─▶ T6 (/verify skill)
T1 ─▶ T8 (publish 0.1.0 ⛔) ─▶ T7 (author integration)
```

---

## T1 — Sibling repo + package skeleton ⛔ (await-Patrick: repo creation)

**Objective:** stand up `attune-verify` as a family sibling.

- Create `../attune-verify/` (full source), `packages/attune-verify/
  README.md` pointer stub, `[tool.uv.sources]` editable entry in
  attune-ai's `pyproject.toml`.
- `pyproject.toml`: core deps minimal (stdlib-only target); extras
  `[rag]` → `attune-rag`; `[dev]` → pytest etc.
- CI mirroring the family (tests matrix, lint, signed releases),
  `pypi` env.

**Acceptance:** `uv pip install -e ../attune-verify` imports;
`attune-verify` console entry resolves.
**Blocked on:** `gh repo create` — Patrick runs or authorizes.

---

## T2 — Data model + VerifyContext

**Objective:** the typed surface everything else builds on.

- `result.py`: `FindingKind`, `Finding` (frozen), `VerifyResult`
  (`.ok`), `VerificationError`, `raise_if_failed()`.
- `context.py`: `VerifyContext` (project_root, env_python,
  help_commands, allowed_help_cmds, count_sources, judge, semantic).
- `__init__.py` exports.

**Acceptance:** unit tests construct each type; `VerifyResult.ok`
true/false by severity; `raise_if_failed` raises only on errors.

---

## T3 — Deterministic checkers + author-#351 regression fixture

**Objective:** the no-LLM core (5 of 6 classes).

- `_extract.py`: pull code fences, links, numeric claims.
- `checkers/imports.py` (`find_spec` vs `env_python`),
  `flags.py` (vs `help_commands` / gated `--help` capture),
  `links.py` (vs `project_root`), `counts.py` (vs `count_sources`).
- Per-checker error isolation (one checker failing → `warning`
  finding, others still run).
- `verify()` orchestration (deterministic path).

**Acceptance:** a **regression fixture rebuilt from author-#351**
(invented `--allow-run`; `_readers`/`_models` imports; 4 dead "See
also" links; `498 templates` miscount; `POST /run` route) — verify
flags each. Security test: never runs `--help` for a command
outside `allowed_help_cmds`; never executes fence code.

---

## T4 — Judge protocol + semantic plumbing

**Objective:** the injected semantic layer (no rag import here).

- `semantic/protocol.py`: `Judge` Protocol, `SemanticVerdict`.
- `verify()` semantic branch: if `context.semantic` and a judge is
  present, run it → `SEMANTIC` findings; else degrade path
  (`semantic_ran=False` + one `warning`).

**Acceptance:** `FakeJudge` (scripted verdict, no API) surfaces a
`SEMANTIC` finding; no-judge + `semantic=True` → graceful warning,
deterministic findings intact.

---

## T4b — Semantic/deterministic cross-check suppression ([decisions.md](decisions.md) D1)

**Objective:** stop the semantic layer from emitting false-positive
entity-existence findings. Per D1, deterministic resolution is
authoritative for "does this entity exist?" and disciplines the judge.

- After both layers run, **suppress** any `SEMANTIC` finding whose
  evidence names an entity (import, symbol, flag, link) that the
  deterministic resolvers can resolve — it is a context-truncation
  false positive, not a hallucination.
- v1: post-filter the union. v2 (follow-up): scope the judge prompt
  to non-entity claims so the false positive never forms.

**Acceptance:** a fixture where the judge flags a symbol that IS
defined in the (caller-supplied) source yields **no** finding;
a fixture where the judge flags a genuinely-absent symbol **does**
surface. Regression: replay the 2026-06-04 dogfood shape — 9 flagged,
all real → 0 surfaced findings.

---

## T5 — rag adapter ([rag] extra)

**Objective:** headless semantic judge via attune-rag.

- **Phase-3 pre-step:** verify rag `FaithfulnessResult` field names
  against installed attune-rag (design used placeholder
  `is_faithful`/`unsupported_claims`).
- `semantic/rag_adapter.py`: `make_rag_judge(**kw)` wrapping
  `FaithfulnessJudge.score`; lazy import under `[rag]`.

**Acceptance:** adapter satisfies `Judge`; `sys.modules[name]=None`
sentinel test proves clean degradation when rag absent.

---

## T6 — `/verify` skill (attune-ai plugin) ✅ DONE

**Status:** shipped. `plugin/skills/verify/SKILL.md` + `.agents` mirror;
all three plugin gates green; `attune-verify` wired as a core dependency.
Dogfooded against a known-bad doc (caught the dead link; documented the
top-level-only import-checker limitation in the skill body).

**Objective:** the interactive, on-subscription surface.

- `plugin/skills/verify/SKILL.md` (+ `.agents/skills/verify/`
  mirror via `scripts/sync_agents_skills.py`).
- Flow: deterministic checks via library → ambient-agent
  skill-judge → unified findings report.
- **Three plugin gates:** bump skill-count test; add row to
  attune-hub reference table; run the `.agents` mirror sync.

**Acceptance:** the three plugin-config tests pass; skill triggers
on "fact-check"/"verify docs".

---

## T7 — attune-author polish integration (first consumer)

**Objective:** wire verify as author's post-generation gate.

- author polish calls `attune_verify.verify(content, ctx)` after
  generation; surfaces findings (return, not hard-gate by default).

**Acceptance:** author's polish run on a known-hallucinated fixture
reports verify findings.
**Blocked on:** T8 (verify on PyPI) so author CI exercises it
rather than `importorskip`.

---

## T8 — Publish 0.1.0 ⛔ (await-Patrick: PyPI publish) + docs flip ✅ DONE

**Status:** `attune-verify` 0.1.0 published to PyPI via trusted publishing
(2026-06-09, first-publish pending-publisher). Now resolvable as a core dep
in attune-ai.

**Objective:** make verify resolvable + visible.

- Publish `attune-verify` 0.1.0 (trusted publishing).
- Flip family docs/README from roadmap → available (criterion 6) —
  only now that it ships.

**Blocked on:** Patrick (publish + the `pypi` env approval).

---

## Notes

- T1 and T8 are the only Patrick-gated units; T2–T6 are codeable
  autonomously once T1's repo exists.
- Tasks may shift if design.md changes on review.
