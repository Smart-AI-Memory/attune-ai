# Cross-Provider Session Handoff — Tasks

**Status:** complete (2026-07-28; flipped at 2026-08-08 triage) —
T1+T2 merged #1605, T3 merged #1694, T4 merged #1700; R6 live
cross-provider receipt CLOSED PASS 2026-07-28 (Antigravity leg,
receipts.md). The post-07-27 staging note is discharged.

Execution note: T1 and T2 have NO code dependency on the held
transport stack (pure new module + MCP wiring) — they may be built
early as held drafts if a build slot opens. T3 imports the
session-stash helpers and MUST wait for the 07-27 lift. T4's live
receipt additionally waits for distribution (marketplace re-sync /
PyPI publish). Before executing any task, re-grep the named scope
against the current tree (spec text goes stale; code is the
contract).

## T1 — core module (packet + verify)

```xml
<task id="handoff-t1" name="core-module">
  <objective>
    Build src/attune/handoff/ — packet assembly from real git
    state, packet rendering/parsing (D1 frontmatter + template
    body), and the D3 drift matrix. No MCP wiring yet.
  </objective>
  <context>
    <existing-code path="templates/agent-handoff.md">
      Contract packet template — body sections must match it.
    </existing-code>
    <design>D1 frontmatter fields; D2 read-only subprocess git,
    validated paths; D3 warning codes; D4 caps 8KB/2KB
    reject-with-reason, overwrite-in-place + superseded_at.</design>
  </context>
  <files-to-create>
    <file path="src/attune/handoff/__init__.py">public API:
      handoff_create(), handoff_resume() (pure functions returning
      dicts; no MCP imports)</file>
    <file path="src/attune/handoff/packet.py">assemble/render/parse;
      caps enforcement</file>
    <file path="src/attune/handoff/verify.py">git reads + drift
      matrix</file>
    <file path="tests/unit/handoff/test_packet.py">fixture-repo
      assembly; git-derived fields provably from git; cap
      rejections; overwrite-in-place</file>
    <file path="tests/unit/handoff/test_verify.py">one case per D3
      code + clean path</file>
  </files-to-create>
  <validation>
    <check>suite receipt: tests/unit/handoff run SERIALLY, exact
      tail reported</check>
    <check>no mutating git command anywhere in the module (grep
      receipt: no commit/checkout/push/add tokens)</check>
    <check>_validate_file_path() on every file operation; security
      tests for the packet write path</check>
  </validation>
  <risks>
    <risk severity="medium">Windows path/encoding in git subprocess
      output — wait Windows lanes at merge.</risk>
  </risks>
</task>
```

## T2 — MCP surface

```xml
<task id="handoff-t2" name="mcp-surface">
  <objective>
    Register handoff_create / handoff_resume on the attune MCP
    server per the plugin-reference checklist.
  </objective>
  <context>
    <checklist>schema in src/attune/mcp/tool_schemas.py; handler;
    dispatch entry in _build_dispatch_table(); tool-count test
    update; skill references validated.</checklist>
  </context>
  <files-to-modify>
    <file path="src/attune/mcp/tool_schemas.py">two tool schemas
      (create: caller prose fields + optional slug; resume: slug
      optional, defaults to current branch)</file>
    <file path="tests/unit/test_mcp_memory_tools.py">tool-count
      update</file>
  </files-to-modify>
  <validation>
    <check>integration receipt: real-dispatch test class extended
      (transport receipt-2 pattern) — call_tool through the real
      server for both tools</check>
    <check>tests/unit/plugins/test_plugin_reference_validation.py
      green</check>
  </validation>
  <risks>
    <risk severity="low">Exact-dict-equality response-shape tests in
      OTHER files — run the full mcp handler test dir, not just the
      new file.</risk>
  </risks>
</task>
```

## T3 — memory linkage + telemetry (post-lift only)

```xml
<task id="handoff-t3" name="memory-telemetry">
  <objective>
    D5: capture/recall topic-handoff pointers via the session-stash
    helpers with degrade-silent reporting. D6: one structlog event
    per tool (slug, warning codes, duration, memory outcome).
  </objective>
  <context>
    <depends>session_memory_* helpers on main (07-27 lift).</depends>
  </context>
  <validation>
    <check>suite receipt: unreachable-backend path asserts
      memory:skipped WITH reason, and ok stays true</check>
    <check>live local canary (Claude side): create → resume round
      trip with a real backend; pointer recalled; canary
      forgotten — logged in receipts.md</check>
  </validation>
  <risks>
    <risk severity="medium">Helper import paths may shift in the
      lift squashes — re-grep before wiring.</risk>
  </risks>
</task>
```

## T4 — docs, ledger, live cross-provider receipt

```xml
<task id="handoff-t4" name="docs-and-receipts">
  <objective>
    User-facing docs (feature page per the single-source playbook),
    receipts.md ledger for this spec, and the R6 live receipt:
    packet created in Claude Code, resumed in a live Codex session
    post-distribution.
  </objective>
  <validation>
    <check>evidence-chain: receipts.md rows dated; UNPROBED rows
      stay honest until the named client runs</check>
    <check>live-fire: Codex transcript appended (session id +
      verbatim tool results)</check>
  </validation>
  <risks>
    <risk severity="low">Distribution lag (proven 2026-07-22):
      marketplace re-sync / PyPI publish gates the live row —
      sequencing note, not a failure.</risk>
  </risks>
</task>
```
