---
type: tip
name: plugin-tip
feature: plugin
depth: tip
generated_at: 2026-06-10T07:07:04.684068+00:00
source_hash: 97a2943dbbe1f0524955dd7678a2b8b4eb09cacaf89d2950ee2705251fcd2249
status: generated
---

# Tip: working effectively with plugin

Call `estimate_utilization()` before you call `build_resume_prompt()` — passing a bloated transcript into the resume builder wastes context budget that the prompt itself needs.

**Why it sticks:** `estimate_utilization` returns a `float` in `[0.0, 1.0]`; if it's already high, `format_warning` in `hooks.compact_warning` can surface that to the user before you spend tokens on the full resume prompt.

**Tradeoff:** Adding the utilization check is an extra call to `hooks._transcript_size.estimate_utilization`. In fast-path hooks where transcript I/O is expensive, you may choose to skip it and call `build_resume_prompt` unconditionally — just know you're trading responsiveness for accuracy.
