export interface Wizard {
  name: string;
  displayName: string;
  description: string;
  longDescription: string;
  tier: 'cheap' | 'capable' | 'premium';
  domain: string;
  keywords: string[];
  cliExample: string;
}

export const wizards: Wizard[] = [
  {
    name: 'security-audit',
    displayName: 'Security Audit',
    description:
      'Analyze code for security vulnerabilities, injection risks, and compliance issues',
    longDescription:
      'Performs a comprehensive security analysis of your codebase, identifying OWASP Top 10 vulnerabilities, injection risks (SQL, XSS, command injection), insecure dependencies, hardcoded secrets, and compliance gaps. Returns a prioritized list of issues with fix recommendations.',
    tier: 'capable',
    domain: 'Security',
    keywords: ['security', 'vulnerability', 'injection', 'xss', 'sql', 'owasp'],
    cliExample: 'attune wizard run security-audit',
  },
  {
    name: 'code-review',
    displayName: 'Code Review',
    description:
      'Review code for quality, best practices, maintainability, and potential bugs',
    longDescription:
      'Provides an expert-level code review covering code quality, adherence to best practices, maintainability, naming conventions, potential bugs, and architectural concerns. Supports Python, TypeScript, JavaScript, Go, and more.',
    tier: 'capable',
    domain: 'Quality',
    keywords: ['review', 'quality', 'lint', 'style', 'best practice', 'refactor'],
    cliExample: 'attune wizard run code-review',
  },
  {
    name: 'bug-predict',
    displayName: 'Bug Prediction',
    description: 'Predict potential bugs based on code patterns and historical data',
    longDescription:
      'Analyzes your codebase for common bug patterns — null pointer dereferences, off-by-one errors, race conditions, resource leaks, and more — before they become production incidents. Outputs a risk-ranked list with explanations.',
    tier: 'capable',
    domain: 'Debugging',
    keywords: ['bug', 'error', 'exception', 'fail', 'fix', 'defect'],
    cliExample: 'attune wizard run bug-predict',
  },
  {
    name: 'perf-audit',
    displayName: 'Performance Audit',
    description:
      'Analyze code for performance issues, bottlenecks, and optimization opportunities',
    longDescription:
      'Identifies performance bottlenecks in your code: N+1 queries, missing caching opportunities, inefficient data structures, large list copies, and slow algorithm choices. Provides concrete optimization recommendations.',
    tier: 'capable',
    domain: 'Performance',
    keywords: ['performance', 'slow', 'optimize', 'bottleneck', 'memory', 'cpu'],
    cliExample: 'attune wizard run perf-audit',
  },
  {
    name: 'refactor-plan',
    displayName: 'Refactor Plan',
    description: 'Plan code refactoring to improve structure and reduce complexity',
    longDescription:
      'Analyzes your code architecture and produces a phased refactoring plan that reduces complexity, improves cohesion, and sets you up for future maintainability. Identifies dead code, duplicate logic, and over-engineered abstractions.',
    tier: 'capable',
    domain: 'Architecture',
    keywords: ['refactor', 'restructure', 'simplify', 'complexity', 'design'],
    cliExample: 'attune wizard run refactor-plan',
  },
  {
    name: 'test-gen',
    displayName: 'Test Generation',
    description: 'Generate test cases and improve test coverage automatically',
    longDescription:
      'Generates comprehensive test suites for your functions and classes: unit tests, edge cases, error paths, and integration scenarios. Outputs pytest-compatible Python tests or Jest tests for TypeScript/JavaScript.',
    tier: 'cheap',
    domain: 'Testing',
    keywords: ['test', 'unit', 'integration', 'coverage', 'pytest', 'mock'],
    cliExample: 'attune wizard run test-gen',
  },
  {
    name: 'doc-gen',
    displayName: 'Documentation',
    description:
      'Generate documentation from code including API docs, READMEs, and guides',
    longDescription:
      'Reads your source code and generates accurate, structured documentation: docstrings, API reference pages, README files, and usage guides. Keeps your docs in sync with the actual implementation.',
    tier: 'cheap',
    domain: 'Documentation',
    keywords: ['document', 'readme', 'api', 'docstring', 'explain'],
    cliExample: 'attune wizard run doc-gen',
  },
  {
    name: 'dependency-check',
    displayName: 'Dependency Check',
    description:
      'Audit dependencies for vulnerabilities, updates, and license issues',
    longDescription:
      'Audits your project dependencies for known CVEs, outdated packages, breaking-change upgrade paths, and license compatibility issues. Works with pip, npm, and poetry. Outputs a prioritized remediation plan.',
    tier: 'cheap',
    domain: 'Dependencies',
    keywords: ['dependency', 'package', 'npm', 'pip', 'vulnerability', 'update'],
    cliExample: 'attune wizard run dependency-check',
  },
  {
    name: 'release-prep',
    displayName: 'Release Prep',
    description:
      'Pre-release quality gate with health checks, security scan, and changelog',
    longDescription:
      'Runs a full pre-release checklist: test coverage check, security scan, dependency audit, changelog generation, and version bump validation. Acts as your automated release gatekeeper before you push to production.',
    tier: 'capable',
    domain: 'Release',
    keywords: ['release', 'deploy', 'publish', 'version', 'changelog', 'production'],
    cliExample: 'attune wizard run release-prep',
  },
  {
    name: 'research',
    displayName: 'Research',
    description: 'Research and synthesize information from multiple sources',
    longDescription:
      'Investigates a technical topic, library, or architectural decision and synthesizes findings into a structured report with pros/cons, recommendations, and references. Ideal for technology evaluations and architecture decisions.',
    tier: 'capable',
    domain: 'Research',
    keywords: ['research', 'investigate', 'explore', 'analyze', 'study'],
    cliExample: 'attune wizard run research',
  },
];

export const tierColors: Record<string, string> = {
  cheap: 'bg-green-100 text-green-800 border-green-200',
  capable: 'bg-blue-100 text-blue-800 border-blue-200',
  premium: 'bg-purple-100 text-purple-800 border-purple-200',
};

export const tierLabels: Record<string, string> = {
  cheap: 'Fast & Affordable',
  capable: 'Balanced',
  premium: 'Most Capable',
};

export function getWizardByName(name: string): Wizard | undefined {
  return wizards.find((w) => w.name === name);
}
