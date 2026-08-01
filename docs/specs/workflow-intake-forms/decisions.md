# Workflow Intake Forms — Decisions

**Status:** active (decision log; grows as the spec advances)

## D1 — Theme byte budget amended 4 KB → 6 KB (chair, 2026-07-31 ~21:20 ET, Task 3 execution)

Task 3's execution measurement: `FORM_THEME_CSS` — the full family
sheet WITH the design-mandated `var()` fallback literals — is
5,574 B raw, 5,192 B minified; the scope-prefix repetition is
~920 B, so even CSS-nesting restructuring lands ~4.3 K. The 4 KB
figure was authored before the fallbacks existed and measured a
per-widget subset, not the full concatenation.

Chair ruled (over the presented fork, lead recommendation
followed): amend the budget to 6 KB rather than cut real rules to
honor a stale number. Rationale preserved from the original
design: the latency claim (sub-millisecond against the ~100–145 ms
derivation baseline) holds identically at 6 KB, the anti-framework
ratchet remains the test itself plus the hard bans (no fonts, no
icon fonts, no images, no @import), and widgets continue shipping
per-form family subsets (~2.5–3 KB class). `test_form_theme_budget`
enforces 6,144 B; design.md amended in the same commit.
