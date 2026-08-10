# D11 Pre-Flight Checklist — lead diffs, before the review lane

**Created:** 2026-08-10 (chair: "sounds promising", 2026-08-09)
**Source:** repeat-class taxonomy from the 2026-08-09 seven-lane
R5 run — the classes different-model lanes keep re-finding in
lead-authored diffs.

---

## When this fires

Before pushing any lead-authored diff that touches src/ or tests/
— mandatory when the diff will enter a D11b different-model review
lane (risk classes: security, persistence, release,
governance/enforcement, external boundaries, disputed findings).
Run the checklist BEFORE the lane launches, so lanes spend their
attention on novel findings instead of re-finding these classes.

## The checklist

Walk the diff once per class. Each check names the concrete probe.

1. **Fail-open paths that crash on legal-but-unexpected input.**
   For every `except`/fallback/degraded branch: feed it the full
   legal input domain (None, empty string, empty list, zero-length
   corpus, unicode). A fail-open path that raises on legal input
   is fail-closed in disguise.
2. **Unbounded / off-by-one windows.** For every slice, window,
   limit, or pagination bound: probe both ends, the empty window,
   and N == limit exactly. Check that "last N" and "since T"
   agree on inclusivity.
3. **Record-before-stamp ordering.** For every persistence write
   that also flips a status/stamp: the durable record must land
   BEFORE the stamp flips. A crash between the two must leave a
   recoverable, honest state — never a stamp pointing at a record
   that doesn't exist.
4. **String-prefix path containment.** Never
   `str(path).startswith(str(root))` — `/a/bc` passes a `/a/b`
   prefix check. Use `Path.is_relative_to()` on resolved paths
   (or the project's `_validate_file_path()` helper).
5. **Cross-corpus key collisions.** Any dict/index keyed on a
   name, stem, or slug derived from user content: confirm the key
   carries its corpus/namespace. Two corpora sharing a stem must
   not share a row.
6. **Windows USERPROFILE in home-isolating fixtures.** A fixture
   that redirects `HOME` must also set `USERPROFILE` —
   `Path.home()` on Windows reads the latter, and the fixture
   silently stops isolating on the Windows lanes.

## Measurement (the testability answer)

Efficacy is measured in the R5 dogfood ledger
(`docs/specs/cross-review/receipts.md`): repeat-class findings per
lane, before vs after this rule's adoption. A class that keeps
being found by lanes despite the checklist is a candidate for a
mechanical gate; a class lanes stop finding is the checklist
working (or the class going extinct — the ledger can't tell, and
doesn't need to).

## Cross-references

- D11/D11b–d rulings:
  `docs/specs/feature-lead-governance/decisions.md` (2026-07-29)
  and the collaboration contract's "Lead programmer and
  delegation" section.
- R5 ledger: `docs/specs/cross-review/receipts.md`.
