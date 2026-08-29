/**
 * Canonical Feature List - Single Source of Truth
 *
 * All pages should import from here to ensure consistency.
 * Update counts and descriptions here when features change.
 *
 * PRODUCTS is unrendered but load-bearing: its pypiName/version
 * pairs are the version-sync anchor parsed by
 * scripts/audit_website_versions.py and
 * tests/unit/test_website_version_accuracy.py. Positioning copy
 * follows DEC-10..14
 * (docs/specs/product-direction-review/positioning-2026-08-29.md).
 *
 * Marketplace mapping (consolidated 2026-06-22, retiring the
 * 2026-04-10 attune-docs split): both plugins live in the single
 * Smart-AI-Memory/attune-ai marketplace.
 *   attune-ai   → Smart-AI-Memory/attune-ai marketplace
 *   attune-help → Smart-AI-Memory/attune-ai marketplace
 * (attune-author retired 2026-07: its authoring capabilities were
 * consolidated into attune-ai, the PyPI package is archived, and
 * the marketplace plugin was removed — see the docs page FAQ.)
 */

// --- Capability counts (verified against Python registry) ---

/**
 * Counts that appear in prose and stat callouts across the
 * site — the single source of truth. Interpolate these into
 * copy; never hard-code a count in a page or a prose string.
 * Verified against the live Python code per the
 * website-content-accuracy rule (last verified 2026-08-25,
 * attune-ai 15.0.0):
 *
 *   workflows: distinct classes in attune.workflows.discover_workflows()
 *     (D4, claim-drift-gates, 2026-07-12: the prior count used
 *     list_workflows() filtered on a truthy `stages` field, which is
 *     set on nearly every workflow — only 3 actually declare more than
 *     one stage. "Multi-stage workflows" overclaimed what the number
 *     measured; this is the honest distinct-workflow-class total.
 *     release-prep/release-gate count once — deliberate alias pair.)
 *   skills: plugin/skills/ directory count (test_skill_count)
 *   mcpTools: attune.mcp.tool_schemas get_*_tools() total
 *   templateKinds: attune.authoring.generator._ALL_TEMPLATE_NAMES
 *     length (moved from the retired attune_author package)
 *   wizards: attune.wizards.list_wizards() length
 */
export const CAPABILITIES = {
  workflows: 21,
  skills: 28,
  mcpTools: 48,
  templateKinds: 15,
  wizards: 5,
} as const;

/**
 * Homepage proof metrics — each one names its verifiable source.
 * See /benchmarks for the methodology behind each number.
 *
 *   testsFloor: the README badge's round floor ("25,000+ passing"),
 *     freshness-guarded by scripts/check_badge_freshness.py in CI —
 *     it fails the build if actual collected tests fall below the
 *     floor or exceed it by more than the margin.
 *   coverageFloorPct: the CI coverage RATCHET — the
 *     `--cov-fail-under` value in tests.yml's coverage job (a
 *     raise-only valve; the authoritative merge gate). Displayed
 *     as "NN%+": actual coverage sits at or above it by
 *     construction, so the claim needs no freshness script.
 *     Drift-guarded: test_coverage_floor_matches_ci_gate fails if
 *     this number diverges from the workflow's gate (bump both
 *     together when the ratchet rises). pyproject's fail_under=85
 *     and the codecov 85% targets are looser secondary floors —
 *     not this number.
 *   ragFaithfulness: attune-rag's measured MEAN faithfulness (40-query
 *     golden set, N=20 runs). The CI regression gate is locked at
 *     ≥ 0.9686 — say "mean 0.97, CI-gated", never "gated at ≥ 0.97".
 */
export const METRICS = {
  testsFloor: "25,000+",
  coverageFloorPct: 94,
  ragFaithfulness: "0.97",
} as const;

// --- Products ---

export interface Product {
  id: string;
  name: string;
  pypiName: string;
  version: string;
  tagline: string;
  installCommand: string;
  /** Claude Code marketplace installation (if applicable). */
  marketplaceInstall?: string;
  description: string;
  features: string[];
}

