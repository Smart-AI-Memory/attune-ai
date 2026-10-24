# Existing CSV example — source notes

These notes summarize the existing synthetic CSV tutorial and accepted candidate 02 at ~/attune-harness/csv-activity-prototype/docs/spec-v02.md. They are background evidence, not a new implementation grant or a claim that this proposed project has executed tests.

## Established behavior to preserve

1. List and export share selection. A known simulated user needs project membership. Row restriction null adds no restriction; a named list allows its named users; an empty list allows nobody. Unknown users fail closed. This is simulated identity, not authentication.
2. Project, kind, date-from, date-to and summary-search filters intersect. Project and kind match exactly with case sensitivity. Summary search uses Unicode casefold. YYYY-MM-DD date bounds are inclusive; reversed ranges fail.
3. Rows sort by date ascending, then unique activity_id. No pagination or hidden limit.
4. Columns in order: activity_id,date,project,actor,kind,summary,minutes. Membership/restriction metadata are excluded.
5. Output is UTF-8 without BOM, all cells quoted, embedded quotes doubled, CRLF record endings. Commas, quotes and embedded line endings must round-trip through a CSV parser. No matches means one header record and no data rows.
6. For every text column, prefix one ASCII apostrophe when the first significant character is =, +, -, @ or a fullwidth counterpart after skipping leading Unicode whitespace/format characters; also prefix a value starting with TAB, CR or LF. Preserve the remainder. Minutes is a validated nonnegative integer. This changes dangerous literal text and does not establish safety for every spreadsheet consumer.
7. Reject invalid schema, duplicate IDs, invalid references/dates/types, negative minutes and disallowed controls. Validate before creating an export.
8. Require a new destination file; never overwrite. On a writing failure, remove the new partial file. Do not modify the input dataset or list's literal text. Report the public row count separately from CSV file content.
9. Same source, user and filters produce identical export bytes.

## Concrete synthetic review example

For viewer + atlas + review + 2026-10-11 through 2026-10-12, the original tutorial expects a-0002 and a-0004. One summary contains a newline and Café text; another begins with spaces followed by =SUM(1,2). An inaccessible project yields headers only. These are proposed acceptance cases for the new spec, not freshly executed results.

## Provenance and limits

The existing tutorial distinguishes host-authored implementation from Harness retention/testing and a later bounded replay of known source. Do not attribute this existing code to a new roundtable, or claim production access control from synthetic identity. The full code, fixture, tests, private records and machine configuration are not part of this proposed source packet.
