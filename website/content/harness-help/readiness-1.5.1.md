# Harness 1.5.1 website readiness

Status: preparation; publication held until Harness 1.5.1 is released.
Reviewed October 22, 2026 against Harness source
`0f2711b4c88ee4f231f61d71cd70a0c840be6357`. The source notes still identify
1.5.1 as unpublished; the published package remains 1.5.0. This record does
not claim a final 1.5.1 wheel, Windows desktop walkthrough, live model
consultation or human acceptance of those journeys.

## Content disposition

| Content | Disposition | Evidence and limits |
| --- | --- | --- |
| Help landing and navigation | Changed | Prominent goals link; learning category first; compact semantic anchors. |
| Goals guide | Added from the reviewed local guide | 21 goals and six testing FAQs; real intake captures remain labeled 1.5.0; other outputs are illustrative. No live consultation or example implementation is established. |
| Installation and runtime selection | Changed | Prepared 1.5.1 managed CLI and separate Python API setup follow `docs/installation.md` and package metadata. Installation today still points to published 1.5.0. Final-wheel replay pending. |
| Command reference | Reviewed and updated | Candidate source `docs/cli-guide.md`; prior published 1.5.0 catalog observations remain attributed. New completed-assessment status presentation is identified separately. |
| Completed assessment reporting | Added | Source `assessment_view.py`, `task_cli.py`, `tests/test_assessment_view.py` and CLI guide inspection section. Inspection retains outcomes and attribution; it does not rerun or accept an assessment. Final-artifact command replay pending. |
| Docs, FAQ, homepage and footer | Changed | Share release identity and link to Help/goals. Historical 1.4.0 quick start is retained with its original package and label. |
| 1.5.0 installation | Retained and reviewed | Original version, source links and published-wheel observation preserved. Links to newer guidance do not relabel those observations. |
| Seven 1.3.0 task guides | Unchanged but reviewed | Get started, start/continue, plan/accept, research, save/resume, troubleshooting and dependencies retain 1.3.0 behavior and source. No 1.5.1 replay claimed. |
| Four canonical training walkthroughs | Retained | Existing source snapshot, provenance and projector are unchanged. Candidate walkthrough links identify their original artifact; no final 1.5.1 walkthrough acceptance is claimed. |
| Older preparation page | Retained | `/next-release/` remains a noindex historical record with its original JSON. |

## Publication gate

1. Verify the Harness 1.5.1 GitHub release and PyPI package, including final
   version, source commit and artifact identity. Reconcile changes after the
   reviewed source above. Check the final release notes and readiness record.
2. Replay the installation, version/help and deterministic example against the
   published wheel in a new environment. Check completed-assessment Markdown
   and HTML presentation with a retained completed task; keep source tests and
   actual walkthrough evidence distinct. Coordinate remaining walkthrough and
   derivative dispositions with their existing owners.
3. Set `release.json` status to `published`, set `published_version` to `1.5.1`
   and pin `source_ref` to the verified release commit. Regenerate the goal guide
   and repeat projection, website, link and browser checks. This also enables
   current-page indexing and sitemap entries.
4. Record the evidence in the PR, obtain the applicable merge approval, and
   publish through the existing main-branch deployment. Check the production
   Help landing-to-goals journey after deployment. Do not change hosting gates.

Website build and interaction checks establish the delivered website behavior.
They do not qualify Harness execution, participant quality, all Windows
storage/recovery cases or live native-memory reliability. Full Windows parity
remains deferred and native planning/building remain experimental.