export const PRODUCTS: Product[] = [
  {
    id: "attune-ai",
    name: "Attune AI",
    pypiName: "attune-ai",
    version: "16.1.0",
    tagline:
      "Persistent memory and receipt-verified workflows for Claude Code",
    installCommand: "pip install attune-ai",
    marketplaceInstall:
      "claude plugin marketplace add Smart-AI-Memory/attune-ai",
    description:
      "Your agent stops starting from zero and its word stops being the " +
      "evidence. A stash → recall → promote loop carries decisions, bugs, " +
      "and lessons across sessions; workflows verify their claims with " +
      "independently re-run probes; interactive forms replace walls of " +
      "prose at every fork.",
    features: [
      "Cross-session memory: stash on stop, recall at the door, promote what endures",
      "Your memory is git-tracked files in your repo — served to Claude Code, Codex, or Antigravity alike",
      "Fix Receipts (attune fix): probes re-run independently of the agent's claim",
      "Decision, pushback, and progress forms — one tap each",
      `${CAPABILITIES.workflows} multi-agent workflows with cost-tiered routing`,
      `One MCP server, ${CAPABILITIES.mcpTools} core tools`,
    ],
  },
  {
    id: "attune-help",
    name: "Attune Help",
    pypiName: "attune-help",
    version: "0.13.0",
    tagline: "Lightweight reader for help templates",
    installCommand: "pip install attune-help",
    marketplaceInstall:
      "claude plugin install attune-help@attune-ai",
    description:
      "Standalone reader with just 1 dependency. Loads templates, " +
      "provides progressive depth (concept → task → reference), " +
      "session tracking, and multiple renderers. 6 files, no bloat.",
    features: [
      "1 dependency (python-frontmatter)",
      "Progressive depth auto-advancement",
      "Session storage (file or custom backend)",
      "Renderers: plain, CLI, Claude Code, marketplace",
      "Precursor warnings for files being edited",
      "Embeddable in any Python tool",
    ],
  },
  {
    id: "claude-code-plugin",
    name: "Claude Code Plugin",
    pypiName: "attune-ai",
    version: "16.1.0",
    tagline: "Skills, hooks, and forms on your Claude subscription",
    installCommand:
      "claude plugin marketplace add Smart-AI-Memory/attune-ai",
    marketplaceInstall:
      "claude plugin install attune-ai@attune-ai",
    description:
      "Install as a Claude Code plugin (this repo doubles as the " +
      "plugin marketplace source). Skills trigger from natural " +
      "language, security hooks guard every tool call, and " +
      "interactive forms structure the agent's questions — no API " +
      "key, no extra charge.",
    features: [
      `${CAPABILITIES.skills} auto-triggering skills (security, testing, review, memory)`,
      "Security hooks: eval/exec blocking, path validation",
      "Decision, pushback, and progress forms at every fork",
      '"what can attune do?" — Socratic discovery entry point',
      "/coach <topic> — progressive-depth help",
      "Runs on your Claude subscription — no API credits needed",
    ],
  },
];

// --- Platform positioning (spec-driven dev) ---

/**
 * The five-stage reliability loop — the narrative spine of the
 * homepage. Maps requirement → shipped without losing the thread.
 */
export interface LoopStage {
  n: string;
  name: string;
  description: string;
}

export const RELIABILITY_LOOP: LoopStage[] = [
  {
    n: "01",
    name: "Specify",
    description:
      "Socratic spec engine: requirements, design, and tasks with an approval gate.",
  },
  {
    n: "02",
    name: "Ground",
    description:
      "RAG retrieval cites your code so the agent doesn't invent APIs.",
  },
  {
    n: "03",
    name: "Build",
    description:
      `${CAPABILITIES.workflows} workflows: review, tests, bug prediction, refactor.`,
  },
  {
    n: "04",
    name: "Remember",
    description:
      "Cross-session memory and a lessons corpus surface what worked before.",
  },
  {
    n: "05",
    name: "Verify",
    description:
      "Fact-check generated content: imports, flags, links, counts — all real.",
  },
];

