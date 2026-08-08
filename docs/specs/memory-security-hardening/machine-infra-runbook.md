# memory-security-hardening — machine-infra runbook (R2#6, R3#5/#6, R3#2)

Operator steps for the **machine-gated** remainder (D6). These touch the live
Redis and the out-of-repo hydrator (`~/.attune/memory/`), so they are NOT
applied by the in-repo work — run them deliberately, in order, with the backup
in hand. Everything in-repo (R1/R2/R3#1/R5) already shipped on PR #1979.

## Backups (already taken)

`~/.attune/backups/memory-security-<timestamp>/` holds copies of
`hydrate.py`, `session_hydrate.py`, `functions.lua`. Rollback = copy these back.
Re-take before editing if the live files have changed since.

## Live state observed (2026-08-07)

- Redis = `redis-stack-server` on `*:6379`, **`requirepass` empty**,
  **`bind * -::*`** (all interfaces). Unauthenticated + externally reachable.
- Active config file: `/opt/homebrew/etc/redis-stack.conf` (`port 6379` +
  `daemonize yes`); modules loaded via the caskroom service conf.
- `hydrate.py:254` and `session_hydrate.py:89` both connect with a bare
  `redis.Redis(decode_responses=True)` — **no password**.
- The hydrator venv (`~/.attune/memory/.venv`) has **no `attune`** → the R2#6
  scan must be self-contained (stdlib only), not an import.

## ORDERING (critical)

1. **Merge + release PR #1979 first**, and update the installed `attune-ai`
   (the MCP server's readers gain `connect_recall_redis`, which reads
   `REDIS_PASSWORD`). Turning on `requirepass` before the installed readers are
   auth-aware will break recall/ops.
2. Then R2#6 (hydrator scan) — independent, safe to do any time.
3. Then R3#5 (requirepass + bind) — the disruptive step; do it when you can set
   the env everywhere and restart.
4. Then R3#6 + R3#2 (epoch-stamp writer + reader) — co-designed follow-on.

---

## R2#6 — self-contained secret scan in `hydrate.py`  ✅ APPLIED 2026-08-07

**Applied live** to `~/.attune/memory/hydrate.py` (scan + guards on all 4 hset
writes) and the auth-prep to both hooks (below). Verified: a planted `sk-ant-`
key is skipped and absent from Redis; a real corpus false positive — AWS's
documented `AKIAIOSFODNN7EXAMPLE` in a rules doc — surfaced and drove the
placeholder filter below (so legit files that *mention* an example key aren't
dropped). Originals are in the backup dir for rollback.

The hydrator copies each corpus record's `text`/`name`/`description` into Redis.
Skip (fail closed) any record carrying a secret, and warn to ROTATE. Stdlib-only.

**Add near the top (after the imports / `MAX_TEXT`):**

```python
import re as _re

# memory-security-hardening R2: the hydration path is a write path. A secret in
# a file-of-record (predating the write-time gates, or hand-added) must not be
# copied into Redis. Fail closed: skip the record + warn to ROTATE. Stdlib-only
# — the hydrator venv has no attune; mirrors SecretsDetector's core patterns.
_SECRET_RES = tuple(_re.compile(p) for p in (
    r"sk-ant-[A-Za-z0-9_-]{90,}",                 # Anthropic
    r"sk-(?:proj-)?[A-Za-z0-9]{20,}",             # OpenAI
    r"AKIA[0-9A-Z]{16}",                          # AWS access key id
    r"gh[pousr]_[A-Za-z0-9]{36,}",                # GitHub token
    r"xox[baprs]-[A-Za-z0-9-]{10,}",              # Slack
    r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----",
))


# Documentation placeholders that structurally match but are not real (AWS's
# AKIAIOSFODNN7EXAMPLE appears in docs ABOUT secret detection). Real creds never
# contain these words. Without this, legit files get dropped from recall.
_SECRET_PLACEHOLDER = _re.compile(r"EXAMPLE|XXXX|REDACTED|PLACEHOLDER|YOUR[-_]", _re.I)


def _has_secret(*fields: str) -> bool:
    for f in fields:
        if not f:
            continue
        for rx in _SECRET_RES:
            for m in rx.finditer(f):
                if not _SECRET_PLACEHOLDER.search(m.group(0)):
                    return True
    return False
```

(Uses the already-imported `re` — `import os` is also needed for the auth-prep
below, and both `import os` lines get stripped by the format-on-save hook if
added before their first use; add import + usage together, or re-add after.)

**Guard each `pipe.hset(...)` write** (files ~line 303, lessons ~324, rules
~344) — wrap the body/text you are about to store:

```python
            if _has_secret(name, desc, body):
                print(f"[hydrate] SKIPPED {md} — secret detected; ROTATE, do not just delete")
                continue
            pipe.hset(f"{PREFIX}:file:{corpus}:{md.stem}", mapping={...})  # unchanged
```

(Do the same for the lesson `chunk` and rule `body` writes, and for the curated
`nodes` loop if a node's `name`/`description` come from an untrusted source.)

**Verify:** plant `sk-ant-` + 95 chars in a throwaway `~/.attune/memory/…/tmp.md`,
run the hydrator, confirm a `SKIPPED … ROTATE` line and that the key is absent
(`redis-cli HGETALL attune:memory:file:…:tmp`). Delete the throwaway.

---

## R3#5 — requirepass + loopback bind  ← SOLE REMAINING STEP (gated on PR #1979 release)

**a. Hooks are already auth-aware** ✅ — `hydrate.py` and `session_hydrate.py`
now connect with `password=os.environ.get("REDIS_PASSWORD") or None` (applied
2026-08-07). No-op until the secret is set. The `FUNCTION LOAD` / `FCALL` run on
the same authed client, so no extra change.

**Do NOT flip requirepass until PR #1979 is released and installed** — the
installed MCP server's readers (attune-ai 11.1.0) don't yet read `REDIS_PASSWORD`
and would break. After upgrade:

**b. Provision the secret** where every process inherits it — your shell profile
(`~/.zshrc`) and wherever the plugin MCP server is launched:

```bash
export REDIS_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

Record it in your password manager. Every connector reads `REDIS_PASSWORD`:
the in-repo readers (via `connect_recall_redis`, post-release), the two hooks
(step a), and the MCP server (inherits the env).

**c. Flip Redis** (immediate; do it right after a/b, then restart Claude Code so
all processes pick up the env):

```bash
redis-cli -p 6379 CONFIG SET requirepass "$REDIS_PASSWORD"
redis-cli -p 6379 -a "$REDIS_PASSWORD" CONFIG SET bind "127.0.0.1 -::1"
redis-cli -p 6379 -a "$REDIS_PASSWORD" CONFIG REWRITE
```

(Or add `requirepass …` + `bind 127.0.0.1 -::1` to
`/opt/homebrew/etc/redis-stack.conf` and restart the server.)

**Verify:** `redis-cli -p 6379 PING` → `NOAUTH`; `redis-cli -p 6379 -a "$REDIS_PASSWORD" PING`
→ `PONG`. Start a fresh Claude Code session; the hydrate line should still report
active nodes and `/recall` should work.

**Rollback:** `redis-cli -p 6379 -a "$REDIS_PASSWORD" CONFIG SET requirepass ""`,
`unset REDIS_PASSWORD`, restore the two hooks from the backup dir.

---

## R3#6 + R3#2 — hydration epoch-stamp (writer) + read-side epoch trust (reader)

Deferred and **co-designed** — the writer and reader must agree on one stamp
format, and enforcement can't turn on until the writer stamps (else recall
rejects every current record). Proposed shape:

- **Writer (`hydrate.py`):** each hydration computes an epoch token (e.g. a
  monotonic counter or the hydration start timestamp passed in) and writes
  `attune:memory:epoch` = token; every record hash gains `epoch`, `schema=1`,
  `src` (canonical path), `digest` (sha256 of body).
- **Reader (in-repo `attune.memory`):** a validator that, when
  `ATTUNE_MEMORY_ENFORCE_EPOCH=1`, filters recall to records whose `epoch`
  == current `attune:memory:epoch` and whose `digest` matches — a raw key
  injected into the prefix (no/So stale epoch) is ignored. Default off, so it
  ships dark and is flipped on only after the writer stamps.

Land these together in a follow-up PR; add reader tests with a stubbed Redis
(valid vs stale-epoch vs missing-digest records).
```
