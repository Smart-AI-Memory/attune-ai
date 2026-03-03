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
    name: 'debug',
    displayName: 'Debugging',
    description:
      'Guided error investigation and fix planning',
    longDescription:
      'Walks you through debugging step by step: reproduce the error, isolate the root cause, and plan a fix. Asks targeted questions about symptoms, recent changes, and expected behavior to narrow down the issue efficiently.',
    tier: 'capable',
    domain: 'Development',
    keywords: ['debug', 'error', 'bug', 'fix', 'investigate', 'troubleshoot'],
    cliExample: 'attune wizard run debug',
  },
  {
    name: 'refactor',
    displayName: 'Refactoring',
    description:
      'Plan safe, incremental code refactoring',
    longDescription:
      'Analyzes your code architecture and produces a phased refactoring plan that reduces complexity, improves cohesion, and sets you up for future maintainability. Identifies dead code, duplicate logic, and over-engineered abstractions.',
    tier: 'capable',
    domain: 'Development',
    keywords: ['refactor', 'restructure', 'simplify', 'complexity', 'design'],
    cliExample: 'attune wizard run refactor',
  },
  {
    name: 'release-prep',
    displayName: 'Release Prep',
    description:
      'Guided release readiness check and preparation',
    longDescription:
      'Runs a full pre-release checklist: test coverage check, security scan, dependency audit, changelog generation, and version bump validation. Acts as your automated release gatekeeper before you push to production.',
    tier: 'capable',
    domain: 'Release',
    keywords: ['release', 'deploy', 'publish', 'version', 'changelog', 'production'],
    cliExample: 'attune wizard run release-prep',
  },
  {
    name: 'security',
    displayName: 'Security Audit',
    description:
      'Guided security vulnerability scanning and remediation',
    longDescription:
      'Performs a comprehensive security analysis of your codebase, identifying OWASP Top 10 vulnerabilities, injection risks (SQL, XSS, command injection), insecure dependencies, hardcoded secrets, and compliance gaps. Returns a prioritized list of issues with fix recommendations.',
    tier: 'capable',
    domain: 'Security',
    keywords: ['security', 'vulnerability', 'injection', 'xss', 'sql', 'owasp'],
    cliExample: 'attune wizard run security',
  },
  {
    name: 'test-gen',
    displayName: 'Test Generation',
    description: 'Generate behavioral tests for a module or file',
    longDescription:
      'Generates comprehensive test suites for your functions and classes: unit tests, edge cases, error paths, and integration scenarios. Outputs pytest-compatible Python tests with proper mocking and fixtures.',
    tier: 'cheap',
    domain: 'Testing',
    keywords: ['test', 'unit', 'integration', 'coverage', 'pytest', 'mock'],
    cliExample: 'attune wizard run test-gen',
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
