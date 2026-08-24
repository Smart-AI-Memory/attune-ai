/**
 * Canonical Feature List - Single Source of Truth
 *
 * All pages should import from here to ensure consistency.
 * Update counts and descriptions here when features change.
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
    version: "14.1.0",
    tagline: "Generate, maintain, and serve help from your code",
    installCommand: "pip install attune-ai",
    marketplaceInstall:
      "claude plugin marketplace add Smart-AI-Memory/attune-ai",
    description:
      "Full framework for bootstrapping a knowledge base from source code. " +
      "Scans your codebase, generates concept/task/reference templates, " +
      "detects when code drifts from docs, and regenerates stale content.",
    features: [
      "Bootstrap help from any codebase",
      "Generate concept, task, and reference templates",
      "Staleness detection via source hashing",
      "Auto-regeneration of stale templates",
      "28 Claude Code skills included",
      "MCP server with 49 registered tools",
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
    version: "14.1.0",
    tagline: "Progressive help right in your terminal",
    installCommand:
      "claude plugin marketplace add Smart-AI-Memory/attune-ai",
    marketplaceInstall:
      "claude plugin install attune-ai@attune-ai",
    description:
      "Install from the Claude Code marketplace. Type /coach to get " +
      "progressive help on any topic. Init, status, maintain, and " +
      "update your help system without leaving the terminal.",
    features: [
      "/coach <topic> — progressive depth lookup",
      "/coach init — bootstrap .help/ for your project",
      "/coach status — check template freshness",
      "/coach maintain — regenerate stale templates",
      "Auto-triggers on natural language (help, explain, learn)",
      "28 auto-triggering skills (security, testing, review, etc.)",
    ],
  },
];

// --- Help System Model ---

export interface DepthLevel {
  level: number;
  type: string;
  description: string;
  color: string;
}

export const HELP_DEPTH_LEVELS: DepthLevel[] = [
  {
    level: 0,
    type: "Concept",
    description: "What is it? When to use it?",
    color: "blue",
  },
  {
    level: 1,
    type: "Task",
    description: "Step-by-step: how to do it",
    color: "green",
  },
  {
    level: 2,
    type: "Reference",
    description: "Full detail, edge cases, API",
    color: "purple",
  },
];

export interface LifecycleStep {
  step: number;
  name: string;
  verb: string;
  description: string;
  detail: string;
}

export const LIFECYCLE_STEPS: LifecycleStep[] = [
  {
    step: 1,
    name: "Bootstrap",
    verb: "Scan",
    description: "Scan your codebase and discover features",
    detail:
      "The scanner reads your project structure, finds modules, " +
      "classes, and functions. It proposes features with file " +
      "patterns, descriptions, and tags. You review and confirm.",
  },
  {
    step: 2,
    name: "Generate",
    verb: "Create",
    description: "AI creates templates from your source code",
    detail:
      "For each feature, three templates are generated: concept " +
      "(what is it?), task (how to use it), and reference (full " +
      "API detail). Content is extracted from actual source — " +
      "docstrings, class hierarchies, function signatures.",
  },
  {
    step: 3,
    name: "Serve",
    verb: "Deliver",
    description: "Progressive help via attune-help or /coach",
    detail:
      "Users get concept on first ask, task on repeat, reference " +
      "on third. The reader auto-advances depth. Works standalone " +
      "(attune-help), in Claude Code (/coach), or embedded in " +
      "your own tools.",
  },
  {
    step: 4,
    name: "Maintain",
    verb: "Refresh",
    description: "Detect drift and regenerate stale templates",
    detail:
      "Source file hashes are stored in template frontmatter. " +
      "When code changes, staleness detection finds which " +
      "features drifted. Regeneration updates only stale " +
      "templates — hand-written ones are preserved.",
  },
];

export interface Differentiator {
  title: string;
  description: string;
  icon: string;
}

export const DIFFERENTIATORS: Differentiator[] = [
  {
    title: "Rooted in Code",
    description:
      "Templates are generated from actual source — docstrings, " +
      "signatures, class hierarchies. Not wiki pages that drift.",
    icon: "🌱",
  },
  {
    title: "Progressive Depth",
    description:
      "Concept → task → reference. Each repeat goes deeper. " +
      "New topic resets to concept. No information overload.",
    icon: "📊",
  },
  {
    title: "Human-Enhanceable",
    description:
      "Edit generated templates or write from scratch. " +
      "Hand-written templates are preserved during regeneration.",
    icon: "✏️",
  },
  {
    title: "Auto-Freshness",
    description:
      "Source hashes detect when code changes. Stale templates " +
      "are flagged and regenerated. Docs can't drift silently.",
    icon: "🔄",
  },
];

// --- Capability counts (verified against Python registry) ---

/**
 * Counts that appear in prose and stat callouts across the
 * site. Verified against the live Python code per the
 * website-content-accuracy rule (last verified 2026-07-12,
 * attune-ai 10.4.0):
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
 *   templateKinds: attune.authoring.generator._ALL_TEMPLATE_NAMES length
 *   wizards: attune.wizards.list_wizards() length
 *
 * (agentTemplates / compositionPatterns were dropped 2026-06-11:
 * the registries they referenced no longer exist in that shape
 * and no page consumed them.)
 */
export const CAPABILITIES = {
  workflows: 21,
  skills: 28,
  mcpTools: 50,
  templateKinds: 15,
  wizards: 5,
} as const;

/**
 * @deprecated Use {@link CAPABILITIES} instead. Kept for
 * backward compatibility with any consumer that may still
 * import the old name.
 */
export const LEGACY_CAPABILITIES = CAPABILITIES;

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
      "23 workflows: review, tests, bug prediction, refactor.",
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
    ],
    icon: "🧠",
    color: "secondary",
  },
  // 10.6.0 multi-LLM wave (launch plan; wording aligned with the
  // shipped README "Multi-LLM collaboration" section).
  {
    id: "multi-llm",
    tag: "Multi-LLM",
    title: "Three AI agents, one project brain",
    description:
      "Claude Code, Codex, and Antigravity share the same project " +
      "memory, hand off work with git-verified packets, and give " +
      "each other second opinions on real diffs. The round table " +
      "lets them deliberate a question — you chair what gets " +
      "adopted.",
    points: [
      "Shared session memory via MCP — same tools in every agent",
      "Handoffs re-verified against the actual git tree on resume",
      "Cross-model review and deliberation — advisory; you decide",
    ],
    icon: "🤝",
    color: "accent",
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
      "23 workflows run teams of 2–6 Claude subagents to " +
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
      "your actual source. Mean faithfulness ≥ 0.97, CI-gated — drift " +
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

/** Icon used in homepage product cards for each product. */
const PRODUCT_ICONS: Record<string, string> = {
  "attune-ai": "🛠️",
  "attune-help": "📖",
  "claude-code-plugin": "⚡",
};

export function getHomepageFeatures(): Array<{
  icon: string;
  title: string;
  description: string;
}> {
  return PRODUCTS.map((p) => ({
    icon: PRODUCT_ICONS[p.id] ?? "📦",
    title: p.name,
    description: p.tagline,
  }));
}
