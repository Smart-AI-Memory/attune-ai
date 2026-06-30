# Single-Source Authoring — Design

**Status:** draft (2026-06-30) · pairs with
[requirements.md](requirements.md).

## Shape: a skill that orchestrates judgment between two deterministic tools

```text
scaffolder.scaffold   →   [ SKILL: author + verify the master ]   →   scaffolder.build
   (mechanical)                    (judgment — this spec)              (mechanical)
```

The skill is the disciplined middle. It does not generate; it *walks the
session* through authoring a master that is correct by verification, then
hands off to the deterministic build.

## The skill's flow (what `SKILL.md` encodes)

1. **Locate or scaffold.** If no master exists, invoke the scaffolder
   (`scaffold <slug> …`) to lay down frontmatter + the section skeleton.
   If revising, open the existing master.
2. **Author section by section, grounded in code.** For each section the
   projector expects, the skill instructs: *find the truth first.* Before
   an API table — `grep` the `__all__`, the enum, the tool schema. Before
   a CLI example — confirm the flag. The skill names the canonical
   verification commands (the ones #1188 used) so the session doesn't
   improvise.
3. **Verify continuously.** Run `audit_doc_imports.py --paths <master>`
   and the projector `--dry-run`; fix findings *at the master*. The skill
   frames a fact-check finding as "fix the claim," never "ship the
   warning."
4. **Build + confirm.** Hand off to `scaffolder build <slug>` (project →
   sync → audits) and confirm green.
5. **Preview before commit.** Show the projected hub/pages to the user
   before staging (the "show generated output sooner" discipline).

## What the skill explicitly does NOT do

- It does not write prose for the user to approve blindly — the model
  authors *with* verification, not from imagination.
- It does not call any LLM-polish/generation path (none will exist
  post-consolidation).
- It does not re-implement the projector, the audits, or the scaffolder —
  it *calls* them.

## Relationship to the three pieces

| Piece | Kind | Owns |
|---|---|---|
| scaffolder (#1190) | deterministic code | mechanical setup + build chain |
| projector (consolidation) | deterministic code | the master → 14 artifacts fan-out |
| **this skill** | **instructions** | **the judgment: author + verify the master** |

This is the authoring-vs-mechanics split made concrete: two tools that
must be invariant, one skill that supplies the judgment between them.

## Tasks / sequencing

1. **T1 — Author the skill.** `plugin/skills/single-source-authoring/
   SKILL.md` (name TBD): the flow above, the canonical verification
   commands, the section contract, the "fix the master not the output"
   framing. Sync the `.agents/` mirror.
2. **T2 — Wire the references.** Point the skill at the post-consolidation
   in-repo machinery (`attune.authoring.*`, `scripts/new_feature.py` from
   the scaffolder spec, the audits). If the scaffolder isn't built yet,
   the skill names the manual `project_features.py` + `sync_help_bundle.py`
   steps and is updated when the scaffolder lands.
3. **T3 — Dogfood.** A fresh session (or a clean transcript) uses only the
   skill to author a throwaway feature page; it must project clean and
   pass the gates on the first real attempt (R5). Record the receipt.
4. **T4 — Retire the playbook lesson into the skill.** #1189's playbook
   lesson points to the skill as the canonical authoring path (parallels
   the scaffolder's T4 for the mechanical half).

## Dependency note

This skill's *content* assumes the consolidation has moved the projector
in-repo (so it references `attune.authoring`, not `attune_author`). It can
be authored against today's paths and updated on consolidation, or
sequenced after T1–T2 of the consolidation. Recommend: author the skill
now against the *manual* steps (#1189 baseline), repoint its references
when the consolidation lands — the judgment content doesn't change, only
the tool paths it names.
