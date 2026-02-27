import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata } from '@/lib/metadata';

export const metadata: Metadata = generateMetadata({
  title: 'AI Developer Workflows — Non-Interactive CI/CD Pipelines',
  description:
    '10 production-ready AI workflows for security audits, code review, bug prediction, test generation, documentation, and more. Run from CLI or CI/CD with structured JSON output.',
  url: 'https://smartaimemory.com/workflows',
  keywords: [
    'AI workflow automation',
    'Claude Code workflows',
    'CI/CD AI integration',
    'automated code review',
    'automated security audit',
    'AI test generation',
    'developer automation',
  ],
});

const workflows = [
  {
    name: 'Security Audit',
    command: 'security-audit',
    icon: '🔒',
    description: 'OWASP-focused security scan with vulnerability assessment across triage, analysis, severity scoring, and remediation stages.',
    benefits: [
      'OWASP Top 10 detection',
      'Secrets and credential scanning',
      'Dependency vulnerability audit',
      'Prioritized fix recommendations',
    ],
    useCases: ['Pre-deployment checks', 'Compliance verification', 'Security audits'],
  },
  {
    name: 'Code Review',
    command: 'code-review',
    icon: '👁️',
    description: 'Tiered code analysis with conditional premium review — classify, scan, performance check, and architect review stages.',
    benefits: [
      'Multi-tier analysis (Haiku → Sonnet → Opus)',
      'Security vulnerability detection',
      'Performance suggestions',
      'Architecture-level feedback',
    ],
    useCases: ['PR reviews', 'Code quality gates', 'Team standards enforcement'],
  },
  {
    name: 'Bug Prediction',
    command: 'bug-predict',
    icon: '🐛',
    description: 'Predict bugs by analyzing code against learned patterns — scan, correlate with history, predict risk, and recommend fixes.',
    benefits: [
      'Pattern-based risk scoring',
      'Historical bug correlation',
      'Null pointer and race condition detection',
      'Prioritized remediation list',
    ],
    useCases: ['Pre-release risk assessment', 'Code quality gates', 'Technical debt triage'],
  },
  {
    name: 'Performance Audit',
    command: 'perf-audit',
    icon: '⚡',
    description: 'Identify performance bottlenecks and optimization opportunities — profile, analyze, identify hotspots, and optimize.',
    benefits: [
      'Hotspot identification',
      'Memory leak detection',
      'Query optimization suggestions',
      'Caching recommendations',
    ],
    useCases: ['Performance tuning', 'Scalability planning', 'Resource optimization'],
  },
  {
    name: 'Test Generation',
    command: 'test-gen',
    icon: '🧪',
    description: 'Generate tests targeting areas with historical bugs — identify gaps, analyze coverage, generate pytest suites, review output.',
    benefits: [
      'Bug-history-driven test targeting',
      'Edge case identification',
      'Mock and fixture creation',
      'Coverage gap analysis',
    ],
    useCases: ['New feature testing', 'Legacy code coverage', 'Regression prevention'],
  },
  {
    name: 'Documentation',
    command: 'doc-gen',
    icon: '📝',
    description: 'Cost-optimized documentation pipeline — outline with Haiku, write with Sonnet, polish with Opus.',
    benefits: [
      'API documentation generation',
      'README creation',
      'Inline comment suggestions',
      'Architecture docs',
    ],
    useCases: ['API documentation', 'Onboarding guides', 'Technical specs'],
  },
  {
    name: 'Refactor Plan',
    command: 'refactor-plan',
    icon: '🔧',
    description: 'Prioritize tech debt based on trajectory and impact — scan codebase, analyze complexity, prioritize issues, output action plan.',
    benefits: [
      'Impact-ranked tech debt list',
      'Complexity analysis',
      'Safe refactoring sequencing',
      'Breaking change detection',
    ],
    useCases: ['Code modernization', 'Technical debt reduction', 'Pre-sprint planning'],
  },
  {
    name: 'Dependency Check',
    command: 'dependency-check',
    icon: '📦',
    description: 'Audit dependencies for vulnerabilities and updates — inventory packages, assess CVEs, report with severity rankings.',
    benefits: [
      'CVE vulnerability detection',
      'Outdated package identification',
      'Unmaintained package flagging',
      'Severity-ranked action list',
    ],
    useCases: ['Security audits', 'Dependency hygiene', 'Compliance checks'],
  },
  {
    name: 'Release Prep',
    command: 'release-prep',
    icon: '🚀',
    description: 'Multi-agent release readiness assessment with parallel validation — triage, parallel checks, synthesis, and go/no-go decision.',
    benefits: [
      'Parallel security + test + doc checks',
      'Test coverage verification',
      'Documentation completeness check',
      'Automated go/no-go decision',
    ],
    useCases: ['Release candidates', 'Production deployments', 'Version launches'],
  },
  {
    name: 'Research Synthesis',
    command: 'research-synthesis',
    icon: '🔍',
    description: 'Cost-optimized multi-document research — summarize sources with Haiku, analyze with Sonnet, synthesize findings with Opus.',
    benefits: [
      'Multi-source aggregation',
      'Structured research reports',
      'Cost-optimized tier routing',
      'Citation and source tracking',
    ],
    useCases: ['Architecture decisions', 'Technology evaluation', 'Best practices research'],
  },
];

