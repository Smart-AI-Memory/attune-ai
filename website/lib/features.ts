/**
 * Canonical Feature List - Single Source of Truth
 *
 * All pages should import from here to ensure consistency.
 * Update counts and descriptions here when features change.
 */

export const FEATURE_COUNTS = {
  wizards: 10,
  workflows: 14,
  agentTemplates: 7,
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
  'Test Coverage',
  'Security',
  'Code Quality',
  'Documentation',
  'Performance',
  'Architecture',
  'Refactoring',
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
    name: '12 Integrated Workflows',
    icon: '⚡',
    benefitDescription: 'Research, code review, debugging, refactoring, test generation, documentation, security scanning, and more.',
    technicalDescription: '10 base workflows + 4 meta-workflows for release prep, test coverage, test maintenance, and documentation.',
    pricingDescription: '14 integrated workflows',
  },
  {
    id: 'agent-templates',
    name: '7 Agent Templates + 6 Patterns',
    icon: '🤖',
    benefitDescription: 'Pre-built agents you can compose with Sequential, Parallel, Debate, Teaching, Refinement, or Adaptive patterns.',
    technicalDescription: 'Agents for test coverage, security, code quality, docs, performance, architecture, and refactoring. 6 composition strategies.',
    pricingDescription: '7 agent templates, 6 composition patterns',
  },
  {
    id: 'wizards',
    name: '10 Smart Wizards',
    icon: '🧙',
    benefitDescription: 'Security audit, code review, bug prediction, performance analysis, and more—domain-specific AI assistance.',
    technicalDescription: 'WizardRegistry with 10+ wizards including security, refactoring, test generation, documentation, and research.',
    pricingDescription: '10 smart wizards',
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
    name: 'Persistent Memory System',
    icon: '🧠',
    benefitDescription: 'Short-term Redis memory for agent coordination during workflows. Long-term MemDocs storage remembers your coding patterns, past decisions, and project context across sessions.',
    technicalDescription: 'Two-tier memory: Redis for real-time agent coordination, MemDocs for persistent cross-session storage with semantic search.',
    pricingDescription: 'Persistent memory system',
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
    benefitDescription: 'Up to 90% cost savings on API tokens via Anthropic auto-caching. Zero configuration required.',
    technicalDescription: 'Claude-native architecture designed around prompt caching. System prompts, tool definitions, and conversation history are automatically cached and reused.',
    pricingDescription: 'Automatic prompt caching (90% savings)',
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
