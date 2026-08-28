# Round table — marking intentionally-public endpoints (2026-08-28)

Thread: `q-wizards-public-catalog-sequencing-001` (Redis board, TTL 7d).
Full transcript (moderator development data, untracked):
`~/.attune/reports/roundtable/q-wizards-public-catalog-sequencing-001.md`.

The thread's original subject — how to sequence a `backend/api/wizards.py`
fix against PR #2342 — is spent: the chair's ruling was executed as
PR #2344, and both that PR and the whole `backend/` tree were retired on
2026-08-28 (PR #2345, after the chair confirmed the app had no deploy
target). That ruling was **declined for promotion** and is not recorded
here.

What survived the deletion are two member-originated questions (R9) that
were never triaged. They are promoted because they generalize past
`backend/`: they are about the codebase's inability to distinguish an
intentionally-public route from an authentication gap.

## Chair-promoted items (2026-08-28)

**Board message 5 — claude, question:**

> Should the intentional-public decision live somewhere more durable than
> the PR description (a one-line router code comment + a decisions.md
> note), given #2342 makes "public API route" look like a bug everywhere
> else?

**Board message 6 — antigravity, question:**

> When #2342 lands and makes `require_principal` the backend standard, is
> there an agreed decorator/tag/metadata convention to annotate
> intentionally-public endpoints so automated audits/sweeps do not flag
> them as gaps?

## Why these still apply (verified 2026-08-28, post-deletion)

Probed against the surviving tree at `87f1084b1`:

- **No convention exists.** A repo-wide grep for `PUBLIC_ENDPOINT`,
  `INTENTIONALLY_PUBLIC`, `intentionally public`, and `# public:` over
  `src/` returns nothing. There is no decorator, tag, or comment form an
  audit could key on.
- **29 of 50 `attune/ops` routes sit in files with no
  `require_client_token` reference.** Stated precisely, because the raw
  number invites the wrong conclusion: these are largely GET reads on a
  loopback-bound dashboard, and the token gate is applied to *mutating*
  routes by design (`ops/security.py`). They are not 29 security holes.
  They are 29 routes whose public-versus-private **intent is not
  expressed in code** — which is the exact gap the questions name.

The failure mode is documented and has already fired once: intentional
public routes were read as an auth omission and "harmonized" back to
protected. Without a marker, every future auth sweep re-litigates the
same routes, and the only record of intent is a PR description that no
scanner reads.

## Disposition

Recorded as an open question, not a decision. No convention is adopted
here and no code is changed.

Suggested tier if the chair later picks it up: **structured one-shot** —
a marker (decorator or module-level constant) plus a gate that reads it,
so an unmarked unauthenticated route is a finding and a marked one is
silent. That is small enough not to need a spec, and it converts the
question into an enforcer rather than another line of prose.

Provenance: promoted per-item (R4) from board thread
`q-wizards-public-catalog-sequencing-001`, message ids 5 and 6. Other
messages in that thread were declined and are not recorded in-repo.
