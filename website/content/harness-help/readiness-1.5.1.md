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

## Before package publication

Documentation readiness is a prerequisite to the 1.5.1 release. Do not defer
instruction and walkthrough validation until PyPI publication.

1. Review all current documentation for the selected final source: canonical
   instructions, Help, installation, command reference, examples and actual
   tutorial/class derivatives. Reconcile changes after the source above and
   record each topic as changed or unchanged but reviewed. Coordinate canonical
   walkthroughs and derivatives with their existing owners. Historical guides
   retain their original versions and evidence; they are not relabeled as 1.5.1.
2. Test installation, version/help and the deterministic example against the
   exact versioned candidate wheel in a new environment, using the local wheel
   before it is available from PyPI. Check completed-assessment Markdown and
   HTML presentation with a retained completed task and reproduce affected
   walkthroughs. Keep source tests, actual walkthrough outcomes, human
   acceptance and untested boundaries distinct.
3. Record candidate source, artifact identity, content dispositions and results
   in the release readiness record and this PR. Run projection, link, website
   and required package qualification checks. Resolve documentation blockers
   before requesting the separately gated package publication approval.

## After package publication

1. Verify the published 1.5.1 package bytes and release/source identity. Perform
   an index-install smoke check to confirm users receive the reviewed package.
   If identity or behavior differs, stop website publication and reconcile it.
   These distribution checks do not replace the candidate validation above.
2. Set `release.json` status to `published`, set `published_version` to `1.5.1`
   and pin `source_ref` to the verified release commit. Regenerate the goal guide
   and check the final version links, projection and website. This also enables
   current-page indexing and sitemap entries.
3. Record the final evidence in the PR, obtain the applicable merge approval,
   and publish through the existing main-branch deployment. Check the production
   Help landing-to-goals journey after deployment. Do not change hosting gates.

Website build and interaction checks establish the delivered website behavior.
They do not qualify Harness execution, participant quality, all Windows
storage/recovery cases or live native-memory reliability. Full Windows parity
remains deferred and native planning/building remain experimental.
