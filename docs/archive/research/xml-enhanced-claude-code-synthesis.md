# Research Synthesis: XML-Enhanced Prompts for Claude Code

**Date:** February 15, 2026
**Methodology:** External research (Anthropic docs, community projects, ecosystem analysis) + internal codebase analysis (35 XML-related files across Attune AI)
**Research Questions:** How should XML be used to enhance Claude Code tasks? What's working in Attune AI's implementation? Where are the gaps and opportunities?

---

## Key Findings

### Finding 1: XML remains a high-value technique for complex, multi-component prompts — but selectivity matters

**Evidence:** Anthropic's official docs state that XML tags "help Claude parse prompts more accurately, leading to higher-quality outputs" when prompts involve multiple components. Their 2026 blog update adds nuance: "Don't rely on outdated techniques: XML tags and heavy role prompting are less necessary with modern models. Start with explicit, clear instructions."

Attune AI's own metrics from v3.7.0 show strong gains for structured workflows:

| Metric | Plain Text | XML-Enhanced | Delta |
|--------|-----------|--------------|-------|
| Hallucinations | Baseline | -53% | Better |
| Instruction following | 87% | 96% | +9% |
| Output consistency | 79% | 94% | +15% |
| Parsing errors | 12% | 3% | -75% |

**Frequency:** Universal across Anthropic documentation and corroborated by Attune's internal measurements.

**Impact:** High — the 53% hallucination reduction directly affects code quality in security audits and reviews.

**Confidence:** High for complex multi-stage prompts. Medium for simple single-step tasks where overhead may not be justified.

---

### Finding 2: Attune AI has strong XML infrastructure but it's underutilized — only 53% of workflows converted

**Evidence:** The codebase has 8 core infrastructure files (PromptMixin, XmlPromptTemplate, XmlResponseParser, PromptService, registry, config, context, parser) totaling ~1,121 SLOC. However:

- 6 of ~17 workflows use XML prompts (security-audit, code-review, bug-predict, perf-audit, research-synthesis, release-prep)
- Only 1 of 100+ wizards uses XML
- XML is **disabled by default** (`config.get("enabled", False)`) — meaning new workflows won't use it unless explicitly configured
- 5 built-in templates exist in the registry; remaining workflows have no templates

The infrastructure is mature — defusedxml for security, graceful fallback to plain text, configuration hierarchy with per-workflow overrides — but adoption is bottlenecked by the opt-in default.

**Frequency:** Consistent finding across all component types.

**Impact:** High — unconverted workflows miss the hallucination and consistency gains.

**Confidence:** High — based on direct codebase analysis.

---

### Finding 3: The Claude 4.x literal instruction-following paradigm makes XML structure more valuable, not less

**Evidence:** When Sonnet 4.5 launched (September 2025), it "broke many existing prompts — not because it was buggy, but because Anthropic rebuilt how Claude follows instructions." Earlier versions inferred intent; Claude 4.x takes instructions literally. Simon Willison examined Claude's own system prompts and found sections wrapped in tags like `<behavior_instructions>`, `<artifacts_info>`, and `<knowledge_cutoff>`.

This means vague plain-text prompts are now more likely to produce unexpected results, while XML-structured prompts that explicitly separate role, goal, instructions, constraints, and output format are more reliably executed.

**Frequency:** Reported across multiple community analyses post-September 2025.

**Impact:** High — the shift to literal instruction following directly rewards structured prompts.

**Confidence:** High — well-documented behavioral change.

---

### Finding 4: XML-structured task decomposition is emerging as the standard for multi-agent orchestration

**Evidence:** Multiple projects now use XML or XML-like structured prompts for agent task decomposition:

