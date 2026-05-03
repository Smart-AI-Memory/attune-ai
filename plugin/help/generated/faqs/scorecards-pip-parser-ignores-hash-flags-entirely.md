---
name: scorecards-pip-parser-ignores-hash-flags-entirely
source: .claude/CLAUDE.md
summary: This template explains why Scorecard's PinnedDependenciesID check does not
  recognize inline `--hash` flags in `pip install` commands and recommends using a
  requirements file with `--require-hashes` instead.
tags:
- packaging
type: faq
---

# FAQ: Why Does Scorecard Flag `pip install --hash` Commands as Unpinned?

## Answer

Scorecard's `PinnedDependenciesID` check does not recognize the `--hash` CLI flag passed directly to `pip install`. As a result, even a command like the following is flagged as "not pinned by hash":

```sh
pip3 install 'pkg==1.0' --hash=sha256:abc...
```

Scorecard only considers a dependency properly pinned when `--require-hashes` is used alongside a requirements file. Inline `--hash` arguments on the command line are ignored by the parser entirely.

## Recommended Solution

Use a requirements file with `--require-hashes` instead of passing hash flags directly to `pip install`:

```txt
# requirements.txt
pkg==1.0 --hash=sha256:abc...
```

```sh
pip install --require-hashes -r requirements.txt
```

This format is recognized by Scorecard and will satisfy the `PinnedDependenciesID` check.

## Related Topics

- **Check**: `PinnedDependenciesID` — verifies that dependencies are pinned by hash
- **Error**: Scorecard's pip parser ignores `--hash` flags passed directly to `pip install`
- **See also**: [Scorecard documentation on pinned dependencies](https://github.com/ossf/scorecard/blob/main/docs/checks.md#pinned-dependencies)
