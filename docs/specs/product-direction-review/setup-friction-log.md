# Setup Friction Log — Fresh-Machine Reproduction

**Run:** 2026-07-11, clean Linux sandbox (Ubuntu 22.04, Python
3.10.12), fresh venv, zero prior attune state. Agent executed the
README exactly as a new user would. Package: attune-ai 10.3.0 from
PyPI.
**Context:** weekend-plan Block 1; motivated by conversation 1's
"setup issues" signal.
**Caveats:** non-TTY shell, so the D11 consent prompt path was not
exercised; sandbox network is fast (home installs will be slower);
the venv-without-pip hiccup at the start was an Ubuntu artifact, not
attune's.

---

## Timeline

| t | Step | Result |
|---|------|--------|
| 0:00 | Read README for the pip path | "Get Started in 60 Seconds" ends at `pip install attune-ai` — **no first command given** (F5) |
| 0:01 | `pip install attune-ai` | Clean. 72 packages, ~40 s on fast network, no build errors |
| 0:02 | Guessed `attune` (README didn't say) | **Excellent** getting-started screen, 114 ms |
| 0:03 | `attune workflow list` | Clean, 22 workflows, 0.6 s |
| 0:04 | `attune auth status` | Claims "Subscription Tier: PRO / Setup Completed: ✅ Yes" on a never-configured machine; silently wrote `~/.attune/auth_strategy.json` (F3) |
| 0:05 | `attune validate` | "❌ Validation failed: No API keys found" — contradicts auth status; fix points at `python -m attune.models.auth_cli setup` (F2, F3) |
| 0:06 | `attune workflow run code-review` | Spend gate fires first: "≈ up to $10.00" — before checking there's no key to spend with (F4) |
| 0:07 | Same, gate authorized, still keyless | **The wall (F1):** raw 25-line traceback, `Exception: Claude Code returned an error result: success`, then a "🚀 Running workflow" banner *after* the error, then "This one didn't go as planned" with $0.0000. Cause never stated, no next step |
| 0:08 | `python -m attune.models.auth_cli setup` | Interactive wizard starts (needs TTY). Note `attune setup` exists but does something else entirely — installs slash commands (F2) |

**Time-to-first-successful-workflow (CLI path, no key, no Claude
Code auth): not reached.** The keyless requirement is by design
(README says so) — the friction is that nothing on the failure path
says so.

---

## Ranked frictions

### F1 — The first-workflow failure is a traceback, not a message *(fix first)*

A keyless user's first workflow attempt ends in an unhandled
traceback whose message is self-contradictory ("error result:
success"), followed by a success banner, followed by a failure
banner. The actual cause — no API key and no authenticated Claude
Code — is never stated; no remediation is offered. This is almost
certainly what conversation 1's user hit. (Known class: the
`sdk-error-message-fidelity` spec — this is the highest-traffic
instance of it.) **Fix shape:** pre-flight auth before dispatching
the SDK; one sentence — "No API key found and Claude Code isn't
authenticated. Run `attune auth setup`, or set
`ANTHROPIC_API_KEY`." Suppress the traceback outside `--debug`.

### F2 — Three competing "setup" surfaces

`attune setup` installs slash commands; `attune auth` manages
auth; the error text recommends `python -m attune.models.auth_cli
setup`. A stuck user cannot tell which fixes "No API keys found."
**Fix shape:** one canonical `attune auth setup` (alias the
`python -m` path to it); make every error message point at that one
string; rename or fold `attune setup`.

### F3 — Fresh install misreports its own state

`auth status` says "PRO / Setup Completed: Yes" before any setup;
`validate` simultaneously fails. Contradictory diagnostics on
minute one teach the user the tool's self-reports can't be
trusted. **Fix shape:** defaults must render as defaults ("not
configured — using defaults"), not as completed setup.

### F4 — Spend gate fires before the no-key check

A user with no key is warned about "$10.00" of spend they cannot
incur, and the remediation offered is to *authorize spending* —
wrong order, alarming number. **Fix shape:** check key presence
before the spend gate; scale the estimate to the workflow.

### F5 — README pip path has no first command

"Get Started in 60 Seconds" ends at `pip install`. The bare
`attune` screen is genuinely good — but users must guess to type
it. **Fix shape:** one line in the README: "Then run `attune` to
see your next steps." Cheapest fix in this log.

---

## What worked (keep)

Install itself is clean and fast; no compile/dependency errors on
3.10. The bare `attune` screen is the best onboarding surface in
the product. `workflow list` is instant and legible. The spend gate
existing at all is right (F4 is ordering, not existence).

---

## Next (maps to weekend plan)

Block 2/4 fix order: F1 → F2 → F3 (F5 is a one-liner to slip in;
F4 rides along with F1's pre-flight). Re-run this exact sequence in
a clean container after each fix; append the new wall, if any,
below.

---

## Post-fix verification — 2026-07-11 (branch `fix/setup-friction`, commit 6a628f2)

Same sequence, fresh HOME + empty `ANTHROPIC_API_KEY`, worktree code
via the documented `PYTHONPATH` pattern:

| Step | Before | After |
|------|--------|-------|
| `auth status` (fresh) | "PRO / Setup Completed: ✅ Yes" | "PRO (default) / Not configured — using zero-config defaults (run 'attune auth setup')" |
| `validate` (fresh, no auth) | ❌ + `python -m attune.models.auth_cli setup` | ❌ "No auth found. Log in to Claude Code … or set ANTHROPIC_API_KEY / Run: attune auth setup" |
| `validate` (keyless, `~/.claude` present) | ❌ failed | ✅ valid, warning: subscription auth in use, API fallback unavailable |
| `workflow run` (no auth at all) | 💸 $10 spend warning first | 🔑 one-paragraph no-auth message; spend gate never reached; exit 3 |
| `workflow run` (CLI present, logged out) | 25-line traceback, "error result: success", dead-end "see raw stderr below" | one-line log ("re-run with --verbose for the full traceback") + "failed without producing any error output… most likely fixes" naming `claude` login / API key / `attune auth setup` |
| README pip path | ends at `pip install` | `attune` next-step line + validate + first-workflow command |

**New wall:** none of the friction class remains for a keyless user —
the sequence now ends at an explicit instruction to acquire auth,
which is inherent, not friction. Remaining known rough edge (minor,
untouched): the 🚀 banner and result blocks interleave oddly when
stdout is piped.

Tests: 357 unit tests green CI-faithfully (empty key, bare HOME);
spend-gate/dispatch fixtures updated to carry auth evidence so they
still target the gate on keyless runners; 2 `validate` tests updated
to the new keyless contract; +13 new tests
(`test_workflow_auth_preflight.py`,
`test_sdk_error_no_signal_stderr.py`). Pre-existing
`test_token_estimator.py::TestGetEncodingPaths` failures reproduce on
unmodified main (environmental; tiktoken download).
