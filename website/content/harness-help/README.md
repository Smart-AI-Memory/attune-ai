# Harness Help Center content maintenance

The current published-release entry is `/harness/help/1-5-0/`, authored in
`lib/harness-help/topics.ts`. Its installation uses PyPI 1.5.0 rather than a
candidate wheel. The base install, version, CLI help and deterministic demo
were checked on macOS/Python 3.12.2 on October 19, 2026. No Windows desktop,
paid-provider or candidate walkthrough execution is newly claimed.

The 1.5.0 `/harness/help/ai-tools-and-integrations/` reference uses the same topic
registry and renderer. `lib/harness-help/commands.ts` owns its command map;
complete fixtures/procedures remain in the linked existing versioned CLI guide
and canonical walkthroughs. The Typical use groups describe usual initiators,
not exclusive roles or permission grants. Keep actual subcommands separate from
action flags, numbered prerequisite/output handoffs separate from alternatives,
and acceptance separate from execution authority. The installed published 1.5.0
catalog was inspected through 32 top-level and 63 nested help selections without
executing the documented mutation or model commands. Next links stay within a
guide version so 1.5.0 readers do not enter historical 1.3.0 procedures by default.

The other seven guides retain 1.3.0 instructions and source identity. The
`next-release` route is now a noindex historical record, with its original
JSON unchanged. Neither that record nor the separately prepared 1.5.0 candidate
walkthrough overlay is relabeled as published-wheel evidence. Publication is
authorized for the scoped 1.5.0 Help page through the normal repository gates;
this does not authorize dependency changes or bypasses of failed checks.

`lib/harness-help/topics.ts` is the single authored source for Help Center
framing, topic IDs and release-reference guidance. One ordinary Markdown
renderer handles task, explanation, reference and troubleshooting content.
The first increment includes no separate class, editorial or book derivative.

`next-release.json` is a small readiness record for the new release candidate.
Its version and date remain unset. The separate `/harness/help/next-release/`
page stages only source-verified behavior and supplied capture observations,
labels them unreleased, and leaves next-version instructions pending coordinated
canonical source and integrated capture review.
Central owns the combined release checklist; this record covers the Help topics.

The four canonical walkthroughs remain owned in the Harness repository's
`docs/tutorials-1.3.0.md`. The `.source.md` here is a pinned input snapshot;
`walkthroughs.generated.json` is its generated presentation. Never hand-edit
either. `walkthrough-provenance.json` records the upstream commit, content hash
and distinct behavior release. It also states when the tutorial source is not
yet published. No link to an unpublished upstream commit is claimed to work.

Refresh from the owner's committed source after its review:

```sh
python3 scripts/project-harness-walkthroughs.py --repo /absolute/path/to/harness --commit FULL_SOURCE_COMMIT
python3 scripts/project-harness-walkthroughs.py --check
```

These commands run from `website/`. The projector preserves instruction text,
setup, expected results and limits, while converting the action table to a
numbered list and pinning guide links. Source questions and typed examples retain
their distinct formatting. New helper framing does not invent released controls.

Known source discrepancy: the release-pinned `docs/local-workflow.md` contains
older optional `[verify,rag]` installation instructions and treats forms intake
as future work. Released 1.3.0 package metadata places rag/verify in the base,
and its GUI supplies forms intake. The Help framing explicitly labels that
older reference and points to the verified release setup. Its retained upstream
bytes are unchanged; the discrepancy is sent to the canonical content owner for
the next documentation-readiness review.

## Every package version publication

Use the existing Harness release runbook's documentation readiness item and
its **Documentation readiness** record. For each of the seven topic IDs in
`topics.ts`, record changed or unchanged-but-reviewed, the candidate version and
code/test evidence, actual derivative owners, semantic walkthrough results and
limits, checked links, and retained/superseded older guidance. Coordinate the
snapshot refresh with the tutorial owner; do not fork the canonical procedures.

Versioned code and reproducible tests ground behavior; approved policy and style
requirements govern content. Approved project exceptions precede general Google
guidance. Flag conflicts for resolution instead of silently changing policy or
claiming code automatically grants approval.

Run projection drift, website tests, lint, TypeScript, direct Next compilation,
local links and browser journeys after relevant changes. Link/build success
does not replace explicit walkthrough review on the candidate. Keep old release
guidance useful and visibly versioned; current main and prototypes are separate.

The public Help overview and current release page are linked from `/docs/`
and the sitemap. Historical preparation remains noindex. The website Git integration creates hosted
previews from branch/PR updates and deploys main to production. Source
publication and production deployment require their applicable approval; do not
change hosting settings to bypass those boundaries.
