# claude-agent-sdk 0.2.x Migration — Tasks

**Status:** complete (2026-06-16) — migration shipped (#917, 8.7.0).
Reconciled from stale "approved (for review)" and archived 2026-06-24.

Tasks are ordered. T0 is a measurement that scopes T1 and T2 —
its findings may shrink, grow, or re-prioritize them. Execute on a
fresh branch off `origin/main` (this is unrelated to the website
work), ideally in its own worktree.

---

```xml
<task id="0" name="phase0-empirical-breakage-scan">
  <objective>
    Measure what actually breaks under claude-agent-sdk 0.2.101
    before writing fixes. Produces the authoritative defect list.
  </objective>
  <context>
    <existing-code path="pyproject.toml">
      Pin is claude-agent-sdk>=0.1.60,<0.2.82; lock at 0.1.63.
    </existing-code>
    <note>
      Bump is empirical only — do not hand-fix yet. Run keyless
      (ANTHROPIC_API_KEY="") for the unit suite; run integration-auth
      with ATTUNE_MAX_BUDGET_USD set (budget-capped).
    </note>
  </context>
  <files-to-modify>
    <file path="pyproject.toml">Temporarily set pin to ==0.2.101</file>
    <file path="uv.lock">Regenerate via `uv lock`</file>
  </files-to-modify>
  <validation>
    <check>uv lock resolves claude-agent-sdk to 0.2.101</check>
    <check>Run full unit suite; capture every failure + traceback</check>
    <check>Run integration-auth (budget-capped); capture failures</check>
    <check>Record findings in decisions.md as the T1/T2 scope</check>
  </validation>
  <risks>
    <risk severity="medium">
      Failures may be the systemic CI runner-hang, not real — run
      locally first to distinguish real defects from infra.
    </risk>
  </risks>
</task>
```

```xml
<task id="1" name="system-prompt-default-audit">
  <objective>
    Ensure no workflow silently loses behavior from the 0.2.x
    system-prompt default change. Add explicit system_prompt where
    attune relied on the implicit Claude Code preset.
  </objective>
  <context>
    <existing-code path="src/attune/workflows/agent_sdk_adapter.py">
      The single SDK seam; 18 ClaudeAgentOptions construction sites
      live across src/attune/workflows/.
    </existing-code>
  </context>
  <files-to-modify>
    <file path="(per Phase 0 findings)">
      Add explicit system_prompt preset/string to the
      ClaudeAgentOptions sites that relied on the default.
    </file>
  </files-to-modify>
  <validation>
    <check>Workflows that depended on the Claude Code system prompt
      still produce equivalent output (spot-check 2-3 workflows)</check>
    <check>No ClaudeAgentOptions site silently uses the new default
      where the old default was load-bearing</check>
  </validation>
</task>
```

```xml
<task id="2" name="mcp-background-connection-handling">
  <objective>
    Verify attune's MCP-tool workflows (and attune's own MCP server)
    tolerate the 0.2.x background-connection default, or force
    blocking where readiness is required.
  </objective>
  <context>
    <note>
      0.2.x starts sessions before MCP servers report connected.
      Controls: MCP_CONNECTION_NONBLOCKING env, per-server
      alwaysLoad. Decide blocking-vs-nonblocking per workflow.
    </note>
  </context>
  <validation>
    <check>An MCP-tool-using workflow run completes with tools
      available (no "tool not found" from a pending server)</check>
    <check>If a shim/env is set, a regression test asserts it</check>
  </validation>
  <risks>
    <risk severity="medium">
      Silent: a pending MCP server yields "tool unavailable" rather
      than an error — assert tool availability explicitly.
    </risk>
  </risks>
</task>
```

```xml
<task id="3" name="finalize-pin-and-lock">
  <objective>
    Land the deliberate pin per decision d1 and document it.
  </objective>
  <files-to-modify>
    <file path="pyproject.toml">
      Pin claude-agent-sdk>=0.2.101,<0.3.0; rewrite the inline
      comment to document the deliberate 0.2.x adoption and the new
      <0.3 guard. Also check the [dev] mirror of this dep.
    </file>
    <file path="uv.lock">Regenerate so the hash matches pyproject</file>
  </files-to-modify>
  <validation>
    <check>pre-commit (check-docs-freshness) passes — lock not stale</check>
    <check>grep confirms no remaining <0.2.82 references</check>
  </validation>
</task>
```

```xml
<task id="4" name="verify-green-against-0-2-x">
  <objective>
    Prove the suite is green against the locked 0.2.101, including
    the budget-capped auth integration path.
  </objective>
  <validation>
    <check>Full unit suite green (keyless)</check>
    <check>integration-auth green (ATTUNE_MAX_BUDGET_USD capped)</check>
    <check>Any behavioral shim from T1/T2 has a regression guard</check>
  </validation>
</task>
```

```xml
<task id="5" name="release-notes-and-pr">
  <objective>
    Document the migration and open the PR.
  </objective>
  <files-to-modify>
    <file path="CHANGELOG.md">Entry: adopt claude-agent-sdk 0.2.x</file>
  </files-to-modify>
  <validation>
    <check>PR opened; required CI green (read required lanes, not
      the systemic-hang OS lanes)</check>
  </validation>
</task>
```
