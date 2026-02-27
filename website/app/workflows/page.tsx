import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata } from '@/lib/metadata';

export const metadata: Metadata = generateMetadata({
  title: 'Workflows',
  description: '12 integrated AI workflows including 4 meta-workflows with agent composition for research, debugging, code review, refactoring, release prep, and more.',
  url: 'https://smartaimemory.com/workflows',
});

const workflows = [
  {
    name: 'Research',
    icon: '🔍',
    description: 'Deep research on any technical topic with multi-source synthesis.',
    benefits: [
      'Comprehensive topic analysis',
      'Multiple source aggregation',
      'Structured research reports',
      'Citation tracking',
    ],
    useCases: ['Learning new technologies', 'Architecture decisions', 'Best practices research'],
  },
  {
    name: 'Code Review',
    icon: '👁️',
    description: 'Thorough code review for bugs, style issues, security concerns, and best practices.',
    benefits: [
      'Multi-perspective analysis',
      'Security vulnerability detection',
      'Style and consistency checks',
      'Performance suggestions',
    ],
    useCases: ['PR reviews', 'Code quality gates', 'Team standards enforcement'],
  },
  {
    name: 'Debug',
    icon: '🐛',
    description: 'Intelligent debugging with full project context and root cause analysis.',
    benefits: [
      'Root cause identification',
      'Fix suggestions with code',
      'Similar bug pattern matching',
      'Context-aware analysis',
    ],
    useCases: ['Error resolution', 'Stack trace analysis', 'Production debugging'],
  },
  {
    name: 'Refactor',
    icon: '🔧',
    description: 'Safe refactoring with impact analysis and rollback checkpoints.',
    benefits: [
      'Impact analysis before changes',
      'Automatic checkpoints',
      'Test coverage awareness',
      'Breaking change detection',
    ],
    useCases: ['Code modernization', 'Performance optimization', 'Technical debt reduction'],
  },
  {
    name: 'Test Generation',
    icon: '🧪',
    description: 'Generate comprehensive test suites with edge case coverage.',
    benefits: [
      'Unit test generation',
      'Edge case identification',
      'Mock and fixture creation',
      'Coverage optimization',
    ],
    useCases: ['New feature testing', 'Legacy code coverage', 'Regression prevention'],
  },
  {
    name: 'Documentation',
    icon: '📝',
    description: 'Auto-generate documentation from code with context awareness.',
    benefits: [
      'API documentation',
      'README generation',
      'Inline comment suggestions',
      'Architecture docs',
    ],
    useCases: ['API documentation', 'Onboarding guides', 'Technical specs'],
  },
  {
    name: 'Security Scan',
    icon: '🔒',
    description: 'Deep security analysis for vulnerabilities, secrets, and compliance.',
    benefits: [
      'OWASP vulnerability detection',
      'Secrets and credential scanning',
      'Dependency audit',
      'Compliance checking (HIPAA, SOC2)',
    ],
    useCases: ['Security audits', 'Pre-deployment checks', 'Compliance verification'],
  },
  {
    name: 'Performance',
    icon: '⚡',
    description: 'Identify performance bottlenecks and optimization opportunities.',
    benefits: [
      'Hotspot identification',
      'Memory leak detection',
      'Query optimization',
      'Caching suggestions',
    ],
    useCases: ['Performance tuning', 'Scalability planning', 'Resource optimization'],
  },
  {
    name: 'Explain Code',
    icon: '💡',
    description: 'Get clear explanations of complex code with context.',
    benefits: [
      'Line-by-line explanations',
      'Algorithm breakdowns',
      'Architecture overviews',
      'Dependency mapping',
    ],
    useCases: ['Onboarding', 'Code archaeology', 'Knowledge transfer'],
  },
  {
    name: 'Morning Briefing',
    icon: '☀️',
    description: 'Daily summary of project status, priorities, and action items.',
    benefits: [
      'Git activity summary',
      'Priority recommendations',
      'Blocker identification',
      'Team coordination insights',
    ],
    useCases: ['Daily standups', 'Sprint planning', 'Project status'],
  },
  {
    name: 'Release Prep',
    icon: '🚀',
    description: 'Multi-agent release readiness assessment with parallel validation.',
    benefits: [
      'Security audit automation',
      'Test coverage verification',
      'Documentation completeness check',
      'Performance validation',
    ],
    useCases: ['Release candidates', 'Production deployments', 'Version launches'],
    isMetaWorkflow: true,
  },
  {
    name: 'Test Coverage Boost',
    icon: '📈',
    description: 'Agent team that analyzes gaps and generates tests with progressive tier escalation.',
    benefits: [
      'Gap analysis by module',
      'Automated test generation',
      'Quality gate enforcement',
      'Cost-optimized execution',
    ],
    useCases: ['Coverage improvement', 'Legacy code testing', 'CI/CD gates'],
    isMetaWorkflow: true,
  },
  {
    name: 'Test Maintenance',
    icon: '🔄',
    description: 'Automated test lifecycle management with flaky test detection.',
    benefits: [
      'Flaky test identification',
      'Test health monitoring',
      'Outdated test cleanup',
      'Performance regression detection',
    ],
    useCases: ['Test suite health', 'CI stability', 'Technical debt reduction'],
    isMetaWorkflow: true,
  },
  {
    name: 'Documentation Management',
    icon: '📚',
    description: 'Multi-agent documentation sync with gap detection and generation.',
    benefits: [
      'Doc-code sync verification',
      'Missing documentation detection',
      'API reference generation',
      'Changelog automation',
    ],
    useCases: ['API documentation', 'README maintenance', 'Release notes'],
    isMetaWorkflow: true,
  },
];

