import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';

const wizards = [
  {
    name: 'security-audit',
    displayName: 'Security Audit',
    description: 'Analyze code for security vulnerabilities, injection risks, and compliance issues',
    tier: 'capable',
    domain: 'Security',
    keywords: ['security', 'vulnerability', 'injection', 'xss', 'sql', 'owasp'],
  },
  {
    name: 'code-review',
    displayName: 'Code Review',
    description: 'Review code for quality, best practices, maintainability, and potential bugs',
    tier: 'capable',
    domain: 'Quality',
    keywords: ['review', 'quality', 'lint', 'style', 'best practice', 'refactor'],
  },
  {
    name: 'bug-predict',
    displayName: 'Bug Prediction',
    description: 'Predict potential bugs based on code patterns and historical data',
    tier: 'capable',
    domain: 'Debugging',
    keywords: ['bug', 'error', 'exception', 'fail', 'fix', 'defect'],
  },
  {
    name: 'perf-audit',
    displayName: 'Performance Audit',
    description: 'Analyze code for performance issues, bottlenecks, and optimization opportunities',
    tier: 'capable',
    domain: 'Performance',
    keywords: ['performance', 'slow', 'optimize', 'bottleneck', 'memory', 'cpu'],
  },
  {
    name: 'refactor-plan',
    displayName: 'Refactor Plan',
    description: 'Plan code refactoring to improve structure and reduce complexity',
    tier: 'capable',
    domain: 'Architecture',
    keywords: ['refactor', 'restructure', 'simplify', 'complexity', 'design'],
  },
  {
    name: 'test-gen',
    displayName: 'Test Generation',
    description: 'Generate test cases and improve test coverage automatically',
    tier: 'cheap',
    domain: 'Testing',
    keywords: ['test', 'unit', 'integration', 'coverage', 'pytest', 'mock'],
  },
  {
    name: 'doc-gen',
    displayName: 'Documentation',
    description: 'Generate documentation from code including API docs, READMEs, and guides',
    tier: 'cheap',
    domain: 'Documentation',
    keywords: ['document', 'readme', 'api', 'docstring', 'explain'],
  },
  {
    name: 'dependency-check',
    displayName: 'Dependency Check',
    description: 'Audit dependencies for vulnerabilities, updates, and license issues',
    tier: 'cheap',
    domain: 'Dependencies',
    keywords: ['dependency', 'package', 'npm', 'pip', 'vulnerability', 'update'],
  },
  {
    name: 'release-prep',
    displayName: 'Release Prep',
    description: 'Pre-release quality gate with health checks, security scan, and changelog',
    tier: 'capable',
    domain: 'Release',
    keywords: ['release', 'deploy', 'publish', 'version', 'changelog', 'production'],
  },
  {
    name: 'research',
    displayName: 'Research',
    description: 'Research and synthesize information from multiple sources',
    tier: 'capable',
    domain: 'Research',
    keywords: ['research', 'investigate', 'explore', 'analyze', 'study'],
  },
];

const tierColors = {
  cheap: 'bg-green-100 text-green-800 border-green-200',
  capable: 'bg-blue-100 text-blue-800 border-blue-200',
  premium: 'bg-purple-100 text-purple-800 border-purple-200',
};

const tierLabels = {
  cheap: 'Fast & Affordable',
  capable: 'Balanced',
  premium: 'Most Capable',
};