- **Claude Code Agent Teams** (official Anthropic feature, early 2026): Opus 4.6 decomposes tasks into dependency graphs with `blockedBy`/`blocks` relationships
- **Claude Swarm**: Uses Opus 4.6 to decompose into dependency graphs with parallel execution
- **CC Mirror / "The Conductor"**: Pure task decomposition with blocking relationships and background execution
- **Attune AI's TASK_PROMPTS.md**: 10 real XML task prompts with `<task>`, `<context>`, `<files-to-create>`, `<files-to-modify>`, `<validation>`, `<risks>` structure

Attune's XML task prompt schema (from `xml-enhanced-prompts.md` rules file) is well-aligned with this ecosystem direction. The `<validation>` and `<risks>` sections are differentiators not seen in most community implementations.

**Frequency:** 4+ independent projects converging on similar patterns.

**Impact:** High — positions Attune AI for native integration with Claude Code's multi-agent features.

**Confidence:** High — multiple independent implementations.

---

### Finding 5: Critical gaps exist in measurement, schema validation, and streaming

**Evidence from internal analysis:**

| Gap | Current State | Impact |
|-----|---------------|--------|
| Performance benchmarks | No XML vs plain text speed/cost measurements | Cannot justify expansion with data |
| Token cost tracking | XML adds ~15-20% overhead; not measured | ROI unknown for each workflow |
| Schema validation | defusedxml used but no XSD/DTD validation | Malformed templates fail silently |
| Streaming responses | Full buffering required; no incremental parsing | Latency for long responses |
| Schema versioning | "1.0" exists; no "2.0" or migration path tested | Future evolution blocked |
| Cache hit metrics | Not tracked | Cannot verify caching benefits offset token overhead |

**Frequency:** Consistent across the infrastructure layer.

**Impact:** Medium — doesn't block current usage but blocks data-driven expansion decisions.

**Confidence:** High — verified through file-by-file analysis.

---

### Finding 6: Anthropic recommends combining XML with other techniques — Attune partially does this

**Evidence:** Anthropic's docs recommend combining XML with multishot prompting (`<examples>`), chain of thought (`<thinking>`, `<answer>`), and structured outputs. Their "power user tip" explicitly suggests this combination for "super-structured, high-performance prompts."

Attune AI's implementation uses XML for role/goal/instructions/constraints but does not currently:

