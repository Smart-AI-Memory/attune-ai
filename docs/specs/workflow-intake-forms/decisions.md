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

## D2 — Phase 2a ruled and executed same night: the merge fallback, six refinements, gate override (chair, 2026-07-31 ~22:15 ET)

Roundtable `q-intake-forms-phase2-design-001` (transcript
machine-local; msgs 2–5 promoted). Convergence 3/3: shape
right-sized; cache-free v1; thin two-consumer staging; the
re-expression gate right in spirit. Split 2–1 on template-less
fallback (codex+antigravity: free-text until authored slots;
claude: demand-gated derivation with telemetry).

**Chair rulings:** (1) THE MERGE — free-text fallback in v1 plus
claude's demand-telemetry marker on every template-less ask;
derivation is a debug tool only. (2) All six refinements PROMOTED:
structural-equality gate with stubbed providers; same-PR deletion
of hand FORM-BUILDING; cache-free v1; list-without-provider
rejected at build time; prefill exact-match only; drill-down
re-entrancy design text before migration. (3) IMPLEMENT NOW —
the chair's third timing override of the evening, over the lead's
post-demo recommendation. Gate-override on record: the
rule-of-three had not fired (two consumers); the chair overrode
his own sequencing gate deliberately, and codex's warning stands
in the spec as the third consumer's test: fix and spec "may be
structurally similar enough to produce a misleadingly elegant
API."

**Executed same session:** `intake_template.py` + fix/spec
re-expression + provider registration + 12-test gate suite
(structural-equality goldens copied verbatim from the deleted
hand construction), 347 elicitation tests green, existing 20
behavioral pins untouched. The drill-down question dissolved on
inspection: `--list-dirs` is a skill-side loop between renders,
not an in-form dependency — recorded in design.md.
