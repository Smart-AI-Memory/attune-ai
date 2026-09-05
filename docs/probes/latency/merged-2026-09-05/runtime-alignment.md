# AI MCP runtime alignment — activation pending

The launcher is aligned to the merged integration. The existing Codex task's
MCP connection still serves the prior package and needs a host reload.

## Diagnosis

Process inspection identified PID 83143 as the published AI MCP process with
cwd matching this task's 30be worktree. Its loaded extension paths locate uv
environment `AVivr15hIuiJpgkHLR946`. A separate interpreter probe of that
environment reports AI 16.2.1, Forms 0.12.3 and no `log_workspace_stage` in the
workspace module. This is environment evidence, not memory inspection. The live
host call independently returned HTML without `instance_id`.

The integration merge also declares AI 16.2.1: the version label cannot distinguish
the published package from merged source. Updating Forms alone cannot add the
missing AI workspace instrumentation.

## Changes and receipts

- Exported exact merge `c2138be2d6be10dfd252495dfae05cc861776375` with `git archive`.
  Built a wheel using existing build dependencies, without dependency resolution.
- Verified all 728 packaged AI Python files against merge source, then against
  the installed isolated runtime. Wheel SHA-256:
  `dfdc711000ba9b3ef761a0b3c752319c1d79e6bc75e6180f3bf545140446b6a6`.
- Retained the wheel at
  `~/.attune/runtimes/c2138be2d6be10dfd252495dfae05cc861776375/attune_ai-16.2.1-py3-none-any.whl`.
  The same directory contains a private backup of the previous Codex config.
- Used `codex mcp add attune-ai` to override the plugin's unpinned launcher with
  `uvx --from <absolute-wheel-path> --with attune-forms==0.12.3 python -m attune.mcp.server`.
  `ATTUNE_REDIS_REQUIRED=false` is retained; credentials were not written into the
  configuration. `codex mcp get attune-ai` confirms the effective pinned command.
- Fresh interpreter probe: AI 16.2.1, Forms 0.12.3, workspace telemetry available.
- Fresh public MCP stdio probe through that exact launcher: render has instance
  token; synthetic start transition advances revision 0 to 1; one canonical
  acceptance matches the rendered workspace/revision/instance exactly. No provider
  calls. Raw result: `runtime-alignment.json`.
- A subsequent call through this task's existing `mcp__attune_ai` connection
  still lacked the token. Configuration is updated; active connection is not.

## Activation boundary

The installed CLI's generated protocol includes `config/mcpServer/reload`, but
the running desktop app-server has no named control socket in its inspected Unix
sockets. `codex app-server daemon version` also reports the standard control
socket absent. The tool catalog exposes no MCP reload operation. No process was
killed, no new app-server started, and no native UI restriction was bypassed.

Next: reload/restart the Codex host, return to this task, and call the active AI
workspace tool again. Require a nonempty instance token and an exact canonical
acceptance join before marking active alignment complete. Preserve these
uncommitted receipts when resuming. Do not infer activation from the config or
fresh-process probe alone.

This local override intentionally stays pinned to the merge. Once a verified
published build contains the integration, replace the override with that build
and re-run the same live receipt. Removing only this override restores the
installed plugin's original launcher; the plugin cache was not edited.
