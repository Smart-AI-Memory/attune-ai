import walkthroughs from '@/content/harness-help/walkthroughs.generated.json';
import provenance from '@/content/harness-help/walkthrough-provenance.json';
import { COMMAND_REFERENCE } from './commands';
import { RELEASE_GUIDE } from './release-guide';
import { HARNESS_RELEASE_SLUG, HARNESS_SOURCE_ROOT, HARNESS_VERSION } from './release';

export const HELP_ROOT = '/harness/help/';
export const RELEASE_COMMIT = '0ecf8e6058cee9ed6f9b9510e043e3af3cbe1da0';
export const RELEASE_ROOT = `https://github.com/Smart-AI-Memory/attune-harness/blob/${RELEASE_COMMIT}`;
export const CURRENT_RELEASE = HARNESS_VERSION;
export const CURRENT_RELEASE_ROOT = HARNESS_SOURCE_ROOT;
const RELEASE_150_ROOT = 'https://github.com/Smart-AI-Memory/attune-harness/blob/v1.5.0';
export { provenance };

export interface HelpTopic {
  slug: string;
  title: string;
  goal: string;
  kind: 'task' | 'explanation' | 'troubleshooting' | 'reference';
  sourcePaths: string[];
  content: string;
  version?: string;
}

export const topics: HelpTopic[] = [
  {
    slug: HARNESS_RELEASE_SLUG, title: `Get started with Harness ${HARNESS_VERSION}`, kind: 'task',
    version: HARNESS_VERSION,
    goal: 'Install the selected version, choose a goal and inspect evidence before continuing work.',
    sourcePaths: ['README.md', 'pyproject.toml', 'docs/release-notes-1.5.1.md', 'docs/release-readiness-1.5.1.md'],
    content: RELEASE_GUIDE,
  },
  {
    slug: '1-5-0', title: 'Get started with Harness 1.5.0', kind: 'task',
    version: '1.5.0',
    goal: 'Install the published release, check a local result, and choose your next workflow.',
    sourcePaths: ['README.md', 'pyproject.toml', 'docs/release-notes-1.5.0.md'],
    content: `## What you can do

Attune Harness runs agent tasks, checks their results against criteria you supply,
and keeps the output and check evidence in a receipt. Use it to plan work,
build an accepted task, review a document against evidence, repair scoped files,
or test a captured change. Inspect a saved task before continuing it.

Version **1.5.0**, published October 19, 2026, includes merged Windows components
for captured tests, file-memory readers, saved-memory storage and experimental
native-memory transport. **Full Windows parity remains deferred.** Hosted
Windows Server checks do not qualify Windows 11 desktop or PowerShell journeys,
all storage/recovery cases, or live native-memory providers. Read the
[release notes](${RELEASE_150_ROOT}/docs/release-notes-1.5.0.md) for the
component evidence and outstanding requirements.

## Install the published release

Use Python 3.10 or later. Keep Harness and Attune AI in separate environments:
they pin different MCP SDK versions. You do not need Attune AI for this example.
Create a fresh environment instead of upgrading a retained evidence environment.

On macOS or Linux, in a new working directory:

\`\`\`sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install 'attune-harness==1.5.0'
\`\`\`

For a Windows installation, the equivalent PowerShell setup is:

\`\`\`powershell
py -3 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install 'attune-harness==1.5.0'
\`\`\`

The Windows commands are installation syntax, not a qualified PowerShell
walkthrough. If activation is restricted, use
\`.\\.venv\\Scripts\\python.exe\` directly for the Python commands below.

In the environment you selected, check the version and run the local example:

\`\`\`sh
python -c "from importlib.metadata import version; print(version('attune-harness'))"
python -m attune_harness
attune-harness --help
\`\`\`

**Expected result:** The version is \`1.5.0\`. The example returns a JSON
receipt with \`status: verified\`, output \`4\` and an accepted arithmetic
check. This deterministic example makes no model call; it establishes only
that example's result. The published base install and these checks were run
on macOS with Python 3.12.2 for this page.

If you use uv instead, install the isolated tool with
\`uv tool install 'attune-harness==1.5.0'\`, inspect
\`uv tool list --show-paths\`, then run \`attune-harness --help\`.
The Python commands above belong to the virtual-environment setup, not uv's
separate tool environment. Installing the Python package does not install a
Claude Code plugin or Codex skill; follow the
[host integration instructions](${RELEASE_150_ROOT}/README.md#use-harness-with-codex-claude-or-other-models)
for your chosen host.

## Choose a workflow

| Goal | Command | Before continuing |
| --- | --- | --- |
| Define work and review its scope | \`attune-harness plan --help\` | Inspect the goal, allowed files and acceptance criteria. |
| Execute an accepted task | \`attune-harness build --help\` | Check the saved checkpoint and configured participants. |
| Review a document against evidence | \`attune-harness review --help\` | Supply the document, corpus and review criteria. |
| Repair scoped files | \`attune-harness fix --help\` | Review the frozen probe and permitted file effects. |
| Test a captured change | \`attune-harness test --help\` | Inspect and accept the proposed tests. |
| Inspect saved work | \`attune-harness status --help\` | Read the state, evidence and next action before resuming. |

Run a route's help in the same selected environment. The
[CLI guide](${RELEASE_150_ROOT}/docs/cli-guide.md) describes configuration,
checkpoints and recovery. Opening a form, saving answers, accepting intent and
authorizing execution are separate actions. Browser forms do not dispatch
builds. External and native participants require their applicable explicit
grants; approving a plan does not authorize paid calls.

Read [AI tools and integrations](/harness/help/ai-tools-and-integrations/) for a
Typical use index, primary verbs, actual subcommands, ordered handoffs, sample
prompts and expected evidence.

## Choose retrieval deliberately

**Voyage AI is the service Patrick uses and recommends.** Its optional
integration requires a Voyage API key and makes paid retrieval calls. Install
\`'attune-harness[voyage]==1.5.0'\` in the isolated environment only when you
choose that integration, then follow the
[Voyage setup and configuration](${RELEASE_150_ROOT}/docs/cli-guide.md).
Installation itself does not authorize execution or spending.

**attune-rag is the explicitly selected local alternative.** Harness 1.5.0
pins \`attune-rag==1.2.0\` in its base dependencies; standalone attune-rag
1.2.1 is a separate release. Keep the Harness pin when following this page.
Automatic fallback during a Voyage outage is planned; it is not available in
1.5.0. Select and configure the intended retrieval path explicitly.

Redis is optional. The \`all\` extra includes Redis and Voyage; experimental
\`memory-native\` is separate. See the
[1.5.0 dependency metadata](${RELEASE_150_ROOT}/pyproject.toml) for exact pins.

## Continue with versioned guidance

- [Published 1.5.0 release](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.5.0) and [PyPI package](https://pypi.org/project/attune-harness/1.5.0/).
- [1.5.0 release notes](${RELEASE_150_ROOT}/docs/release-notes-1.5.0.md): merged components, evidence and deferred Windows requirements.
- [Preparation walkthroughs](${RELEASE_150_ROOT}/docs/tutorials-1.5.0-candidate.md): retained candidate-wheel procedures and observed limits. These require their recorded artifacts and POSIX setup; they are not published-wheel first-use instructions. Use the installation above to start with published 1.5.0.
- [Historical 1.3.0 task guides](/harness/help/get-started/): earlier behavior, explicitly versioned and retained for existing users.
- [Report a problem](https://github.com/Smart-AI-Memory/attune-harness/issues): include the installed version, route and redacted diagnostic. Keep credentials, private form links and project data out of reports.
`,
  },
  {
    slug: 'ai-tools-and-integrations', title: 'AI tools and integrations', kind: 'reference',
    version: CURRENT_RELEASE,
    goal: 'Find commands by typical use, understand their order and know where judgment and approval enter.',
    sourcePaths: ['docs/cli-guide.md', 'src/attune_harness/cli.py', 'src/attune_harness/work_cli.py', 'src/attune_harness/task_cli.py'],
    content: COMMAND_REFERENCE,
  },
  {
    slug: 'get-started', title: 'Get started', kind: 'task',
    goal: 'Check your installation and see a local result before starting real work.',
    sourcePaths: ['pyproject.toml', 'docs/cli-guide.md', 'src/attune_harness/__main__.py'],
    content: `## Set up an isolated environment

Use Python 3.10 or later. Keep Harness in its own environment: Harness and
Attune-AI pin different MCP SDK versions. Attune-AI is not required.

1. In a new working directory, create an environment: \`python3 -m venv .venv\`.
2. Activate it. On macOS or Linux, use \`source .venv/bin/activate\`. On Windows PowerShell, use \`.venv\\Scripts\\Activate.ps1\`.
3. Install the released base package: \`python -m pip install 'attune-harness==1.3.0'\`.
4. Check the selected interpreter's installed version: \`python -c "from importlib.metadata import version; print(version('attune-harness'))"\`.
5. Run the local demonstration: \`python -m attune_harness\`.

**Expected result:** The version is \`1.3.0\`. The demonstration prints a JSON
receipt with a verified result. It uses a deterministic local worker and an
independent arithmetic check; it makes no model call. This result establishes
that example's check, not the quality of an AI participant.

## Choose the next outcome

- [Start and continue work](/harness/help/start-and-continue/): answer an existing draft's questions and review its intent.
- [Plan and accept work](/harness/help/plan-and-accept/): preview the allowed files and acceptance criteria before a build.
- [Research a question](/harness/help/research/): retrieve local sources and check a supported link claim.
- [Save and resume](/harness/help/save-and-resume/): reopen saved intake and understand execution boundaries.

The browser companion opens existing saved tasks. It does not provide a released
**New task** control in 1.3.0. The two form walkthroughs include a disposable
trainer fixture; sample answers are examples, not findings for your project.

## Prepare the release examples

The planning and research examples use files from the repository, which are not
included in the installed wheel. With the environment active, put a release
checkout in an unused directory:

\`\`\`sh
git clone --branch v1.3.0 --depth 1 https://github.com/Smart-AI-Memory/attune-harness.git harness-1.3.0
\`\`\`

Set \`R\` to that checkout's absolute path. In a macOS/Linux shell, from its
parent directory, use \`R="$PWD/harness-1.3.0"\`. The published commit is
\`${RELEASE_COMMIT}\`. Verify it with \`git -C "$R" rev-parse HEAD\`.
The tutorial setup uses POSIX shell syntax; Windows command adaptation is not
newly tested here. Keep task records outside checkouts used for file effects.
On macOS use canonical paths; \`/tmp\` is a symlink to \`/private/tmp\`.

Read [dependencies and compatibility](/harness/help/dependencies/) before adding
optional providers or integrating with another host.
`,
  },
  {
    slug: 'start-and-continue', title: 'Start and continue work', kind: 'task',
    goal: 'Turn saved draft answers into an intent you can inspect and accept.',
    sourcePaths: ['docs/tutorials-1.3.0.md', 'docs/cli-guide.md', 'src/attune_harness/gui_forms_intake.py'],
    content: walkthroughs['start-and-continue'],
  },
  {
    slug: 'plan-and-accept', title: 'Plan and accept work', kind: 'task',
    goal: 'Review the exact scope and accept its current checkpoint before execution.',
    sourcePaths: ['docs/tutorials-1.3.0.md', 'docs/cli-guide.md', 'src/attune_harness/work_cli.py'],
    content: walkthroughs['plan-and-accept'],
  },
  {
    slug: 'research', title: 'Research a question', kind: 'task',
    goal: 'Find local evidence and recognize what the verification actually checked.',
    sourcePaths: ['docs/tutorials-1.3.0.md', 'docs/local-workflow.md'],
    content: walkthroughs.research,
  },
  {
    slug: 'save-and-resume', title: 'Save and resume', kind: 'task',
    goal: 'Keep saved answers across sessions and inspect work before continuing execution.',
    sourcePaths: ['docs/tutorials-1.3.0.md', '.agents/skills/attune-harness/references/browser.md', 'docs/memory-saving.md'],
    content: walkthroughs['save-and-resume'] + `
## Continue execution deliberately

Saving form answers records intake. Accepting intent records a scope decision.
Neither action starts a build. Harness 1.3.0 browser forms cannot dispatch builds
or resume execution.

1. In the same selected environment, inspect the saved task: \`attune-harness status "$TASK" --format markdown\`.
2. Read its state, evidence and next action. Resolve stale scope or uncertain effects before continuing; do not blindly repeat a submission.
3. If the task is eligible and you have the required current authority, continue through the CLI's documented \`resume\` route. Read \`attune-harness resume --help\` and inspect the participant registry first. External/native execution requires its applicable grants and can incur provider costs.

**Expected result:** Inspection explains the saved state; it does not execute
work. An authorized resume may dispatch participants or effects. Use a new form
listener to reopen intake instead of invoking execution resume for that purpose.

Explicit CLI saved memory is a separate store from form answers. See the
[released saved-memory guide](${RELEASE_ROOT}/docs/memory-saving.md).
`,
  },
  {
    slug: 'troubleshooting', title: 'Troubleshooting', kind: 'troubleshooting',
    goal: 'Recover a form or installation while preserving the saved task and its evidence.',
    sourcePaths: ['docs/cli-guide.md', '.agents/skills/attune-harness/references/browser.md', 'src/attune_harness/features.py'],
    content: `## The private form link stopped working

The form listener must remain running. A stopped listener invalidates its link.

1. In the original selected environment, start a listener for the same canonical task directory: \`python -m attune_harness.gui --task "$TASK" --edit --launch-json\`.
2. Keep the process running. Open its new private \`launch_url\`; do not reuse the previous link.
3. Select **Continue form** and inspect **Saved answers** before typing or submitting again.

**Expected result:** Previously saved answers remain in the authoritative task
record. Unsaved typing is not guaranteed to survive. Launcher links contain
private access information; keep them out of public docs, screenshots and logs.

## The form says the checkpoint is stale

Opening a new form or restarting the listener can expire the prior checkpoint.

1. Open the current form for the same saved task.
2. Read the current guidance and saved answers. Review any changed scope before accepting it.
3. Submit through the current form only when its answers and intent are correct.

**Expected result:** The decision is bound to the current preview. Do not replay
an older submission or edit task evidence to bypass the refusal.

## A dependency or command is unavailable

1. Check the installed distribution in the interpreter you selected: \`python -c "from importlib.metadata import version; print(version('attune-harness'))"\`.
2. Read the selected route's \`--help\` and the actual diagnostic. Follow the installed interface if it differs from this 1.3.0 guide.
3. Compare your installation with [the release dependency map](/harness/help/dependencies/). A \`--no-deps\` installation omits the normal base dependencies; restore the normal install in a disposable isolated environment.

**Expected result:** The CLI and interpreter refer to one environment. Optional
integrations are installed only for the requested journey. Do not upgrade a
retained evidence environment or combine Harness and Attune-AI to clear a refusal.

## A task path is refused

Use an existing canonical absolute directory for browser registration. Resolve
symlinks before launching; on macOS, use \`/private/tmp\` rather than \`/tmp\`.
Task directories must sit outside checkouts used for file effects. Read the
route-specific refusal before moving or recreating anything.

## A result is paused, rejected or failed

Inspect \`attune-harness status "$TASK" --format markdown\` and retain its
evidence. A successful status command means inspection worked; it does not mean
the task passed. Resolve its stated next action and current authority before
resuming. Unknown or uncertain effects need reconciliation, not a blind retry.

If you need help, report the version, route, redacted diagnostic and expected
result through [Harness issues](https://github.com/Smart-AI-Memory/attune-harness/issues).
Do not include private launcher links, credentials or project data.
`,
  },
  {
    slug: 'dependencies', title: 'Dependencies and reference', kind: 'reference',
    goal: 'Choose the required integration and find guidance for the version you use.',
    sourcePaths: ['pyproject.toml', 'docs/cli-guide.md', 'docs/codex-plugin.md', 'docs/local-workflow.md'],
    content: `## What a normal 1.3.0 install supplies

Harness requires Python 3.10 or later. Its released package metadata pins these
base dependencies. You do not need to install attune-forms separately for the
Harness forms journey.

| Package | Pinned version | Used for |
| --- | --- | --- |
| attune-forms | 0.17.0 | Rendered forms and answer collection |
| attune-rag | 1.2.0 | Local source retrieval |
| attune-verify | 0.6.0 | Supported verification checks |
| mcp | 2.2.0 | MCP integration |
| tiktoken | 0.12.0 | Token counting |
| packaging | 26.3 | Version compatibility checks |

These are Harness's **release pins**, not a claim that they are each package's
latest version. Independent dependency upgrades require compatibility review.
The [release package metadata](${RELEASE_ROOT}/pyproject.toml) is authoritative.

## Add optional integrations only when needed

| Extra | Release dependency pins | Boundary |
| --- | --- | --- |
| redis | redis 5.3.1 | Optional Redis integration |
| voyage | voyageai 0.5.0, lancedb 0.38.0, pyarrow 25.0.1, jsonschema 4.26.0, httpx2 2.13.0 | Requires a Voyage key; retrieval makes paid calls |
| memory-native | anthropic 1.6.0, httpx2 2.13.0 | Experimental, POSIX-only native memory path |
| all | redis and voyage extras | Excludes experimental memory-native |

For example, install \`'attune-harness[redis]==1.3.0'\` in the isolated
environment if the requested integration needs Redis. The release guide
recommends \`[all]\` for the wider qualified integration set; the local examples
in this Help Center need only the normal base install. Installing an extra does
not grant execution authority or authorize spending.

## Integrate with a host

- [Codex plugin and standalone skill](${RELEASE_ROOT}/docs/codex-plugin.md): install the host integration separately from the Python CLI, and verify its installed help.
- [Browser companion reference](${RELEASE_ROOT}/.agents/skills/attune-harness/references/browser.md): open existing task forms through the selected interpreter; treat launch URLs as private.
- [CLI integration guide](${RELEASE_ROOT}/docs/cli-guide.md): participant configuration, task execution and MCP setup. Keep Harness and Attune-AI in separate environments because of their MCP SDK pins.

## Read guidance for your version

- [Harness 1.3.0 release](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.3.0) and [1.3.0 CLI reference](${RELEASE_ROOT}/docs/cli-guide.md): baseline for these pages.
- [Current main documentation — development](https://github.com/Smart-AI-Memory/attune-harness/tree/main/docs): may describe newer work; compare its version and evidence before using it.
- [Prototypes — unreleased](https://github.com/Smart-AI-Memory/attune-harness/tree/main/prototypes): design exploration, not released help.
- [Existing Attune-AI documentation](/docs/): separate product documentation.

Browser build dispatch and execution resume are unavailable in Harness 1.3.0.
Broader navigation/spec editor designs and pending form accessibility changes
are not presented as released. The local walkthrough evidence covers synthetic
macOS examples; it does not qualify all hosts, Windows, participant quality or
paid-provider behavior.
`,
  },
];

export function topicHref(slug: string): string {
  return `${HELP_ROOT}${slug}/`;
}

export function getTopic(slug: string): HelpTopic | undefined {
  return topics.find((topic) => topic.slug === slug);
}
