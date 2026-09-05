# Native Codex timing: observability blocker

The native ABBA comparison did not run. No native timing numbers were obtained.
The alternative acceptance criterion was met: direct probes identify the missing
runtime provenance and native visibility observations. No renderer was changed,
and the browser harness was not used during this investigation.

## Evidence

1. `cua.getApp('Codex')` refused access to `com.openai.codex` for safety reasons.
   This blocks native accessibility/screenshot observation through the supported
   Computer Use interface. No alternate capture mechanism was attempted.
2. The actual `mcp__attune_ai__command_workspace_open` call succeeded with a
   synthetic roundtable preview. It returned text containing HTML, Markdown and
   MCP Apps metadata for `ui://attune-forms/dynamic-surface/v1`. Its HTML lacked
   `instance_id`. No execution action was submitted or provider called.
3. The merged source's CommandWorkspaceHost renderer supplies a new
   `telemetry_instance_id` when Forms workspace telemetry is available. The active
   response therefore fails the expected correlation-marker check. This does not
   identify which installed dependency or source revision caused the mismatch.
4. The actual standalone Forms render call succeeded and returned HTML containing
   `instance_id`. Configuration pins its launcher to 0.12.3, but neither this
   behavior nor configuration proves the exact package already loaded in memory.
5. AI plugin 16.2.1's `.mcp.json` launches unpinned `uvx --from attune-ai python
   -m attune.mcp.server`; the previous browser measurement explicitly loaded this
   checkout's merged source. These are different launch paths. The discovered
   tool surface has no process-local build/version diagnostic for this purpose.
6. No native widget paint/acknowledgment observation tool or `show_widget` tool
   was found in the available tool catalog. A text result carrying MCP Apps
   metadata does not establish whether the native client displayed it. Native
   That probe alone did not establish native rendering support. The subsequent
   validated interaction below establishes a standalone Forms interaction.

### Subsequent validated interaction

Patrick returned the native interaction's validated server result:
`elicitation_collect_response`, success `true`, response
`{"candidate":"decline"}`, receipt `resp-20260905-001239-c2185558`.
This corresponds to the standalone synthetic Forms preflight. It supplies
behavioral evidence that the widget interaction reached the Forms collector.
It supersedes the earlier uncertainty about a working standalone Forms native
interaction, but does not resolve native paint observation or workspace timing.

The result contains no request, paint, submission or visible-ack timestamps,
workspace revision, or instance ID. Its receipt identifier is not used as a
timing clock. Structural form validation is not the command workspace's canonical
successor-storage acceptance. This is not one of the seven-candidate ABBA runs;
no additional collection or workspace action is needed for this preflight.

Sanitized probe results are in `native-host-preflight.json`. Active action nonce
and full HTML are deliberately not copied into the report.

## Minimum instrumentation to unblock the measurement

- **Runtime provenance:** a diagnostic from the actual serving MCP process with
  its server/session ID, loaded AI build or source hash, Forms version and module
  path. Require the merged integration plus Forms 0.12.3 and a nonempty workspace
  instance token before starting the timing run. A fresh shell import is not
  sufficient. A runtime mismatch must be resolved and re-probed first.
- **Native host trace:** host-supported events for request dispatch, form actually
  visible, submission dispatch and acknowledgment actually visible. Include run,
  condition, workspace ID, consumed revision and instance ID on every event.
  An iframe script's render completion alone is not proof that the containing
  native surface was mounted and visible; retain host visibility evidence.
- **Canonical event export:** expose the existing `workspace_accepted` event
  emitted after canonical successor storage, correlated to the same request and
  instance. The Forms structural collector alone is not canonical acceptance.
- **Clock alignment:** host events use one monotonic clock. Map the server event
  to it with a measured offset/uncertainty, or a shared trace clock. Do not equate
  tool return time with acceptance or visible acknowledgment.

Derived intervals: visible minus request; canonical acceptance minus submission;
visible acknowledgment minus canonical acceptance. Human dwell is submission
minus form visibility and is reported separately. Retain raw traces, clock
uncertainty and invalid/missing joins. Then run the original seven-candidate,
all-decline scenario in ABBA order, requiring 7/3/3/7 accepted submissions and
identical terminal outcomes.

This requires an approved native-host observation/export interface; a renderer
optimization or a replacement browser benchmark cannot close this gap. If the
host already has a diagnostic trace, exporting it with these fields is enough;
otherwise these are the minimum added hooks, not authorization to implement them.

## Comparison with existing receipts

The browser baseline recorded warm first visibility of 68 ms versus 87–90 ms
batched; median submit-to-canonical acceptance was 6–8 ms for both. These are
reference values only. Native request-to-visible, submit-to-canonical and
canonical-to-visible-ack remain unknown, so no native bottleneck or renderer
optimization recommendation follows from the existing measurements.
