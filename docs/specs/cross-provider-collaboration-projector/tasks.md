# Tasks — Cross-Provider Collaboration Projector

## Done (on codex/using-projectors — do not redo)

- [x] Master `content/collaboration/contract.md` (contract +
      handoff template sections).
- [x] Projector `scripts/project_collaboration_contract.py` with
      marker replacement, whole-file template write, `--check`.
- [x] Hardening (currently uncommitted in the working tree):
      preflight-before-mutation, `_validate_file_path` symlink
      containment, mkdir for the template parent.
- [x] 12 focused tests incl. failure-sensitive AC-1/AC-2/AC-3.
- [x] Projected blocks landed in AGENTS.md / .claude/CLAUDE.md /
      templates/agent-handoff.md, synchronized.

## Open — ratified 2026-07-18, ready to execute

- [ ] T1 (D3): wire the drift gate — pre-commit entry + CI step
      running `--check`; receipt = a deliberate master edit fails
      the gate naming the stale file (AC-4).
- [ ] T2 (D2): render the generated-source notice line inside the
      projected block; re-project; receipt = notice visible in both
      targets, `--check` still clean.
- [ ] T3 (D1): create the handoff home + a discovery line in the
      contract's Handoffs section; receipt = both agents locate the
      same artifact from a branch name alone.
- [ ] T4 (D4): reject duplicate required headings in the master;
      receipt = new test with a duplicated section fails loudly.
- [x] T5 — N/A per D5a: preflight + idempotent rerun accepted as
      the failure guarantee; no rollback work.
- [ ] T6: commit the uncommitted hardening + this spec on the
      feature branch; run the focused tests serially and attach the
      tail as the PR receipt.

## Non-goals (this spec)

- Productizing as an `attune` CLI feature (D6 recommends deferring).
- Any Codex hooks.json integration (dead in current build).
