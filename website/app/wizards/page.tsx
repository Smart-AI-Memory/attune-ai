import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata as generateSEOMetadata } from '@/lib/metadata';
import { wizards, tierColors, tierLabels } from '@/lib/wizards';

export const metadata: Metadata = generateSEOMetadata({
  title: 'AI Code Wizards — Security, Review & Testing Automation',
  description:
    '10 AI-powered code wizards for security audits, code review, bug prediction, performance analysis, test generation, and more. Works with Claude Code.',
  url: 'https://smartaimemory.com/wizards',
  keywords: [
    'AI security audit tool',
    'AI code review tool',
    'AI test generation Python',
    'bug prediction AI',
    'AI performance audit',
    'Claude Code wizards',
    'developer automation tools',
  ],
});


export default function WizardsPage() {
  return (
    <>
      <Navigation />
      <main id="main-content" className="min-h-screen pt-16">
        {/* Hero */}
        <section className="py-16 sm:py-20 bg-gradient-to-b from-[var(--border)] to-transparent">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h1 className="text-4xl sm:text-5xl font-bold mb-6">
                10 Smart Wizards
              </h1>
              <p className="text-xl text-[var(--text-secondary)] mb-4">
                Interactive guides that walk you through each step — asking questions,
                collecting context, and showing results as you go.
              </p>
              <p className="text-base text-[var(--muted)] mb-8">
                Need non-interactive CI/CD pipelines instead? See{' '}
                <Link href="/workflows" className="underline hover:text-[var(--primary)]">
                  Workflows
                </Link>{' '}
                — wizards call the same underlying engines.
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
                <Link
                  key={wizard.name}
                  href={`/wizards/${wizard.name}`}
                  className="group bg-[var(--background)] p-6 rounded-xl border-2 border-[var(--border)] hover:border-[var(--primary)] hover:shadow-lg transition-all block"
                >
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <h3 className="font-bold text-xl group-hover:text-[var(--primary)] transition-colors">
                      {wizard.displayName}
                    </h3>
                    <span className={`flex-shrink-0 px-2 py-1 text-xs font-medium rounded border ${tierColors[wizard.tier]}`}>
                      {wizard.tier}
                    </span>
                  </div>
                  <p className="text-[var(--text-secondary)] mb-4">
                    {wizard.description}
                  </p>
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className="text-[var(--muted)]">Domain:</span>
                      <span className="font-medium">{wizard.domain}</span>
                    </div>
                    <span className="text-[var(--primary)] opacity-0 group-hover:opacity-100 transition-opacity text-xs font-semibold">
                      Learn more →
                    </span>
                  </div>
                </Link>
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
