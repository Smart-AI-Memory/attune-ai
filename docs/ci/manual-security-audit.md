# Manual security audit CI

Automatic PR CI verifies audit evidence without making model calls. The separate
[manual workflow](../../.github/workflows/security-audit-manual.yml) runs an
authenticated SDK audit only after explicit spending approval. Both workflows
must be present on trusted `main` before this route can operate.

## Provide the reviewed identity

The manual workflow accepts these inputs:

| Input | Required value |
| --- | --- |
| `pull_request` | An open, same-repository PR targeting `main`. |
| `reviewed_sha` | The full, lowercase, 40-character head SHA approved for the audit. |
| `authorize_spend` | Explicit approval for this run; the default is `false`. |

The workflow checks the current PR head before and after the audit. It installs
the locked package without model credentials, then gives the audit step its
inference credential. The standard audit uses the existing 20-turn limit and a
$10 SDK budget cap. This cap is not an aggregate billing guarantee. The reviewed
commit executes on the runner; it is not sandboxed against malicious approved
code.

A workflow rerun is refused because it would reuse the original approval. A
fresh dispatch needs fresh approval. Any later dispatch for the same PR and SHA,
including a refused or cancelled attempt, becomes the latest evidence attempt
and can revoke an earlier pass. Do not dispatch a run as a connectivity probe.

## Read the result

The trusted-main controller checks the workflow identity, first run attempt,
current PR head, producer bytes, artifact digest and payload hashes. It accepts
only a supported completed SDK report. Missing, expired, malformed, failed or
incomplete evidence produces a failed **Security Scan** check. Critical findings
remain blocking; bypass labels do not apply to this route. Fork PRs are not
supported by the manual audit.

A successful controller job means that it delivered a check result, including
a failed result. Read the **Security Scan** conclusion to determine audit
acceptance. Whether that check is required for merging depends on repository
settings and maintainer policy; this change does not modify those settings.

A successful audit means the approved commit's scanner reported completion under
the trusted producer. It does not establish exhaustive security coverage or model
quality. An older commit's audit never qualifies a newer PR head.

The check contains severity counts and a link to the run. Detailed results remain
in the `manual-security-audit-<sha>` artifact for seven days. Upload requires
successful literal credential-byte sanitation and payload binding. Sanitation
does not guarantee removal of encoded credentials or unrelated secrets. Approve
this artifact disclosure as part of the run authorization.

Requested, running and completed audit events reconcile the latest attempt.
GitHub API outages, check-publication errors and a dispatch racing the final
metadata read can delay reconciliation. Publication is attempted once. Inspect
the actual run and check metadata before authorizing another attempt; an error
does not establish a clean audit.
