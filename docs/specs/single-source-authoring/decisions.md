# Single-Source Authoring — Decisions

**Status:** draft (2026-06-30) · log for
[requirements.md](requirements.md) / [design.md](design.md).

## D1 — The session authors; a skill supplies the discipline

**Decided.** The replacement for the retired generator is not a smaller
generator — it is the driving session, made reliable by a skill that
encodes the authoring discipline (#1188's practices). The lesson is
empirical: the session is a *superior* polish layer and the only one that
catches correctness bugs. The skill's job is to make that quality
*repeatable* by any session, not to automate the prose.

## D2 — Verification is the spine, because it's the only thing separating authoring from fiction

**Decided.** The generator failed by writing confident, unverified prose
(six hallucination shapes). The session succeeds by *grounding every claim
in code first*. So the skill's load-bearing instruction is "find the truth
before you write it" — grep the symbol, run the audit, fix the master.
Without that, session-authoring is just a slower generator with the same
failure mode.

## D3 — Instructions for judgment, code for mechanics (shared with the consolidation)

**Decided.** Same principle as
[attune-author-consolidation D1](../attune-author-consolidation/decisions.md):
this skill is *instructions* because authoring is judgment; the projector,
scaffolder, and audits stay *code* because they must be invariant. The
skill never re-implements a deterministic tool — it calls it.

## D4 — Author against the manual baseline; repoint on consolidation

**Decided.** The skill can ship before the consolidation by naming today's
manual steps (#1189 playbook). Its *judgment content* (author + verify) is
independent of whether the projector lives in `attune_author` or
`attune.authoring`; only the tool paths it references change. So it isn't
blocked on the consolidation — repoint the references when that lands.

## D5 — Self-demonstration is the acceptance bar

**Decided.** The skill is "done" only when a fresh session, given *only*
the skill, reproduces the #1188 outcome (a green, code-accurate page) with
no out-of-band knowledge. That dogfood (T3) is the receipt — consistent
with "registered ≠ working; dogfood the live loop."

## D6 — Name: `author-feature`; T1 shipped against post-consolidation paths

**Decided (2026-06-30).** The skill is named **`author-feature`** —
verb-noun, matching the existing family (`bug-predict`, `fix-test`,
`refactor-plan`, `security-audit`), and most distinct from the
LLM-based `doc-gen` skill. T1 (author the skill + `.agents/` mirror)
landed: `plugin/skills/author-feature/SKILL.md` encodes the #1188/#1189
playbook with verification as the spine (D2), referencing the
**post-consolidation in-repo** projector (`attune.authoring.projector`
via `scripts/project_features.py`), the bundle sync
(`scripts/sync_help_bundle.py`), and the audits
(`audit_doc_imports.py`, `audit_docs_wiring.py`). Because the projector
already moved in-repo (#1193), D4's "repoint on consolidation" is
already satisfied for the projector path — the skill names
`attune.authoring`, not `attune_author`. The scaffolder
(`new_feature.py`) is **not** built yet, so the skill names the manual
project→sync→audit steps (D4 baseline); repoint to the scaffolder when
it lands. Guards: `plugin/skills` count 23→24; attune-hub Skills
Reference row added; 131 plugin tests green. The skill's own ENV/verify
gotchas were dogfood-confirmed live (bare `python -c` fails on the
editable mapping; `PYTHONPATH=src` + the audit resolve correctly).

**Still open:** T3 dogfood (R5/D5 self-demonstration — a fresh session
authors a throwaway feature page green on the first real attempt) and
T4 (retire #1189's playbook lesson into the skill) remain.

## Open

- **Boundary with the scaffolder** — the skill *calls* the scaffolder
  (once built); confirm at build time there's no overlap where both try
  to own the `features.yaml` entry or the build chain.
- **Boundary with the scaffolder** — the skill *calls* the scaffolder;
  confirm at build time there's no overlap where both try to own the
  features.yaml entry or the build chain. (They shouldn't: scaffolder owns
  mechanics, skill owns judgment.)
