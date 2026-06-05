# Design: attune-verify — Generation Fact-Checker

**Status:** draft (2026-06-02) — Phase 2, awaiting review
**Requirements:** [requirements.md](requirements.md) (Phase 1
approved 2026-06-02)

> This design realizes the Phase-1 decisions: deterministic core +
> LLM semantic layer behind an injected `Judge` protocol; explicit
> `VerifyContext`; return-findings with an opt-in gate; library +
> `/verify` skill surfaces; standalone sibling package.

---

## Architecture overview

Two surfaces over one core:

```text
                    ┌─────────────────────────────┐
   library API ───▶ │  attune_verify.verify(...)  │
   (CI, pipelines)  │   - deterministic checkers  │
                    │   - semantic layer (opt)    │
   /verify skill ─▶ │   - Judge protocol (inject) │
   (Claude Code)    └─────────────┬───────────────┘
                                  │
                 ┌────────────────┴────────────────┐
                 ▼                                  ▼
        deterministic checkers              Judge (injected)
        (pure Python, no LLM)        skill-judge | rag adapter | custom
```

The **deterministic core** has zero LLM dependency and runs
everywhere. The **semantic layer** is optional and delegates to an
injected `Judge`; it never imports attune-rag directly.

---

## Module layout (`src/attune_verify/`)

| Module | Responsibility |
|--------|----------------|
| `__init__.py` | Public exports: `verify`, `VerifyContext`, `VerifyResult`, `Finding`, `Judge`, `raise_if_failed` |
| `context.py` | `VerifyContext` dataclass — the declared truth boundaries |
| `result.py` | `Finding`, `FindingKind`, `VerifyResult`, `raise_if_failed()` |
| `checkers/imports.py` | AST-walk code fences; resolve imports against the env |
| `checkers/flags.py` | Extract command+flag refs; resolve vs. captured `--help` |
| `checkers/links.py` | Resolve markdown link targets against the project root |
| `checkers/counts.py` | Compare numeric claims against caller-supplied sources |
| `semantic/protocol.py` | `Judge` protocol + `SemanticVerdict` |
| `semantic/rag_adapter.py` | Thin adapter over rag's `FaithfulnessJudge` (only under the `[rag]` extra) |
| `_extract.py` | Shared: pull code fences, links, numeric claims from content |

The `/verify` skill lives in the attune-ai plugin
(`plugin/skills/verify/`), not in this package — it invokes the
library for deterministic checks and supplies a skill-judge.

---

## Data model

```python
class FindingKind(str, Enum):
    UNRESOLVED_IMPORT = "unresolved_import"
    UNKNOWN_FLAG      = "unknown_flag"
    DEAD_LINK         = "dead_link"
    COUNT_MISMATCH    = "count_mismatch"
    SEMANTIC          = "semantic"

@dataclass(frozen=True)
class Finding:
    kind: FindingKind
    detail: str            # human-readable
    evidence: str          # the offending span from the content
    location: str | None   # line/section if resolvable
    severity: str          # "error" | "warning"

@dataclass
class VerifyResult:
    findings: list[Finding]
    checked: list[str]     # which checkers ran
    semantic_ran: bool     # whether the Judge was invoked
    @property
    def ok(self) -> bool:
        return not any(f.severity == "error" for f in self.findings)
```

`raise_if_failed(result)` raises `VerificationError` when
`not result.ok` — the opt-in hard gate. Default flow is
return-and-inspect.

---

## VerifyContext — auto-resolve lookups, caller declares boundaries

```python
@dataclass
class VerifyContext:
    project_root: Path | None = None      # for link resolution
    env_python: str | None = None         # default: sys.executable
    help_commands: dict[str, str] = field(default_factory=dict)
                                          # name -> captured --help text
    allowed_help_cmds: frozenset[str] = frozenset()
                                          # commands safe to run --help on
    count_sources: dict[str, int | Callable[[], int]] = field(default_factory=dict)
    judge: "Judge | None" = None          # semantic layer; None = skip
    semantic: bool = False                # opt-in semantic checking
```

Resolution policy (the Phase-1 decision made concrete):

- **Imports** — verify resolves via `importlib.util.find_spec`
  against `env_python` (default current interpreter). Caller picks
  the env; verify does the lookup.
- **Links** — verify stats targets relative to `project_root`.
  Caller declares the root; verify resolves.
