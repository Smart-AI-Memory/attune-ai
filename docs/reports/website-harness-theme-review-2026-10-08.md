# Harness-led website theme review — 8 October 2026

Scope: `website/harness-led-homepage` against base `2e3e4f1b50c490b106cc7d5737db5965e36abdfb`. The homepage leads with Attune Harness and three exploratory paths; shared page styling and static documentation use an authored green theme adapter. Released Forms token projections and documentation content are preserved.

## Independent review

A native Codex advisory lane using gpt-6-astra reviewed source and the evidence chain, including all 274 ordinary documentation head changes. This was a real subscription-session review, not a synthetic `attune.roundtable` execution or a paid API run. No board thread or countersigned artifact is claimed.

Five findings were accepted and fixed:

1. Separate control borders from legacy code/panel backgrounds to preserve light/dark contrast. Dark tag-link background `#314b3b` with foreground `#b8cdbb` calculates to 5.68:1.
2. Retain the homepage's 64px clearance below fixed navigation.
3. Point mobile Collaborate navigation to the collaboration section.
4. Keep the diagnostic browser-host script byte-identical to base; its literal `</head>` inside JavaScript is not a document-head insertion point.
5. Replace the self-referential muted CSS variable with the semantic muted token.

The reviewer confirmed each correction. Normalized comparison of the 274 styled documentation pages found zero changes beyond the stylesheet link and whitespace. The headless redirect and diagnostic remain unchanged.

The subsequent authorization-helper extraction resolves unsupported Next route exports. Independent comparison found moved helper blocks and remaining handler bodies identical to base after trimming surrounding blank lines. The reviewer's two authorization suites passed 27 tests with database/email operations mocked. Its capabilities suite passed three tests with the established project Python runtime. These receipts do not establish real database initialization or message delivery.

## Integration checks

The integrating session reran 68 website tests, eight additional capabilities/demo tests, 22 Python website-accuracy/token-projection tests, TypeScript and lint. All passed; lint retains three existing warnings. The production Webpack build passed. Pinned pre-commit auto-fixed only whitespace/EOF, then passed.

Built-site acceptance independently found three layout issues: an unlayered `nav button` display rule overrode desktop hiding, the fixed-size Documentation title overflowed the mobile width with the system font, and preserved Markdown code blocks overflowed the mobile article column. The adapter now preserves responsive button visibility and gives existing page titles a mobile scale and contains code/table scrolling within the Markdown column; more-specific homepage and Material heading rules remain intact. Final responsive/browser receipts and live deployment verification are separate publication gates, pending at this report's initial write.

The further 320px audit exposed intrinsic grid widths in existing Docs/Blog cards and long benchmark labels/paths. The adapter allows grid children to shrink, long main-content tokens to wrap, and narrow metric rows to wrap. Material code/focus variables follow its selected palette independently of the OS theme. Follow-up independent source review found no actionable defect in these deltas.