export default function WorkflowsPage() {
  return (
    <>
      <Navigation />
      <main id="main-content" className="min-h-screen pt-16">
        {/* Hero Section */}
        <section className="py-20 gradient-primary text-white">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h1 className="text-5xl font-bold mb-6">
                12 Integrated Workflows
              </h1>
              <p className="text-2xl mb-8 opacity-90">
                Production-ready AI workflows including 4 meta-workflows with automatic agent composition—research, build, test, deploy, and maintain.
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

        {/* Workflows Grid */}
        <section className="py-20">
          <div className="container">
            <div className="max-w-6xl mx-auto">
              <div className="grid md:grid-cols-2 gap-8">
                {workflows.map((workflow) => (
                  <div
                    key={workflow.name}
                    className="bg-[var(--background)] p-8 rounded-xl border-2 border-[var(--border)] hover:border-[var(--primary)] transition-all"
                  >
                    <div className="flex items-center gap-4 mb-4">
                      <span className="text-4xl">{workflow.icon}</span>
                      <h2 className="text-2xl font-bold">{workflow.name}</h2>
                    </div>
                    <p className="text-[var(--text-secondary)] mb-6">
                      {workflow.description}
                    </p>

                    <div className="mb-6">
                      <h3 className="font-semibold mb-2">Benefits:</h3>
                      <ul className="space-y-1">
                        {workflow.benefits.map((benefit) => (
                          <li key={benefit} className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
                            <span className="text-green-500">✓</span>
                            {benefit}
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <h3 className="font-semibold mb-2">Use Cases:</h3>
                      <div className="flex flex-wrap gap-2">
                        {workflow.useCases.map((useCase) => (
                          <span
                            key={useCase}
                            className="px-3 py-1 bg-[var(--border)] rounded-full text-sm"
                          >
                            {useCase}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-20">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-3xl font-bold mb-4">
                Ready to Supercharge Your Development?
              </h2>
              <p className="text-xl text-[var(--text-secondary)] mb-8">
                Install Attune AI and start using all 12 workflows today.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  href="/framework-docs/tutorials/quickstart/"
                  className="btn btn-primary text-lg px-8 py-4"
                >
                  pip install attune-ai
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