- **Flags** — verify resolves a flag against `help_commands[cmd]`
  if pre-captured, else captures `--help` **only if `cmd in
  allowed_help_cmds`**. A command not pre-captured and not
  allow-listed yields a `warning`-severity finding ("could not
  verify"), never a silent pass and never an un-gated subprocess.
- **Counts** — never inferred; resolved only against
  `count_sources`. A numeric claim with no matching source →
  `warning` ("unverifiable count"), not an error.

**Security:** the `allowed_help_cmds` gate is the boundary that
keeps `--help` capture from running arbitrary command names lifted
from generated content. Generated code is never executed (req
criterion 5); only allow-listed CLIs are introspected.

---

## Judge protocol (Option C) + implementations

```python
@runtime_checkable
class Judge(Protocol):
    def score(self, query: str, answer: str,
              passages: str | list[str]) -> "SemanticVerdict": ...

@dataclass
class SemanticVerdict:
    faithful: bool
    issues: list[str]      # e.g. "insecure example: host=0.0.0.0, no auth note"
    raw: object | None     # underlying result, for debugging
```

The signature mirrors rag's `FaithfulnessJudge.score(query, answer,
passages)` (verified against installed rag 0.2.0) so the adapter is
near-trivial.

**Skill-judge (interactive default).** Lives in the `/verify`
skill, not this package. The skill runs the deterministic checks
via the library, then the ambient Claude Code agent performs the
semantic judgment and constructs a `SemanticVerdict` — no API call,
on-subscription. The skill injects this judge into
`VerifyContext.judge`.

**rag adapter (headless fallback).** `semantic/rag_adapter.py`,
imported only when the `[rag]` extra is installed:

```python
def make_rag_judge(**kw) -> Judge:
    from attune_rag.eval.faithfulness import FaithfulnessJudge
    inner = FaithfulnessJudge(**kw)
    class _Adapter:
        def score(self, query, answer, passages):
            r = asyncio.run(inner.score(query, answer, passages))
            return SemanticVerdict(faithful=r.is_faithful,
                                   issues=r.unsupported_claims, raw=r)
    return _Adapter()
```

Degradation: `semantic=True` with no `judge` and no `[rag]` extra
→ `VerifyResult.semantic_ran=False` + a single `warning` finding
("semantic layer requested but no judge available"). Deterministic
findings are unaffected.

> The exact rag `FaithfulnessResult` field names
> (`is_faithful` / `unsupported_claims` above) are a **Phase-3
> verification item** — confirm against installed rag before
> wiring the adapter.

---

## Public API

```python
def verify(content: str, context: VerifyContext) -> VerifyResult:
    """Run deterministic checkers (always) + semantic layer (if
    context.semantic and a judge is resolvable). Returns findings;
    never raises on findings (use raise_if_failed)."""
```

Deterministic checkers run unconditionally and independently — a
failure in one does not abort the others (each wrapped, errors
surfaced as `warning` findings, mirroring the discovery-sweep
source-isolation pattern).

> **Revision pending — see [decisions.md](decisions.md) D1
> (2026-06-04).** Deterministic and semantic findings are NOT fully
> independent: a 2026-06-04 dogfood showed the semantic judge emits
> false-positive entity-existence findings when source context is
> incomplete (9 of 9 flags were real symbols past the judge's
> window). D1 makes the layers **compose** — deterministic resolution
> is authoritative for entity existence and **suppresses** any
> semantic finding whose named entity resolves deterministically.
> This section's union semantics need a Phase-2 update accordingly.

---

## The `/verify` skill (attune-ai plugin)

- `plugin/skills/verify/SKILL.md` — triggers on "verify docs",
  "fact-check", "check this generated content".
- Flow: read target content + source → call
  `attune_verify.verify(content, ctx)` for deterministic findings →
  agent judges semantics (skill-judge) → present a unified findings
  report (deterministic + semantic).
- Adding the skill triggers the three plugin gates (skill count
  test; attune-hub reference table; `.agents/` mirror sync) — noted
  for tasks.md.

---

## Packaging (sibling pattern)

- Full source at `../attune-verify/`; pointer stub at
  `packages/attune-verify/README.md`; `[tool.uv.sources]` editable
  entry in attune-ai.
- Extras: `attune-verify` (deterministic core, zero heavy deps);
  `attune-verify[rag]` (pulls attune-rag for the adapter).
- Own `pypi` env; **publish 0.1.0 before** wiring the attune-author
  consumer so the integration is CI-testable (not `importorskip`-ed).
- **Repo creation (`gh repo create`) is an await-Patrick step** per
  the autonomous guardrails — not done unattended.

---

## Testing strategy

- **Deterministic checkers** — unit tests per checker; the
  load-bearing one is a **regression fixture rebuilt from the
  author-#351 hallucinations** (invented `--allow-run` flag, the
  `_readers`/`_models` private imports, the four dead "See also"
  links, the `498 templates` miscount, the `POST /run` route) —
  verify must flag each.
- **Semantic layer** — test with a `FakeJudge` (no API): inject a
  scripted `SemanticVerdict`, assert it surfaces as a `SEMANTIC`
  finding. Test the no-judge degrade path.
- **rag adapter** — guard with the `sys.modules[name] = None`
  sentinel to exercise the "rag absent" path cross-version
  (per the CLAUDE.md lesson on `find_spec` sentinels).
- **Security** — assert verify never executes generated code, and
  never runs `--help` for a command outside `allowed_help_cmds`.

---

## Open items carried to tasks.md / Phase 3

- Exact rag `FaithfulnessResult` field names (verify against
  installed rag before adapter wiring).
- `Judge.score` signature: keep rag's `(query, answer, passages)`
  or adopt a verify-native `(content, source)` and map in the
  adapter.
- How the `/verify` skill threads its `SemanticVerdict` back into a
  `VerifyResult` (skill returns structured findings vs. the library
  composing them).
- Whether `verify()` gets an async variant for the rag adapter
  (currently `asyncio.run` inside a sync wrapper — fine for CLI,
  awkward inside an existing event loop).
