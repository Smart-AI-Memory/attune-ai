---
type: faq
name: deep-review-faq
feature: deep-review
depth: faq
generated_at: 2026-07-14T15:58:50.492567+00:00
source_hash: 5e2ccde04cab83b41196f2c5f05ef11b8e7be00e39bb8040b02fb2a225aef083
status: generated
---

# Deep Review FAQ

## What's the difference between deep-review and security-audit?

Deep-review covers three domains (security, quality, test
gaps) in one pass and can be narrowed with `focus`;
security-audit is security-only with four specialized subagents
and a deeper treatment. Use deep-review for breadth,
security-audit for the thorough security sweep.

## How do I run only the security pass?

`await workflow.execute(path=..., focus=["security"])`,
or on the CLI `--input '{"focus": ["security"]}'`.

## Which calls are async?

`execute` is the only public method and it is a
coroutine — `await` it or use `asyncio.run`.

## Is there an `attune deep-review` command?

No dedicated subcommand — run it as
`attune workflow run deep-review`, the `/deep-review` skill, or
the `deep_review` MCP tool.

## Does a clean review mean the code is good?

No. Findings are LLM predictions, not proofs, and a clean
pass is not a guarantee — treat the review as one input.
