/**
 * Canonical Feature List - Single Source of Truth
 *
 * All pages should import from here to ensure consistency.
 * Update counts and descriptions here when features change.
 */

// --- Products ---

export interface Product {
  id: string;
  name: string;
  pypiName: string;
  version: string;
  tagline: string;
  installCommand: string;
  description: string;
  features: string[];
}

export const PRODUCTS: Product[] = [
  {
    id: "attune-ai",
    name: "Attune AI",
    pypiName: "attune-ai",
    version: "5.10.0",
    tagline: "Generate, maintain, and serve help from your code",
    installCommand: "pip install attune-ai",
    description:
      "Full framework for bootstrapping a knowledge base from source code. " +
      "Scans your codebase, generates concept/task/reference templates, " +
      "detects when code drifts from docs, and regenerates stale content.",
    features: [
      "Bootstrap help from any codebase",
      "Generate concept, task, and reference templates",
      "Staleness detection via source hashing",
      "Auto-regeneration of stale templates",
      "14 Claude Code skills included",
      "MCP server with 5 help tools",
    ],
  },
  {
    id: "attune-help",
    name: "Attune Help",
    pypiName: "attune-help",
    version: "0.3.0",
    tagline: "Lightweight reader for help templates",
    installCommand: "pip install attune-help",
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
    version: "5.10.0",
    tagline: "Progressive help right in your terminal",
    installCommand:
      "claude plugin marketplace add Smart-AI-Memory/attune-ai",
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
      "14 additional skills (security, testing, review, etc.)",
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

// --- Legacy Capabilities (folded into docs) ---

export const LEGACY_CAPABILITIES = {
  wizards: 5,
  workflows: 17,
  agentTemplates: 14,
  compositionPatterns: 6,
} as const;

// --- Helpers ---

export function getPricingSummary(): string {
  return "Everything open source — Apache 2.0";
}

export function getHomepageFeatures(): Array<{
  icon: string;
  title: string;
  description: string;
}> {
  return PRODUCTS.map((p) => ({
    icon: p.id === "attune-ai" ? "🛠️" : p.id === "attune-help" ? "📖" : "⚡",
    title: p.name,
    description: p.tagline,
  }));
}