- Embed `<examples>` sections with few-shot demonstrations inside XML prompts
- Use `<thinking>`/`<answer>` separation within XML-enhanced workflows
- Leverage Anthropic's new Structured Outputs API (late 2025) for guaranteed JSON schema conformance alongside XML prompts
- Use extended thinking directives within XML structure (Task 2.4 in TASK_PROMPTS.md plans this but it's unimplemented)

**Frequency:** Gap identified in all 6 converted workflows.

**Impact:** Medium-High — combining techniques could compound the existing gains.

**Confidence:** Medium — based on Anthropic's recommendations; actual improvement would need measurement.

---

### Finding 7: The XML response parsing layer is a competitive advantage worth expanding

**Evidence:** Attune's `XmlResponseParser` (parser.py, 285 lines) uses defusedxml and provides graceful fallback on parse failure. The built-in response format templates in `registry.py` define structured schemas for each workflow type (security findings with severity/CWE, code review with verdict, performance with 0-100 score).

This is more sophisticated than what most community projects implement. However:

- Only 5 response templates exist (security, code-review, research, bug-analysis, perf-audit)
- DocumentGenWorkflow may need a template but doesn't have one
- Wizard response parsing is available but rarely used (`enforce_xml_response=False` is the default)
- Partial response recovery is limited — if XML is malformed, the entire structured output is lost and raw text is returned

**Frequency:** Unique to Attune AI in the community projects surveyed.

**Impact:** High — structured response parsing is what makes XML a two-way contract, not just a one-way prompt format.

**Confidence:** High — based on direct code analysis.

---

### Finding 8: The Hooks + XML combination creates a powerful runtime safety layer

**Evidence:** Attune's `security_guard.py` PreToolUse hook (Task 2.1) demonstrates how XML-structured security policies can be enforced at runtime — blocking eval/exec and system directory writes before they execute. This pattern of "XML-defined policy → hook-enforced runtime check" is architecturally aligned with Claude Code's hook system.

The broader ecosystem shows hooks evolving rapidly: async hooks (January 2026), increased timeout to 10 minutes, and official support for PreToolUse/PostToolUse/SessionStart/Stop/PreCompact events. Attune's learning pipeline (Task 4.3: evaluate on Stop, inject patterns on SessionStart) further demonstrates the XML + hooks synergy.

**Frequency:** Unique to Attune AI's approach; hooks usage is common but XML-structured policy enforcement is not.

**Impact:** Medium — primarily a safety and quality benefit rather than a performance one.

**Confidence:** Medium — Task 2.1 and 4.3 are designed but implementation status unclear.

---

## Opportunity Areas

### Opportunity 1: Flip the default — enable XML by default for all workflows

The current `config.get("enabled", False)` default means every new workflow starts without XML. Given the measured gains (53% fewer hallucinations, +15% consistency), the default should be `True` with an opt-out for simple workflows.

**Tied to:** Finding 2 (underutilization), Finding 3 (literal instruction following rewards structure).

**Feasibility:** Low effort — single line change in `prompt_mixin.py:140-143`.

### Opportunity 2: Add benchmarking infrastructure for XML vs plain text

Before expanding XML to remaining workflows, establish measurement: token counts, latency, cost per workflow, hallucination rate. This data justifies the expansion and identifies workflows where XML overhead isn't worth it.

**Tied to:** Finding 5 (measurement gaps).

**Feasibility:** Medium effort — extend existing benchmarks in `benchmarks/` directory.

### Opportunity 3: Combine XML prompts with few-shot examples and structured outputs

Add `<examples>` sections to the 6 existing XML workflows showing ideal output for each workflow type. Investigate Anthropic's Structured Outputs API for guaranteed JSON conformance on the response side, complementing XML on the prompt side.

**Tied to:** Finding 6 (partial technique combination).

**Feasibility:** Medium effort per workflow — requires curating good examples.

### Opportunity 4: Create a "XML Prompt Cookbook" for the community

Attune AI has one of the most complete XML-enhanced prompt systems in the Claude Code ecosystem. The TASK_PROMPTS.md file with 10 real executed examples is unique. Packaging this as a shareable guide would establish thought leadership and attract contributors.

**Tied to:** User goal of sharing knowledge.

**Feasibility:** Low-Medium effort — much of the content already exists across docs/guides/xml-enhanced-prompts.md, TASK_PROMPTS.md, and the rules file.

### Opportunity 5: Extend XML task prompts for Agent Teams integration

With Claude Code's official Agent Teams feature and the ecosystem converging on dependency-graph task decomposition, Attune's `<task>` schema with `<dependencies>`, `<validation>`, and `<risks>` is well-positioned to generate task graphs that Agent Teams can execute natively.

**Tied to:** Finding 4 (multi-agent convergence).

**Feasibility:** Medium-High effort — requires integration with Agent Teams API.

---

## Recommendations

### Immediate (This Sprint)

1. **Change XML default to enabled** — flip `config.get("enabled", False)` to `True` in `prompt_mixin.py`. Add per-workflow opt-out for any workflow where XML is counterproductive. This single change captures the measured gains for all workflows.

2. **Add token counting to XML render** — instrument `_render_xml_prompt()` to log input token count alongside the existing workflow telemetry. This creates a baseline for cost analysis with zero workflow changes.

### Short-Term (Next 2-3 Weeks)

3. **Convert 5 highest-impact unconverted workflows to XML** — prioritize by usage frequency and error rates. Create registry templates for each. Target: 80%+ workflow XML coverage.

4. **Add `<examples>` sections to security-audit and code-review** — these are the most structurally complex workflows and would benefit most from few-shot demonstrations within the XML prompt.

5. **Create performance benchmark suite** — extend `benchmarks/` to compare XML vs plain text for the 6 converted workflows. Measure: tokens, latency, hallucination rate, output consistency.

### Medium-Term (Next Month)

6. **Draft the XML Prompt Cookbook** — consolidate existing docs into a shareable guide. Structure: Why XML → Schema Reference → 10 Real Examples → Best Practices → Performance Data.

7. **Investigate Structured Outputs API integration** — prototype using Anthropic's guaranteed JSON schema on the response side alongside XML on the prompt side. This could replace the custom XmlResponseParser for workflows that need strict output conformance.

8. **Prototype Agent Teams task generation** — use the `<task>` schema from TASK_PROMPTS.md to generate Claude Code Agent Teams-compatible task graphs with dependency chains.

---

## Open Questions

1. **What is the actual token cost delta?** The estimated 15-20% overhead from XML tags has not been measured. Is the hallucination reduction worth the cost increase per workflow?

2. **Do Claude 4.x models still need XML as much as 3.x did?** Anthropic's 2026 guidance says "XML tags and heavy role prompting are less necessary with modern models" — but Attune's metrics were measured on 3.x/early 4.x. Are the gains still this large on Opus 4.6?

3. **Should the response format use JSON Schema (Structured Outputs) instead of XML?** Anthropic now offers guaranteed JSON conformance. Is there a hybrid approach where prompts use XML but responses use Structured Outputs?

4. **How do XML prompts interact with extended thinking?** Task 2.4 plans to add extended thinking directives to XML workflows but the interaction between XML structure and thinking tokens is unexplored.

5. **What's the wizard conversion ROI?** With 100+ wizards and only 1 using XML, the conversion effort is large. Which wizard categories would benefit most?

---

## Sources

### Anthropic Official

- [Use XML tags to structure your prompts](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/use-xml-tags) — Anthropic API docs
- [Prompt engineering best practices](https://claude.com/blog/best-practices-for-prompt-engineering) — Claude blog, 2026 update
- [Prompt engineering overview](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview) — Anthropic docs
- [Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) — Anthropic developer platform
- [Create custom subagents](https://code.claude.com/docs/en/sub-agents) — Claude Code docs

### Community & Ecosystem

- [Claude Code Agent Teams and Opus 4.6](https://zircote.com/blog/2026/02/whats-new-in-claude-code-opus-4-6/) — zircote blog
- [Claude Code Multi-Agent Orchestration (open source)](https://www.theunwindai.com/p/claude-code-s-hidden-multi-agent-orchestration-now-open-source) — The Unwind AI
- [Claude Code Swarm Orchestration Skill](https://gist.github.com/kieranklaassen/4f2aba89594a4aea4ad64d753984b2ea) — GitHub Gist
- [Claude Code Tasks feature](https://venturebeat.com/orchestration/claude-codes-tasks-update-lets-agents-work-longer-and-coordinate-across/) — VentureBeat
- [Claude Prompt Engineering Best Practices 2026](https://promptbuilder.cc/blog/claude-prompt-engineering-best-practices-2026) — PromptBuilder
- [Claude Agent Skills Landing Guide](https://claudecn.com/en/blog/claude-agent-skills-landing-guide/) — Claude CN
- [Anthropic Structured Outputs announcement](https://ainativedev.io/news/anthropic-brings-structured-outputs-to-claude-developer-platform-making-api-responses-more-reliable) — AI Native Dev

### Internal (Attune AI)

- `docs/guides/xml-enhanced-prompts.md` — Implementation guide with performance metrics
- `docs/implementation/TASK_PROMPTS.md` — 10 real executed XML task prompts
- `.claude/rules/attune/xml-enhanced-prompts.md` — Schema reference and usage guidelines
- `src/attune/prompts/` — Core XML infrastructure (templates, registry, parser, config, context)
- `src/attune/workflows/prompt_mixin.py` — PromptMixin with `_render_xml_prompt()`