export default function WizardsPage() {
  return (
    <>
      <Navigation />
      <main className="min-h-screen pt-16">
        {/* Hero */}
        <section className="py-16 sm:py-20 bg-gradient-to-b from-[var(--border)] to-transparent">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h1 className="text-4xl sm:text-5xl font-bold mb-6">
                10 Smart Wizards
              </h1>
              <p className="text-xl text-[var(--text-secondary)] mb-8">
                Specialized AI agents that understand your codebase.
                Each wizard is optimized for specific tasks with built-in best practices.
              </p>
              <div className="flex flex-wrap gap-4 justify-center">
                <Link
                  href="/framework-docs/guides/wizards-getting-started/"
                  className="btn btn-primary"
                >
                  Getting Started Guide
                </Link>
                <Link
                  href="/framework-docs/guides/wizard-architecture/"
                  className="btn btn-outline"
                >
                  Architecture
                </Link>
                <Link
                  href="/framework-docs/guides/wizard-custom-development/"
                  className="btn btn-outline"
                >
                  Build Your Own
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* Tier Legend */}
        <section className="py-8 border-b border-[var(--border)]">
          <div className="container">
            <div className="flex flex-wrap gap-6 justify-center items-center">
              <span className="text-sm text-[var(--muted)]">Model Tiers:</span>
              {Object.entries(tierLabels).map(([tier, label]) => (
                <div key={tier} className="flex items-center gap-2">
                  <span className={`px-2 py-1 text-xs font-medium rounded border ${tierColors[tier as keyof typeof tierColors]}`}>
                    {tier}
                  </span>
                  <span className="text-sm text-[var(--text-secondary)]">{label}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Wizards Grid */}
        <section className="py-16">
          <div className="container">
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
              {wizards.map((wizard) => (
                <div
                  key={wizard.name}
                  className="bg-[var(--background)] p-6 rounded-xl border-2 border-[var(--border)] hover:border-[var(--primary)] hover:shadow-lg transition-all"
                >
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <h3 className="font-bold text-xl">{wizard.displayName}</h3>
                    <span className={`flex-shrink-0 px-2 py-1 text-xs font-medium rounded border ${tierColors[wizard.tier as keyof typeof tierColors]}`}>
                      {wizard.tier}
                    </span>
                  </div>
                  <p className="text-[var(--text-secondary)] mb-4">
                    {wizard.description}
                  </p>
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-[var(--muted)]">Domain:</span>
                    <span className="font-medium">{wizard.domain}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Usage Example */}
        <section className="py-16 bg-[var(--border)] bg-opacity-30">
          <div className="container">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl sm:text-3xl font-bold text-center mb-8">
                Run Wizards via CLI
              </h2>
              <div className="bg-[#1e1e1e] rounded-xl overflow-hidden shadow-2xl">
                <div className="flex items-center gap-2 px-4 py-3 bg-[#2d2d2d] border-b border-[#3d3d3d]">
                  <div className="w-3 h-3 rounded-full bg-[#ff5f56]"></div>
                  <div className="w-3 h-3 rounded-full bg-[#ffbd2e]"></div>
                  <div className="w-3 h-3 rounded-full bg-[#27ca40]"></div>
                  <span className="ml-2 text-sm text-gray-400">terminal</span>
                </div>
                <pre className="p-6 overflow-x-auto text-sm">
                  <code className="text-gray-300">{`# Run security audit on your codebase
attune workflow run security-audit --input '{"path": "./src"}'

# Generate tests for a module
attune workflow run test-gen --input '{"path": "./src/auth"}'

# Review code with auto-chaining
attune workflow run code-review --input '{"path": "./src/api.py"}'

# Check dependencies for vulnerabilities
attune workflow run dependency-check

# Pre-release quality gate
attune workflow run release-prep
`}</code>
                </pre>
              </div>
            </div>
          </div>
        </section>

        {/* Workflows CTA */}
        <section className="py-20">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-3xl sm:text-4xl font-bold mb-4">
                Need More Power?
              </h2>
              <p className="text-xl text-[var(--text-secondary)] mb-8">
                Combine wizards with our 14 integrated workflows for multi-agent orchestration,
                progressive tier escalation, and automatic cost optimization.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  href="/workflows"
                  className="btn btn-primary text-lg px-8 py-4"
                >
                  Explore Workflows
                </Link>
                <Link
                  href="/framework-docs/"
                  className="btn btn-outline text-lg px-8 py-4"
                >
                  Read the Docs
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
