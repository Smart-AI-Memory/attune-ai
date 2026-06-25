# attune-docs Marketplace — Decisions

**Status:** complete 2026-06-22 — Option A (retire + consolidate)
ratified and shipped; see `tasks.md` for the PR trail.

---

## D1 — Direction: keep, automate, or retire

**Decision:** **A — retire + consolidate** (ratified by Patrick,
2026-06-22).

**Options:** A (retire + consolidate, recommended) · B (keep + automate)
· C (status quo, rejected).

**Context:** see `requirements.md`. The marketplace is frozen since
2026-05-06, has no CI, and ships plugins ~15 minor versions stale; the
project is consolidating onto attune-ai.dev. The April split's promised
independent release cadence was never realized, so the maintenance
liability is not buying anything.

---

## D2 — Target home for the plugins

**Decision:** **proposed — `attune-ai` marketplace** (confirm before
execution).

`attune-ai.dev` is a website, not a `claude plugin marketplace add`
target, so the Claude Code plugins must live in a marketplace repo. The
natural home is the existing `Smart-AI-Memory/attune-ai` marketplace
(already clean, already the canonical dev-tool front door). Install
becomes `claude plugin install attune-help@attune-ai` /
`attune-author@attune-ai`. attune-ai.dev remains the web/docs home, not
a plugin source.

---

## D3 — Migration path for existing marketplace users

**Decision:** **proposed** (confirm before execution).

Before archiving `attune-docs`: replace its README with a migration
note pointing to the attune-ai marketplace, and keep the repo public
(archived, read-only) so `claude plugin marketplace add
Smart-AI-Memory/attune-docs` adders find the redirect rather than a
404. Do NOT delete the repo.

---

## D4 — If B: sync mechanism

**Decision:** N/A — Option B not chosen.
