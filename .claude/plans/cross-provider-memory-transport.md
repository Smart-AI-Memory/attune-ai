# Execution plan: cross-provider-memory-transport

Canonical spec: [tasks.md](../../docs/specs/cross-provider-memory-transport/tasks.md)
with companion requirements, design, and decisions in the same directory.
Status: APPROVED — implementation authorized 2026-07-22.

```xml
<plan>
  <feature>cross-provider-memory-transport</feature>
  <spec>docs/specs/cross-provider-memory-transport/tasks.md</spec>
  <task id="T1">
    <title>Truthful fallback and caller-scoped status</title>
    <dependencies>none</dependencies>
    <scope>file_stash write result, session_stash additive status, focused tests</scope>
    <acceptance>EPERM returns false with a visible reason; existing status keys remain.</acceptance>
  </task>
  <task id="T2">
    <title>Semantics gap and provider-neutral MCP handlers</title>
    <dependencies>T1</dependencies>
    <scope>Measure existing tools; add only missing session-memory adapters.</scope>
    <acceptance>D3 verdict recorded; real dispatch and AMS round-trip pass; old schemas frozen.</acceptance>
  </task>
  <task id="T3">
    <title>Recall skill capability routing</title>
    <dependencies>T2</dependencies>
    <scope>Plugin skill source, generated .agents mirror, projection guard.</scope>
    <acceptance>MCP clients avoid sandboxed Python; drift guard passes.</acceptance>
  </task>
  <task id="T4">
    <title>Hook regression, docs, and telemetry</title>
    <dependencies>T3</dependencies>
    <scope>Claude hooks, capability matrix, local-only failure signals.</scope>
    <acceptance>Claude hook canary passes; docs stay honest; telemetry remains local/default-off.</acceptance>
  </task>
  <task id="T5">
    <title>Live provider verification matrix</title>
    <dependencies>T4</dependencies>
    <scope>Codex, Claude Code, and Antigravity/Gemini receipts.</scope>
    <acceptance>Real receipts or honest unsupported status; every canary deleted.</acceptance>
  </task>
</plan>
```