/**
 * The four platform pillars. Each maps to a real, shipped
 * capability — verified against the live registry, no roadmap
 * fiction (see website-content-accuracy rule). `color` selects a
 * brand token: primary (action), secondary (knowledge), accent (AI).
 */
export interface Pillar {
  id: string;
  tag: string;
  title: string;
  description: string;
  points: string[];
  icon: string;
  color: "primary" | "secondary" | "accent";
}

export const PILLARS: Pillar[] = [
  // DEC-3 (product-direction-review): memory is THE pillar — it
  // stays first; the rest are supporting capabilities.
  {
    id: "memory",
    tag: "Project memory",
    title: "Your agent stops starting from zero",
    description:
      "Findings from each session are stashed and recalled in the next. " +
      "A retrievable lessons corpus surfaces the right engineering lesson " +
      "at the moment a prompt needs it.",
    points: [
      "Local-first by default — no cloud required",
      "Redis semantic tier, client included (local Ollama embeddings)",
      "Automatic recall, or on demand with /recall",
      // DEC-13/14: cross-provider portability is a property of the
      // memory, not a separate pillar — anti-lock-in framing, exactly
      // the three verified providers.
      "Git-tracked files in your repo — served to Claude Code, Codex, or Antigravity alike. Switch agents; keep everything.",
    ],
    icon: "🧠",
    color: "secondary",
  },
  {
    id: "communication",
    tag: "Dynamic forms",
    title: "Forms that improve how you and the AI talk",
    description:
      "Attune improves human/AI communication by dynamically using " +
      "interactive forms: instead of a fixed wall of prose, it renders " +
      "the right form in response to your prompt whenever a structured " +
      "turn communicates better than text. A multi-part question " +
      "becomes one click; a recommendation arrives as weighable cards; " +
      "a disagreement is shown side-by-side so you overrule it in one " +
      "tap.",
    points: [
      "Intake, decision, and pushback fire at a fork; progress reports status",
      "Rich on widget surfaces, graceful menu fallback elsewhere",
      "Answer with one click — or the terse y / go / 1 vocab",
    ],
    icon: "💬",
    color: "primary",
  },
  {
    id: "workflows",
    tag: "AI workflows",
    title: "Specialist teams, not one prompt",
    description:
      `${CAPABILITIES.workflows} workflows run teams of 2–6 Claude subagents to ` +
      "review code, surface vulnerabilities, generate tests, and plan " +
      "refactors — with cost-tiered model routing.",
    points: [
      "Security audit, code review, bug prediction, release prep",
      "Cheap / capable / premium model routing",
      "Structured, readable reports",
    ],
    icon: "⚙️",
    color: "primary",
  },
  {
    id: "grounding",
    tag: "Retrieval grounding",
    title: "Answers anchored to your code",
    description:
      "Keyword + semantic retrieval keeps generated content grounded in " +
      "your actual source. Mean faithfulness 0.97, CI-gated — drift " +
      "fails the build.",
    points: [
      "Powered by attune-rag — built in, no extra install",
      "Citations back to source",
      "Faithfulness measured, not assumed",
    ],
    icon: "🔎",
    color: "secondary",
  },
  {
    id: "verification",
    tag: "Verification",
    title: "Catch hallucinations before they ship",
    description:
      "Fact-check LLM output against source-of-truth: confirm imports " +
      "import, CLI flags are real, links resolve, and counts match — " +
      "before the change reaches main.",
    points: [
      "Verifies docs, code, and generated content",
      "Closes the loop the spec opened",
      // DEC-14: cross-model review/deliberation live under the
      // receipts culture, not a standalone multi-LLM pillar.
      "Cross-model review and roundtable deliberation — advisory; you decide",
      "Built from the discipline that runs this project",
    ],
    icon: "✅",
    color: "accent",
  },
];

// --- Helpers ---

export function getPricingSummary(): string {
  return "Everything open source — Apache 2.0";
}
