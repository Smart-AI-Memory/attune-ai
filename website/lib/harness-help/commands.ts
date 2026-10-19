// Authored command map; complete procedures stay in their existing versioned sources.
export const COMMAND_REFERENCE = `## Typical use

These groups describe who usually initiates work. People and AI can use the CLI;
this grouping grants no permissions and imposes no exclusive operator roles.
AI still needs accepted scope and the applicable execution authorization. Human
judgment enters when selecting evidence, accepting scope, granting file/provider
access and resolving uncertain effects.

The index lists command names. It is not a script to run from top to bottom.
Read \`attune-harness COMMAND --help\` for required inputs before invoking a command.

### AI

\`\`\`text
attune-harness code-config
attune-harness github-checks
attune-harness index
attune-harness mcp-inspect
attune-harness mcp-serve
attune-harness memory
attune-harness retrieval-task
attune-harness retrieve
attune-harness spec
attune-harness triage-check
attune-harness verify
\`\`\`

### AI/Human

\`\`\`text
attune-harness init
attune-harness plan
attune-harness build
attune-harness review
attune-harness fix
attune-harness test
attune-harness status
attune-harness resume
attune-harness repair-economics
attune-harness roundtable
attune-harness source-review
\`\`\`

### Human

\`\`\`text
attune-harness extension
attune-harness cancel-task
attune-harness reconcile-task
attune-harness transfer-task
\`\`\`

## Read the command shapes

The first word after \`attune-harness\` selects a command. Some commands have
subcommands: \`index plan\` and \`index build\` are two different index actions.
\`plan --accept\` instead selects an action flag on \`plan\`; \`accept\` is not a
separate command or subcommand. Options such as \`--config\` supply values.

The reference below reuses the release-pinned CLI guide and existing Help topic structure. It maps command order; complete project fixtures remain in the linked canonical procedures. It shows selected forms, not every option. Uppercase names
such as \`TASK\`, \`CHECKPOINT\`, \`PROJECT\` and \`REQUEST.json\` stand for your actual
paths or returned values. Read the installed help before adapting a shape.
Sample prompts are requests you can give your agent, not CLI arguments.

### Primary action verbs

Typical initiator: **AI/Human**. Read each row's human decision before executing.
These are alternative starting points for different goals, not one universal chain.

| Command and action | Forms in 1.5.0 | Prerequisite and human judgment | Sample prompt | Expected result or evidence |
| --- | --- | --- | --- | --- |
| \`init\` — prepare starter files | \`--profile demo\`, \`claude\` or \`codex\`; \`--for fix\`, \`plan\` or \`roundtable\` are options, not subcommands | Choose the project, scope and participants. Inspect generated files. The default is a deterministic demo; a starter registry is not automatically build-capable. | \`Prepare a plan request for this file and its tests. Show me the generated scope before proceeding.\` | Starter configuration/request files; no task acceptance or model execution. |
| \`plan\` — define and accept work | Actions include \`--request\`, \`--answers\`, \`--decision\`, \`--revise\`, \`--run\`, \`--stage\`, \`--accept\`, \`--reimport\` | A new request needs \`--project\`, \`--config\` and \`--task-dir\`. A person reviews intent, effects and checks before accepting the exact current checkpoint. | \`Prepare a plan for this change. Show the scope and checks, and stop for my acceptance.\` | Saved draft/questions or proposal, checkpoint and next action; acceptance records a scope decision. |
| \`build\` — execute accepted work | \`build TASK\`; checkpoint and dispatch grants are options | First accept a build-ready plan with frozen effects and protected checks. Authorize the configured external/native execution separately. | \`Build the accepted task within its approved scope and report the protected check evidence.\` | Durable build journal, effects and verification evidence, or a stated pause/refusal. |
| \`review\` — assess a document against evidence | Task intake uses \`--goal\`, \`--task-response\`, \`--intake-only\`, \`--accept\`; \`--plan solo\` or \`independent-review\` selects a review plan | Select the document, corpus, context, criteria and assessor. Inspect intake before acceptance; provider/command work needs its grants. | \`Check this guide against these sources. Preserve unsupported and uncertain claims in the report.\` | Assessment receipt and claim/check evidence; a completed assessment may refute claims. This is documentary review, not a general code security audit. |
| \`fix\` — repair scoped files | Intake/acceptance options; \`--review none\`, \`requested\` or \`required\`; optional \`--from-assessment\` | Use a dedicated supported checkout, explicit scope, trusted frozen probe and selected worker/reviewer. Human approval covers the actual replacement and execution. | \`Repair this defect using the frozen probe. Keep the failure before the change and the result after it.\` | Replacement/probe receipts with failed-before and passed-after evidence, or a refusal/pause. |
| \`test\` — check a captured change | \`--project\` with \`--scope\`, or \`--from-task\`; then checkpoint-bound \`--accept\` | Select an interpreter containing pytest and a task directory outside the repository. Inspect proposed tests and exclusions before acceptance. | \`Preview tests for this change. Wait for approval, then run the captured inputs and retain output.\` | Test preview/checkpoint, then retained stdout/stderr and pytest evidence. Collection-only or all-skipped execution is not a pass. |
| \`status\` — inspect saved work | \`status TASK\`; \`--format json\`, \`markdown\` or \`html\`; optional \`--include-task\` | Supply the saved directory. A person assesses the outcome, checks and next action; successful inspection does not mean the task passed. | \`Show this task's current scope, outcome, evidence and next action without executing it.\` | Saved-state presentation. No work dispatch. |
| \`resume\` — continue eligible saved work | \`resume TASK\`; checkpoint, operation limit and dispatch grants are options | Inspect status first. Resolve stale scope or uncertain effects. Carry forward only the execution authority that still applies. | \`Inspect the saved task and continue only if its checkpoint and execution permissions remain valid.\` | Continued task evidence or a precise refusal. It does not repair every failed check or blindly repeat settled work. |

## Follow the order for your goal

Choose one relevant sequence. A review or a test does not require an unrelated
build, retrieval job or model consultation. The numbered steps below describe
required handoffs within each selected path. Optional work and alternatives are
labeled separately. They are command shapes, not ready-made project fixtures.

### Plan, accept, then build

See the existing [plan/build procedure](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.5.0/docs/cli-guide.md#plan-and-build) for its complete fixture and participant requirements. The [retained preparation walkthrough](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.5.0/docs/tutorials-1.5.0-candidate.md#specification-workflow-preview-and-acceptance) keeps its candidate-artifact boundary.

**Prerequisites:** a real request, trusted participant registry, supported project
checkout, frozen file effects and protected verification. Put task state outside
the checkout. Participants must support the intended build; the default demo
registry is not a production build configuration.

1. Create the preview with \`attune-harness plan --request REQUEST.json --project PROJECT --config REGISTRY.json --task-dir TASK\`. Keep the returned task path, questions and current checkpoint. Optional setup: \`init --for plan\` can prepare a starter request before this step; inspect its contents and participant choices.
2. Inspect the decision with \`attune-harness plan --task-dir TASK --decision\`. **Human judgment:** review the goal, exact file scope, effects, constraints and protected checks. If questions remain, use the returned bound answer format with \`--answers ANSWERS.json\`; inspect the refreshed decision and checkpoint before proceeding.
3. Accept only the reviewed revision with \`attune-harness plan --task-dir TASK --accept --checkpoint CHECKPOINT\`. Pass the current displayed checkpoint, not a digest from an earlier preview. The result records accepted scope; it grants no separate paid/external execution authority.
4. Run \`attune-harness build TASK --checkpoint CHECKPOINT\` with only the separately authorized dispatch flags. Pass the accepted task and current checkpoint from step 3. Required external participants need \`--allow-external\`; native participants also need \`--allow-native\`. Read any readiness refusal before continuing.
5. Run \`attune-harness status TASK\`. Inspect the resulting journal and check evidence. **Optional continuation:** use \`resume\` only when status identifies eligible paused work and the required authority remains current.

**Optional planning-participant branch, before step 3:** if a configured planner
must propose the work, run \`plan --task-dir TASK --run\` with its required explicit
grants, then inspect the completed proposal. Run
\`plan --task-dir TASK --stage --checkpoint CHECKPOINT\` to stage that proposal as
a new unaccepted draft. Carry the newly displayed checkpoint back to step 2.
\`--run\`, \`--stage\` and \`--accept\` are distinct actions; staging is not acceptance.

### Preview, approve, then test

The existing [test-this-change procedure](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.5.0/docs/cli-guide.md#test-this-change) provides the complete example and tested profile.

**Prerequisites:** supported Git working-tree changes, explicit scope, an
interpreter with pytest and an unused task directory outside the repository.

1. Run \`attune-harness test --project PROJECT --scope PATH --interpreter PYTHON --task-dir TASK\`. The result is a saved test preview and checkpoint, not completed tests.
2. **Human judgment:** inspect selected tests, broader fallbacks and excluded checks. Keep the preview's task directory and exact checkpoint. Change the proposed selection before accepting if it does not cover the goal.
3. Run \`attune-harness test --task-dir TASK --checkpoint CHECKPOINT --accept\`. This accepts the saved plan and executes its captured inputs. The output names saved records and test evidence.
4. Run \`attune-harness status TASK\` and inspect actual test execution and retained output. **Optional continuation:** if execution was interrupted, inspect the stated recovery action before using \`resume TASK\`.

**Alternative input:** after a completed repair, use \`test --from-task REPAIR_TASK\`
instead of project/scope in step 1. This derives the changed paths and binds repair
completion evidence. It still needs its own test preview acceptance; repair
approval does not approve that later test run.

### Review or repair through intake

These are separate paths: choose \`review\` for document evidence or \`fix\` for a
scoped repair. Neither requires running both commands in sequence. The existing
[CLI guide's review procedure](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.5.0/docs/cli-guide.md#task-oriented-evidence-review)
and [repair procedure](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.5.0/docs/cli-guide.md#scoped-repair)
provide the complete inputs and examples.

1. Prepare the selected command's goal and inputs with \`--intake-only\`. \`review\` needs its document, context, corpus and assessor; \`fix\` needs its checkout, scope, frozen probe and worker/reviewer choices. Retain the returned task directory and bound submission template.
2. **Human judgment:** inspect and complete that submission's answers, request identity and permitted effects. Only when approved, set its \`accepted\` field to \`true\` and retain its explicit \`permissions\`. Save the current bound submission as \`ANSWERS.json\`; do not create an unrelated approval object.
3. Submit with \`attune-harness review --task-dir TASK --task-response ANSWERS.json --intake-only\`, or use \`fix\` in the same command shape for a repair. The response carries its own acceptance and permissions; do not add \`--accept\`, \`--goal\`, \`--config\` or dispatch-grant overrides to this response submission. The result is accepted intake without execution.
4. Run \`attune-harness status TASK\` and inspect the accepted request and next action. Pass this same task identity and current checkpoint onward.
5. When status permits execution and the saved grants remain authorized, use \`attune-harness resume TASK\` with any required current checkpoint/grants. Review returns assessment evidence; repair returns effect/probe evidence. Inspect status again afterward.

**Alternative acceptance path:** a complete initial invocation can use \`--accept\`
instead of the bound-response path. Without \`--intake-only\`, accepted intake can
execute immediately. Choose that path only when all supplied inputs and effects
are already approved; it is not an extra acceptance step after response submission.

**Optional later handoff:** a completed structured assessment can supply selected
findings to \`fix --from-assessment\`; a completed repair can supply
\`test --from-task\`. Each new task has its own intake and approval.

### Inspect first, then choose a recovery branch

1. Run \`status TASK\`; retain its current checkpoint, last event and explicit next action. Establish whether effects are known before taking another action.
2. **Choose one applicable branch:** \`resume TASK\` for eligible continuation; \`reconcile-task\` for the specific unresolved event; \`transfer-task\` for a permitted accepted assessor; or \`cancel-task\` to stop work. These are alternatives, not four mandatory steps.
3. After an authorized reconciliation or transfer, inspect status again. Resume only if the new saved state permits it. Cancellation preserves evidence and does not prove that external effects were reversed.

**Human judgment:** recovery/retry can repeat external effects or usage. Choose a
specific supported reconciliation option from \`reconcile-task --help\`; never
run all retry options or treat cancellation as a rollback.

## AI tools and integrations reference

Typical initiator: **AI**. The person still selects roots, sources, participants
and allowed provider/file effects. Read-only helpers do not approve later work.

| Command and action | Actual subcommands or selected form | Prerequisite and human judgment | Sample prompt | Expected result or evidence |
| --- | --- | --- | --- | --- |
| \`code-config\` — prepare coding-retrieval configuration | \`--repo\`, \`--index-dir\`; optional \`--include-docs\`, \`--structured-path\` | Choose the repository, index destination and source inclusion. Configuration is not an executed index. | \`Prepare repository-first retrieval configuration and show which sources it includes.\` | Configuration/selection data for the chosen application index. |
| \`index\` — manage an application index | \`plan\`, \`build\`, \`update\`, \`inspect\` | Inspect the plan before provider work. Voyage build/update needs explicit upload/call authorization; update uses \`--base-generation\`, inspect uses \`--generation\`. | \`Preview this index, show the source/upload scope and wait for my decision before building it.\` | Index plan or generation/build evidence; inspection reports a selected generation. |
| \`retrieval-task\` — prepare coding-agent retrieval intake | \`--config\`, \`--generation\`, \`--objective\`; optional participant/call limit | Select an existing generation and objective. Review the emitted request before explicitly setting \`accepted=true\`. | \`Prepare a retrieval request for this question against that exact generation, then show it for approval.\` | Intake/request data; preparation does not grant a provider call. |
| \`retrieve\` — obtain source evidence | Choose \`--corpus\` or \`--request\`; supply a query | Local keyword retrieval and an explicitly accepted Voyage request are alternative paths. Voyage additionally needs \`--allow-provider\` and its setup. | \`Retrieve evidence for this claim using the explicitly selected source path and show source identities.\` | Retrieved evidence and source references, or a diagnostic. No automatic Voyage-outage fallback is provided. |
| \`verify\` — check supported document claims | \`verify DOCUMENT --context CONTEXT\` | Supply declared trusted context. Human judgment still assesses claims outside the supported check. | \`Verify the supported claims in this Markdown file against this context and identify limits.\` | Verification report/check evidence, not a guarantee of every statement. |
| \`github-checks\` — inspect exported check runs | \`github-checks INPUT --repository OWNER/REPO --revision SHA\` | Supply a complete GitHub REST check-run export bound to the intended repository/revision. | \`Inspect this exported check-run JSON for this commit without dispatching anything.\` | Bound check suggestions/diagnostics from local input; this command does not fetch GitHub or dispatch fixes. |
| \`triage-check\` — suggest a bounded response | \`triage-check INPUT\` | Supply a trusted check event and attempt history. A person decides any later repair authority. | \`Suggest a bounded response to this trusted failure event and retain the attempt limits.\` | A triage suggestion; no repair dispatch. |
| \`spec\` — prepare or present specification material | \`intake\`; \`present\` with selection \`tasks\`, \`task\`, \`result\` or \`progress\` | Select project/plan and any test evidence. Human judgment supplies intent and assesses the presentation. | \`Prepare Spec intake, then present the existing plan's tasks and available evidence.\` | Intake form/composed answers or a presentation of existing evidence; no implicit build. |
| \`mcp-serve\` — serve a selected local MCP profile | Retrieval options, or separate \`--workspace\` profile | Configure the host and accepted request/grants. Choose the profile deliberately; provider grants stay explicit. | \`Prepare the selected MCP integration and show its accepted sources and grants before serving it.\` | Local MCP stdio service/session receipts. Starting a service is not new task acceptance. |
| \`mcp-inspect\` — inspect MCP receipts | \`mcp-inspect SESSION_DIR\` | Use an existing local session directory. Assess the recorded outcome rather than inferring success from inspection alone. | \`Show this MCP session's retained call receipts without dispatching another call.\` | Local receipt inspection; no new dispatch. |
| \`memory\` — use scoped memory | See the nested catalog below; parent options include \`--config\`, \`--jobs\`, \`--native-config\` | Supply authorized memory roots. Reads, saved-store writes and native proposals have different effects/grants. | \`Recall evidence from these approved roots, preserve provenance and show any separate write or provider action before executing it.\` | Scoped packets, saved history, scratch data or proposal-job receipts for the selected action. |

### Build an index, then retrieve from its selected generation

This path is for explicitly selected Voyage coding retrieval. **Prerequisites:**
the Voyage integration, authorized source selection, provider configuration and
accepted source/upload/usage limits. Configuration and sources must still match
the reviewed plan; repeat planning and review if they change.

1. **Optional setup:** use \`attune-harness code-config --repo PROJECT --index-dir INDEX_DIR\` and save its emitted configuration as \`INDEX.json\`. Alternatively supply an existing reviewed index configuration. This prepares configuration; it does not build an index.
2. Run \`attune-harness index plan --config INDEX.json\`. Inspect its source manifest, proposed generation, estimated input and planned calls. **Human judgment:** authorize the selected source uploads and bounded provider work before building; the estimate is not a guaranteed bill or a new permission grant.
3. When that provider work is explicitly authorized, run \`attune-harness index build --config INDEX.json --allow-provider\`. Retain the returned published \`generation\` and build receipts; do not use a failed or incomplete generation for retrieval.
4. Run \`attune-harness index inspect --config INDEX.json --generation GENERATION\`, passing the generation from step 3. Inspect its manifest, publication/receipt evidence and any stale-source refusal.
5. Run \`attune-harness retrieval-task --config INDEX.json --generation GENERATION --objective OBJECTIVE\`. Pass the inspected generation. The output is a retrieval request template with its selected source scope and call limits.
6. **Human judgment:** review that exact request and its permissions. Only when approved, set its \`accepted\` field to \`true\` and save the approved request as \`REQUEST.json\`. Preparing the template does not approve it.
7. Run \`attune-harness retrieve QUERY --request REQUEST.json --allow-provider\` only with the applicable provider execution authorization. Pass the accepted request from step 6; inspect the returned source evidence and retained call receipts.

**Alternative local path:** \`attune-harness retrieve QUERY --corpus CORPUS\`
performs local keyword retrieval and does not require this Voyage index sequence.
Select the path deliberately; an outage does not automatically select the other.

**Optional update branch:** after source changes, review the new plan and use
\`index update --config INDEX.json --base-generation GENERATION --allow-provider\`
only with authorized provider work. Inspect the newly returned generation, then
prepare and approve a new retrieval request bound to it. Updating is not a
mandatory step between every build and query.

### Memory subcommands

Use parent options before the selected memory subcommand, for example
\`attune-harness memory --config MEMORY.json recall QUERY\`.

- Read/source operations: \`capabilities\`, \`recall\`, \`resolve\`, \`refresh\`, \`serve\`.
- Proposal/job operations: \`create\`, \`replay\`, \`inspect\`, \`execute\`. Creating a proposal is distinct from separately authorized native execution.
- \`saved\`: \`save\`, \`revise\`, \`forget\`, \`complete\`, \`show\`, \`list\`, \`search\`, \`reindex\`. This is a retained store, not the browser's form-answer state.
- \`scratch\`: \`capabilities\`, \`stash\`, \`retrieve\`, \`forget\`, \`keys\`. Writes/deletions need their applicable scope; scratch is distinct from retained saved memory.
- \`redis\`: \`status\`, \`digest\`, \`related\`, \`node\`, \`search\`. This optional integration needs its Redis setup.

These are alternatives by purpose. There is no required \`save\` → \`forget\` chain,
and reading memory does not authorize a write or a provider call. Inspect
\`memory --config MEMORY.json SUBCOMMAND --help\` for that action's actual inputs.

### Consultation and accounting

Typical initiator: **AI/Human**. Consultation may use configured model participants;
it requires the accepted contract and applicable dispatch authority.

| Command and action | Actual subcommands or form | Prerequisite and human judgment | Sample prompt | Expected result or evidence |
| --- | --- | --- | --- | --- |
| \`roundtable\` — consult selected participants about frozen sources | \`check\`, \`prepare\`, \`run\`, \`status\`, \`evidence\`, \`reconcile\`, \`assess-citation\`, \`abandon\` | Select sources/models, inspect the frozen contract, then accept its digest before dispatch. Consultation output still needs human assessment. | \`Prepare a bounded consultation over these files. Show the contract and stop before any participant call.\` | Contract/digest, then participant, citation and assessment evidence if authorized execution completes. |
| \`source-review\` — consult about selected sources | Same subcommands as \`roundtable\` | Follows the same frozen-source contract and grants; it is not a second required stage after roundtable. | \`Prepare a source review for these files and this question, with explicit participant identities and limits.\` | The source-consultation contract and retained results/limits. |
| \`repair-economics\` — account for repair attempts | \`repair-economics INPUT\` | Supply all attempts, costs and quality outcomes. Human judgment determines whether the evidence supports comparison. | \`Account for all repair attempts and their quality before comparing cost.\` | Accounting/quality-aware comparison, not automatic permission to choose a cheaper repair. |

### Check, prepare, approve, then consult

**Prerequisites:** explicit participant/model configuration, selected source paths
and a new run directory outside the project. Use either \`roundtable\` or
\`source-review\`; they expose the same sequence.

1. Run \`roundtable check --config CONFIG.json\` to inspect configuration/local seat readiness. It makes no model call.
2. Run \`roundtable prepare --project PROJECT --path PATH --config CONFIG.json --run-dir RUN\`. This freezes the selected source scope and returns the contract and its digest. It makes no provider call.
3. **Human judgment:** inspect the question, files, participants, limits and requested execution. Keep the accepted contract digest; configuration presence is not approval.
4. Run \`roundtable run RUN --accept DIGEST\` with only separately authorized \`--allow-external\` and, where needed, \`--allow-native\`. Pass the digest from the reviewed preparation. Execution can invoke configured models and consume usage.
5. Inspect \`roundtable status RUN\` and \`roundtable evidence RUN\`. **Alternative recovery:** use the stated \`reconcile\` or \`abandon\` action only when applicable. \`assess-citation\` is a separate evidence-assessment action, not a required execution stage.

## Human decisions and integration management

Typical initiator: **Human**, often with an agent preparing the inputs and
performing an explicitly authorized action. This does not reserve the CLI to a
person or allow an agent to invent approval.

| Command and action | Actual subcommands or form | Prerequisite and human judgment | Sample prompt | Expected result or evidence |
| --- | --- | --- | --- | --- |
| \`extension\` — manage a local bundle | \`discover\`, \`install\`, \`inspect\`, \`enable\`, \`disable\`, \`remove\`, \`replace\` | Inspect manifest/artifact, signature and effective grants where required. Installation creates a disabled registration; enabling is a separate checkpoint-bound decision. | \`Inspect this bundle and its grants, then wait for my decision before enabling it.\` | Manifest inspection or registration/state receipts; installation alone does not activate it. |
| \`reconcile-task\` — resolve one recorded uncertain event | Select one of \`--reply\`, \`--retry-read-only\`, \`--retry-native\`, \`--retry-refused\`, \`--observe-file\`, \`--retry-before\` as supported for that task | Inspect current checkpoint/event and independent effect observations. Human judgment accepts any specific retry risk; the options are alternatives. | \`Inspect this unresolved event and show the one supported reconciliation action and its risks. Do not retry yet.\` | Correlated reply/observation or a bounded retry authorization; no claim that unknown effects never occurred. |
| \`transfer-task\` — transfer an assessor | \`--assessor\`, \`--reason\`; checkpoint where required | Choose an already accepted identity and inspect the saved state. | \`Show the permitted assessor transfer for this checkpoint, including the reason and accepted identity.\` | Retained transfer decision or refusal; no new participant grant. |
| \`cancel-task\` — stop saved work | \`--reason\`; checkpoint where required | Inspect stopped work and preserve uncertain effects. Human judgment distinguishes stopping from undoing. | \`Cancel this stopped task with the stated reason while preserving its evidence and unresolved effects.\` | Cancellation record; no automatic rollback of external effects. |

### Discover, install, inspect, then enable a bundle

1. Run \`extension discover MANIFEST\` and review the manifest before registration.
2. If registration is authorized, run \`extension install MANIFEST --state-dir STATE\`. The new registration is disabled.
3. Run \`extension inspect --state-dir STATE\`. Retain its \`state_digest\`; review the artifact and effective grants. Plugin bundles also require the accepted registry/signature configuration.
4. If enabling that exact state is authorized, run \`extension enable --state-dir STATE --checkpoint STATE_DIGEST\` and supply \`--registry REGISTRY.json\` where required. Carry the digest from step 3. Inspect the enable receipt.

**Alternative maintenance actions:** \`disable\`, \`remove\` and \`replace\` are chosen
for their own purpose and current state. They are not additional mandatory steps
after enable. Read each action's help before using it.

## Compatibility commands

These preserve existing scripts' invocation contracts. For new tasks, start with
\`plan\`, \`build\`, \`review\`, \`fix\`, \`test\`, \`status\` and \`resume\`.

\`\`\`text
attune-harness review-form
attune-harness inspect-review
attune-harness resume-review
attune-harness reconcile-review
attune-harness transfer-review
attune-harness cancel-review
\`\`\`

\`review-form\` prepares the legacy request form. \`inspect-review\` reads a saved
legacy review; the remaining controls resume, reconcile, transfer or cancel that
legacy run under their original arguments. They are not extra steps required
after every new task. Use each command's own \`--help\` when maintaining an
existing script.

## Verification boundary

This catalog was checked against the published **1.5.0** installation: top-level
\`--help\`, \`--help-all\`, all 32 command help pages and 63 nested help selections,
plus the installed CLI dispatch/workflow source and release-pinned CLI guide.
Only help was executed for this reference; the mutation, integration, retry and
model-dispatch commands shown here were not run to document them. Examples need
your actual paths, configuration and acceptance values. Release/platform limits
from the [1.5.0 getting-started guide](/harness/help/1-5-0/) still apply.
`;
