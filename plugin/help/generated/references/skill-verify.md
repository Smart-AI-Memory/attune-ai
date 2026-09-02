---
type: reference
subtype: procedural
name: skill-verify
category: skill
tags: [skill, plugin]
source: plugin/skills/verify/SKILL.md
---

# Reference: Skill: verify

Fact-check LLM-generated content against source-of-truth — confirm imports import, CLI flags are real, links resolve, counts match. Triggers on: verify docs, fact-check, did the model hallucinate, check generated content, are these claims real.

**Usage:** `/verify <path to the generated file to fact-check>`

## What It Does

`/verify` is the output-side fact-checker for LLM-generated content
(docs, READMEs, tutorials). It catches the hallucination classes that
unit tests never see — an invented CLI flag, an import of a package
that doesn't exist, a dead cross-reference, a wrong count — by
confirming the *named entities* in the content actually exist.

It runs in two layers:

1. **Deterministic checkers** (`attune_verify`, authoritative): the
   *top-level package* of each import resolves via `find_spec`, CLI
   flags appear in `--help`, markdown links resolve under the project
   root, numeric claims match a declared count source. These are ground
   truth — no LLM, no guessing.
2. **Ambient semantic cross-check** (you, the agent): after the
   deterministic pass, read the content against its source and flag
   claims the checkers can't see (a security caveat dropped, a route
   path that's plausible-but-wrong, a *private submodule* of an
   installed package that doesn't actually exist — the import checker
   only validates the top-level package, so `from pkg.fake_sub import X`
   passes deterministically when `pkg` is installed). This layer is a
   *cross-check only* — it over-flags on truncated context, so never let
   it override a deterministic pass. If the deterministic layer says a
   top-level import resolves, it resolves.

## How To Run It



### Shared command workspace (preferred)

Open adapter `verify` with the validated generated-content path and optional
`hard_gate=true` for pipeline callers. The invocation authorizes this
read-only run, so there is no confirmation action. Execute
`attune_verify.verify` exactly as below and publish its authoritative outcome
as `deterministic_result`, retaining every finding's kind, severity, detail,
evidence, and location.

Perform the ambient semantic pass only after the deterministic result and
publish it as `cross_check_result`. Ambient findings remain explicitly labeled
warnings and cannot override deterministic entity-existence results. In hard
gate mode, any deterministic error keeps `hard_gate_passed=false`. Checker or
cross-check failure must render “did not complete,” never a clean report.
Present the terminal widget or Markdown and preserve the full evidence chain
in text fallback.

The deterministic layer is `attune_verify.verify(content, context)`.
The caller declares the truth boundaries; verify performs the lookups —
it never auto-discovers them. Run this via Bash from the project root,
passing the file under test as `F`:

```bash
F="<path/to/generated.md>" python -c "
import json, os
from pathlib import Path
from attune_verify import verify, VerifyContext
content = Path(os.environ['F']).read_text(encoding='utf-8')
ctx = VerifyContext(project_root=Path.cwd())
result = verify(content, ctx)
print(json.dumps({
    'ok': result.ok,
    'checked': result.checked,
    'findings': [
        {'kind': f.kind.value, 'severity': f.severity,
         'detail': f.detail, 'evidence': f.evidence, 'location': f.location}
        for f in result.findings
    ],
}, ensure_ascii=False, indent=2))
"
```

Then present the findings as a readable report (errors first, then
warnings), grouped by kind. Each finding carries `kind`
(`unresolved_import` / `unknown_flag` / `dead_link` / `count_mismatch`),
`severity` (`error` | `warning`), `detail`, `evidence`, and `location`.

## Declaring Tighter Boundaries

The default context only checks imports and links (project root). To
catch flag and count hallucinations, declare the sources the content
claims against — `VerifyContext` is the single place to do it:

- **CLI flags** — pre-capture `--help` and pass it so the checker
  knows the real flags:

  ```python
  ctx = VerifyContext(
      project_root=Path.cwd(),
      help_commands={"attune": <captured --help text>},
      allowed_help_cmds=frozenset({"attune"}),  # safe to shell out to
  )
  ```

- **Counts** — declare what a number should be, by label. Values may be
  plain ints or zero-arg callables:

  ```python
  ctx = VerifyContext(
      project_root=Path.cwd(),
      count_sources={"templates": 259, "skills": lambda: len(skill_dirs)},
  )
  ```

A flag whose command is neither pre-captured nor in `allowed_help_cmds`
yields a **warning, not a silent pass** — surface it so the user knows
it went unchecked.

## Reading The Report

- **`result.ok is False`** → at least one error-severity finding. These
  are confirmed hallucinations (the import does not resolve, the flag is
  not in `--help`). Quote the `evidence` line and point at where to fix.
- **Warnings** → something couldn't be checked (no count source
  declared, a command not on the allow-list). Not a failure — a gap in
  the declared boundaries. Tell the user what to declare to close it.
- **Empty findings** → the deterministic layer found nothing wrong.
  Then do the ambient semantic cross-check and report any claims worth a
  human's eye, clearly labeled as cross-check (not deterministic).

Do **not** invent findings, and do **not** soften a deterministic error
into a "maybe" — the checkers are authoritative for entity existence.

## When It Belongs In A Pipeline

For a hard gate (fail the run on any error finding), the library
exposes `raise_if_failed(result)`. The `/verify` skill itself is the
interactive, report-only surface — it never hard-gates. The hard gate
is for callers like attune-author's post-generation step.

## Related Topics

_No related topics yet._