export default function WorkflowsPage() {
  return (
    <>
      <Navigation />
      <main id="main-content" className="min-h-screen pt-16">
        {/* Hero */}
        <section className="py-20 gradient-primary text-white">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h1 className="text-5xl font-bold mb-4">
                10 AI Developer Workflows
              </h1>
              <p className="text-xl mb-4 opacity-90">
                Non-interactive, multi-stage pipelines designed for CLI and CI/CD use.
                Each workflow collects context, escalates through model tiers, and returns structured JSON output.
              </p>
              <p className="text-base mb-8 opacity-75">
                Looking for an interactive guided experience? Try{' '}
                <Link href="/wizards" className="underline hover:opacity-90">
                  Wizards
                </Link>{' '}
                — they wrap these same workflows in a step-by-step conversation.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  href="/framework-docs/tutorials/quickstart/"
                  className="btn bg-white text-[var(--primary)] hover:bg-opacity-90"
                >
                  Get Started
                </Link>
                <a
                  href="https://github.com/Smart-AI-Memory/attune-ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn border-2 border-white text-white hover:bg-white hover:text-[var(--primary)]"
                >
                  View on GitHub
                </a>
              </div>
            </div>
          </div>
        </section>

        {/* CLI usage */}
        <section className="py-10 border-b border-[var(--border)]">
          <div className="container">
            <div className="max-w-2xl mx-auto bg-[#1e1e1e] rounded-xl overflow-hidden shadow-lg">
              <div className="flex items-center gap-2 px-4 py-3 bg-[#2d2d2d] border-b border-[#3d3d3d]">
                <div className="w-3 h-3 rounded-full bg-[#ff5f56]"></div>
                <div className="w-3 h-3 rounded-full bg-[#ffbd2e]"></div>
                <div className="w-3 h-3 rounded-full bg-[#27ca40]"></div>
                <span className="ml-2 text-sm text-gray-400">terminal</span>
              </div>
              <pre className="p-5 overflow-x-auto text-sm">
                <code className="text-gray-300">{`# Run any workflow
attune workflow run <name> --input '{"path": "src/"}'

# Examples
attune workflow run security-audit --input '{"path": "src/"}'
attune workflow run code-review --input '{"path": "src/api.py"}'
attune workflow run release-prep

# JSON output for CI/CD
attune workflow run bug-predict --json`}</code>
              </pre>
            </div>
          </div>
        </section>

        {/* Workflows Grid */}
        <section className="py-16">
          <div className="container">
            <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-8">
              {workflows.map((workflow) => (
                <div
                  key={workflow.name}
                  className="bg-[var(--background)] p-8 rounded-xl border-2 border-[var(--border)] hover:border-[var(--primary)] transition-all"
                >
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-3xl">{workflow.icon}</span>
                    <div>
                      <h2 className="text-xl font-bold">{workflow.name}</h2>
                      <code className="text-xs text-[var(--muted)]">
                        attune workflow run {workflow.command}
                      </code>
                    </div>
                  </div>
                  <p className="text-[var(--text-secondary)] mb-5 text-sm">
                    {workflow.description}
                  </p>
                  <div className="mb-5">
                    <h3 className="font-semibold text-sm mb-2">What you get:</h3>
                    <ul className="space-y-1">
                      {workflow.benefits.map((benefit) => (
                        <li key={benefit} className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
                          <span className="text-green-500">✓</span>
                          {benefit}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {workflow.useCases.map((useCase) => (
                      <span
                        key={useCase}
                        className="px-3 py-1 bg-[var(--border)] rounded-full text-xs"
                      >
                        {useCase}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-20">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-3xl font-bold mb-4">
                Ready to automate your dev workflow?
              </h2>
              <p className="text-xl text-[var(--text-secondary)] mb-8">
                Install Attune AI and run all 10 workflows today.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  href="/framework-docs/tutorials/quickstart/"
                  className="btn btn-primary text-lg px-8 py-4"
                >
                  pip install attune-ai
                </Link>
                <Link
                  href="/wizards"
                  className="btn btn-outline text-lg px-8 py-4"
                >
                  Explore Wizards
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
