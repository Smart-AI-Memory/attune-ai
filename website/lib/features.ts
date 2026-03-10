/**
 * Canonical Feature List - Single Source of Truth
 *
 * All pages should import from here to ensure consistency.
 * Update counts and descriptions here when features change.
 */

export const FEATURE_COUNTS = {
  wizards: 5,
  workflows: 17,
  agentTemplates: 14,
  compositionPatterns: 6,
} as const;

export const COMPOSITION_PATTERNS = [
  'Sequential',
  'Parallel',
  'Debate',
  'Teaching',
  'Refinement',
  'Adaptive',
] as const;

export const AGENT_TEMPLATES = [
  'Test Coverage Analyzer',
  'Security Auditor',
  'Code Quality Reviewer',
  'Documentation Writer',
  'Performance Optimizer',
  'Architecture Analyst',
  'Refactoring Specialist',
  'Test Generator',
  'Test Validator',
  'Report Generator',
  'Documentation Analyst',
  'Information Synthesizer',
  'Code Simplifier',
  'General Purpose',
] as const;

export interface Feature {
  id: string;
  name: string;
  icon: string;
  benefitDescription: string;  // For homepage (what you get)
  technicalDescription: string; // For framework page (how it works)
  pricingDescription: string;   // For pricing page (what's included)
  isNew?: boolean;
  version?: string;
}

export const FEATURES: Feature[] = [
  {
    id: 'socratic-builder',
    name: 'Socratic Agent Builder',
    icon: '🎯',
    benefitDescription: 'Create custom agents through guided questions. Describe what you need, get production-ready agents.',
    technicalDescription: 'SocraticWorkflowBuilder guides you through clarifying questions to generate optimized agent configurations.',
    pricingDescription: 'Custom agent creation',
    isNew: true,
  },
  {
    id: 'workflows',
    name: '17 AI Workflows',
    icon: '⚡',
    benefitDescription: 'Security audit, code review, bug prediction, test generation, documentation, refactoring, dependency check, release prep, and more — all non-interactive, CI/CD-ready.',
    technicalDescription: '17 multi-stage pipelines with automatic tier escalation (Haiku → Sonnet → Opus). Structured JSON output. Run via CLI or CI/CD. Wizards wrap these same workflows in an interactive guided experience.',
    pricingDescription: '17 AI workflows (CLI + CI/CD)',
  },
  {
    id: 'agent-templates',
    name: '14 Agent Templates + 6 Patterns',
    icon: '🤖',
    benefitDescription: 'Pre-built agents you can compose with Sequential, Parallel, Debate, Teaching, Refinement, or Adaptive patterns.',
    technicalDescription: '14 agents including test coverage, security, code quality, docs, performance, architecture, refactoring, synthesis, and more. 6 composition strategies.',
    pricingDescription: '14 agent templates, 6 composition patterns',
  },
  {
    id: 'wizards',
    name: '5 Smart Wizards',
    icon: '🧙',
    benefitDescription: 'Debug, refactor, release prep, security audit, and test generation — guided interactive AI assistance.',
    technicalDescription: 'WizardRegistry with 5 built-in wizards: debug, refactor, release-prep, security, and test-gen. Custom wizards can be added via the registry.',
    pricingDescription: '5 smart wizards',
  },
  {
    id: 'model-routing',
    name: 'Smart Model Routing',
    icon: '💰',
    benefitDescription: '80-96% cost reduction. The right model for each task automatically.',
    technicalDescription: 'Intelligent routing: Haiku for simple tasks, Sonnet for code, Opus for architecture decisions.',
    pricingDescription: 'Cost-optimized model routing',
  },
  {
    id: 'memory',
    name: 'Shared Agent State (Redis)',
    icon: '🧠',
    benefitDescription: 'Coordinate multiple Claude Code instances simultaneously. Shared wizard context, parallel agent execution, and cross-session telemetry — capabilities native Claude Code memory cannot provide.',
    technicalDescription: 'attune-redis plugin provides shared state across concurrent Claude Code instances. Distinct from per-developer auto-memory: enables team coordination, parallel wizard execution, and cross-project telemetry rollups.',
    pricingDescription: 'Redis shared agent state (optional plugin)',
  },
  {
    id: 'security',
    name: 'Enterprise Security',
    icon: '🔒',
    benefitDescription: 'Built-in PII scrubbing, secrets detection, and audit logging.',
    technicalDescription: 'Security scanner, PII detection, audit trails. SOC2 and HIPAA-ready controls.',
    pricingDescription: 'Enterprise security features',
  },
  {
    id: 'meta-orchestration',
    name: 'Meta-Orchestration',
    icon: '🧭',
    benefitDescription: 'Agents compose themselves. Describe a goal, get an optimized multi-agent team.',
    technicalDescription: 'MetaOrchestrator analyzes tasks and automatically selects composition patterns and agent configurations.',
    pricingDescription: 'Auto-composing agent teams',
    version: 'v3.3.0',
  },
  {
    id: 'prompt-caching',
    name: 'Automatic Prompt Caching',
    icon: '⚡',
    benefitDescription: "Anthropic's built-in prompt caching reduces cached token costs by up to 90%. Attune's Claude-native architecture maximizes cache hit rates automatically.",
    technicalDescription: 'Claude-native architecture designed around prompt caching. System prompts, tool definitions, and conversation history are automatically cached and reused.',
    pricingDescription: 'Anthropic prompt caching (up to 90% on cached tokens)',
    isNew: true,
  },
  {
    id: 'semantic-caching',
    name: 'Semantic Caching',
    icon: '🧲',
    benefitDescription: 'Detects similar prompts and reuses cached responses, avoiding redundant API calls entirely. ~57% hit rate measured.',
    technicalDescription: 'HybridCache with sentence-transformers computes embeddings for semantic similarity matching (95%+ cosine threshold). Hash-only fallback when ML deps unavailable.',
    pricingDescription: 'Semantic caching via sentence-transformers',
    isNew: true,
    version: 'v3.3.0',
  },
];

// Helper to get summary for pricing
export function getPricingSummary(): string {
  return `${FEATURE_COUNTS.wizards} smart wizards + ${FEATURE_COUNTS.workflows} workflows`;
}

// Helper to get features for homepage (benefit-focused)
export function getHomepageFeatures(): Array<{ icon: string; title: string; description: string }> {
  return FEATURES.slice(0, 8).map(f => ({
    icon: f.icon,
    title: f.name,
    description: f.benefitDescription,
  }));
}
