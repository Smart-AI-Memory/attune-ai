---
type: error
name: fix-error
feature: fix
depth: error
generated_at: 2026-08-02T16:17:23.326205+00:00
source_hash: 02c4fd57871efde0e308241968a30e45d0a63f6ba866385c62a363e28a5f4b4b
status: generated
---

# Fix Receipts — state the goal and its probes, get a verified receipt

## Failure modes

**"no verification probes given — cannot verify a fix"** — a fix with
no probe cannot be verified, so the command abstains (exit 3) instead
of running something it could not check. Add `--probe`.

**"no --workflow given — Fix never guesses a route"** — a false
confident route is worse than an abstention, so the message names the
runnable next step. Pass `--workflow fix`.

**"probe contains shell metacharacters"** — probes are argv lists.
Rewrite the probe without pipes or redirection; if you need shell
semantics, put them in a script and probe the script.

**"cannot run: --run requires --scope"** — an unscoped fix has no edit
boundary to enforce, so `--run` refuses.

**"SCOPE NOT VERIFIED — no git available"** — attribution fell back to
content hashes of the declared scope files, so edits elsewhere are
undetectable. The run will not report success; review the tree by hand.

**Probe reported `SKIPPED`** — the command could not be executed (most
often a missing binary). This is uncertainty, not a pass; the exit code
is non-zero.
