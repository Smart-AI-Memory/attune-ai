import { HARNESS_PUBLISHED, HARNESS_RELEASE_NOTICE, HARNESS_SOURCE_ROOT, HARNESS_VERSION } from './release';

export const RELEASE_GUIDE = `## Version and scope

${HARNESS_RELEASE_NOTICE}

Harness ${HARNESS_VERSION} is a maintenance update after 1.5.0. The inspected
source adds exact plugin-signature input validation and readable evidence for
completed document assessments. It also carries documentation and verification
improvements. Read the [source release notes](${HARNESS_SOURCE_ROOT}/docs/release-notes-1.5.1.md)
and [readiness record](${HARNESS_SOURCE_ROOT}/docs/release-readiness-1.5.1.md)
for the current release boundary.

**Full Windows parity remains deferred.** Hosted Windows Server software
checks do not establish Windows 11 desktop, PowerShell journeys, full storage
and recovery acceptance, or live native-memory reliability. Native planning and
building remain experimental. Browser forms save and review intent; they do not
dispatch builds.

## ${HARNESS_PUBLISHED ? 'Install Harness' : 'Prepare to install after publication'}

${HARNESS_PUBLISHED ? 'Inspect your existing version and runtime before installing.' : '**Do not use the 1.5.1 installation command until the package is published.** Use the [published 1.5.0 guide](/harness/help/1-5-0/) for an installation today. The following is the prepared 1.5.1 procedure.'}

Use Python 3.10 or later and keep Harness separate from Attune AI. Preserve
older evidence environments and saved task directories. For a managed CLI:

\`\`\`sh
uv tool install 'attune-harness==${HARNESS_VERSION}'
uv tool list --show-paths
attune-harness --help
\`\`\`

**Expected result:** the tool list identifies Harness ${HARNESS_VERSION} and its
environment; help lists the available commands. Installing the runtime does not
install a Claude Code plugin or Codex skill. Follow the
[host setup](${HARNESS_SOURCE_ROOT}/README.md#use-harness-with-codex-claude-or-other-models)
for the agent you use.

For Python API use, create a separate environment instead:

\`\`\`sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install 'attune-harness==${HARNESS_VERSION}'
python -c "from importlib.metadata import version; print(version('attune-harness'))"
python -m attune_harness
\`\`\`

**Expected result:** the version is ${HARNESS_VERSION}; the deterministic local
example returns a verified arithmetic receipt. This example makes no model call
and does not measure a model's reliability. The commands above use a virtual
environment; uv's managed tool environment is separate.

On Windows, create the environment with \`py -3 -m venv .venv\` and use
\`.\\.venv\\Scripts\\python.exe\` for the Python commands. This supplies setup
syntax, not a newly qualified Windows shell walkthrough.

## Choose a useful next step

Start with [What do you want to accomplish?](/harness/help/goals/). It contains
21 expandable goals and six testing FAQs, with prompts, steps, expected outputs
and human review points.

| Goal | Start with | Review before execution |
| --- | --- | --- |
| Define a feature | \`attune-harness plan --help\` | Intent, file scope, effects and acceptance checks. |
| Build accepted work | \`attune-harness build --help\` | Current checkpoint and configured participant permissions. |
| Assess a document | \`attune-harness review --help\` | Document, evidence sources, criteria and assessor. |
| Repair a defect | \`attune-harness fix --help\` | Supported checkout, explicit files and a trusted frozen probe. |
| Check a change | \`attune-harness test --help\` | Selected tests, exclusions, interpreter and saved preview. |
| Return to saved work | \`attune-harness status --help\` | Saved state, evidence, uncertainty and the next action. |

Use [AI tools and integrations](/harness/help/ai-tools-and-integrations/) for
the command catalog and ordered handoffs. Preparing a request, accepting intent
and authorizing execution remain separate actions.

## Inspect completed assessment evidence

For a completed document assessment, use:

\`\`\`sh
attune-harness status TASK --format markdown
attune-harness status TASK --format html > assessment-report.html
\`\`\`

Replace \`TASK\` with the existing assessment task directory. The report shows
the accepted goal and criteria, recorded checker outcomes, retrieved-source
identities and separately attributed participant judgments. Open the generated
HTML file to inspect the report. A successful status command does not mean the
assessment passed.

Inspection does not rerun checks or refresh the evidence. Semantic acceptance
and source freshness still require assessment. Other task profiles and
incomplete assessments retain their existing presentation. See the
[assessment inspection procedure](${HARNESS_SOURCE_ROOT}/docs/cli-guide.md#inspect-completed-assessment-evidence-151-candidate).

## Choose integrations deliberately

The normal base install is enough for the deterministic example. Redis and
Voyage are optional integrations; native memory is a separate experimental
profile. Keep the exact [package dependency pins](${HARNESS_SOURCE_ROOT}/pyproject.toml).

Voyage needs an API key and authorized paid calls. Local keyword retrieval is
an explicitly selected alternative. Automatic fallback during a Voyage outage
is not available. Installation grants no provider, file or execution permission.

## Evidence and older versions

${HARNESS_PUBLISHED ? 'Follow the versioned release record for final artifact identity and qualification.' : 'This preparation page was reconciled against the linked source. A final published-wheel check and release-source reconciliation are still required before publication.'}
Software checks, example outcomes, model quality and human usability establish
different claims. Keep each result within its stated boundary.

- [Historical 1.5.0 installation](/harness/help/1-5-0/).
- [Historical 1.3.0 task guides](/harness/help/get-started/).
- [Report a Harness problem](https://github.com/Smart-AI-Memory/attune-harness/issues).
`;
