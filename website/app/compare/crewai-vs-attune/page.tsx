import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata as generateSEOMetadata, generateStructuredData } from '@/lib/metadata';

export const metadata: Metadata = generateSEOMetadata({
  title: 'CrewAI vs Attune AI — 2026 Comparison for Claude Code Developers',
  description:
    'CrewAI vs Attune AI: a detailed 2026 comparison for Python developers building with Claude Code. Compare multi-agent support, cost optimization, installation, and Claude-native features.',
  url: 'https://smartaimemory.com/compare/crewai-vs-attune',
  keywords: [
    'CrewAI vs Attune AI',
    'CrewAI alternative',
    'Claude Code multi-agent framework',
    'AI agent framework Python 2026',
    'CrewAI comparison',
  ],
});

const rows = [
  { feature: 'Claude-native integration', attune: '✅ First-class', crewai: '⚠️ Via LangChain adapter' },
  { feature: 'Prompt caching (Anthropic built-in)', attune: '✅ Built-in', crewai: '❌ Manual setup' },
  { feature: 'Multi-agent orchestration', attune: '✅ 6 strategies', crewai: '✅ Role-based crews' },
  { feature: 'Code wizards', attune: '✅ 10 built-in', crewai: '❌ None' },
  { feature: 'Semantic caching', attune: '✅ Built-in', crewai: '❌ None' },
  { feature: 'Claude Code CLI integration', attune: '✅ Plugin-native', crewai: '❌ None' },
  { feature: 'Model tier routing', attune: '✅ Cheap/Capable/Premium', crewai: '⚠️ Manual per-agent' },
  { feature: 'Agent state persistence', attune: '✅ Built-in', crewai: '⚠️ Custom setup' },
  { feature: 'Open source license', attune: '✅ Apache 2.0', crewai: '✅ Apache 2.0 (core)' },
  { feature: 'Community size', attune: 'Growing', crewai: '100K+ developers' },
  { feature: 'Installation', attune: 'pip install attune-ai', crewai: 'pip install crewai' },
];

export default function CrewAIVsAttunePage() {
  const breadcrumbSchema = generateStructuredData('breadcrumb', {
    items: [
      { name: 'Home', url: 'https://smartaimemory.com' },
      { name: 'Compare', url: 'https://smartaimemory.com/compare' },
      { name: 'CrewAI vs Attune AI', url: 'https://smartaimemory.com/compare/crewai-vs-attune' },
    ],
  });

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbSchema) }}
      />
      <Navigation />
      <main id="main-content" className="min-h-screen pt-16">
        {/* Hero */}
        <section className="py-16 bg-gradient-to-b from-[var(--border)] to-transparent">
          <div className="container">
            <div className="max-w-3xl mx-auto">
              <nav className="mb-6 text-sm text-[var(--muted)]">
                <Link href="/compare" className="hover:text-[var(--primary)] transition-colors">
                  ← All Comparisons
                </Link>
              </nav>
              <h1 className="text-4xl sm:text-5xl font-bold mb-6">
                CrewAI vs Attune AI
              </h1>
              <p className="text-xl text-[var(--text-secondary)]">
                CrewAI is the most widely adopted multi-agent Python framework with
                100K+ developers. Attune AI is purpose-built for Claude Code developers,
                with 17 AI workflows, 10 code wizards, and cost-optimized tier routing built in.
                Here&apos;s how they compare.
              </p>
            </div>
          </div>
        </section>

        {/* Comparison Table */}
        <section className="py-16">
          <div className="container">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl font-bold mb-6">Feature Comparison</h2>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="border-b-2 border-[var(--border)]">
                      <th className="text-left py-3 px-4 font-bold">Feature</th>
                      <th className="text-left py-3 px-4 font-bold text-[var(--primary)]">Attune AI</th>
                      <th className="text-left py-3 px-4 font-bold">CrewAI</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, i) => (
                      <tr
                        key={row.feature}
                        className={`border-b border-[var(--border)] ${i % 2 === 0 ? 'bg-[var(--border)] bg-opacity-30' : ''}`}
                      >
                        <td className="py-3 px-4 font-medium">{row.feature}</td>
                        <td className="py-3 px-4">{row.attune}</td>
                        <td className="py-3 px-4">{row.crewai}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Summary */}
              <div className="mt-12 grid sm:grid-cols-2 gap-6">
                <div className="p-6 rounded-xl border border-[var(--border)]">
                  <h3 className="text-lg font-bold mb-3">Choose Attune AI if...</h3>
                  <ul className="space-y-2 text-[var(--text-secondary)]">
                    <li>• You use Claude Code as your primary AI development environment</li>
                    <li>• Reducing API costs is a priority (tier routing + Anthropic caching)</li>
                    <li>• You want built-in code wizards for security, testing, and review</li>
                    <li>• You need a Claude-native, workflow-first development experience</li>
                  </ul>
                </div>
                <div className="p-6 rounded-xl border border-[var(--border)]">
                  <h3 className="text-lg font-bold mb-3">Choose CrewAI if...</h3>
                  <ul className="space-y-2 text-[var(--text-secondary)]">
                    <li>• You need the largest community and most examples</li>
                    <li>• You&apos;re working in a multi-LLM environment (OpenAI, Gemini, etc.)</li>
                    <li>• Your team already knows CrewAI patterns</li>
                    <li>• You need enterprise support and SLAs</li>
                  </ul>
                </div>
              </div>

              {/* CTA */}
              <div className="mt-12 p-8 bg-gradient-to-r from-[var(--primary)] to-[var(--primary-dark,var(--primary))] rounded-xl text-white text-center">
                <h2 className="text-2xl font-bold mb-3">Try Attune AI in 2 minutes</h2>
                <p className="mb-6 opacity-90">
                  Free, open source, and designed for Claude Code developers.
                </p>
                <div className="bg-black bg-opacity-30 rounded-lg p-3 font-mono text-sm mb-6 inline-block">
                  pip install attune-ai
                </div>
                <div className="flex justify-center gap-4">
                  <Link href="/framework-docs/" className="btn bg-white text-[var(--primary)] hover:bg-opacity-90">
                    Read the Docs
                  </Link>
                  <a
                    href="https://github.com/Smart-AI-Memory/attune-ai"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-outline border-white text-white hover:bg-white hover:text-[var(--primary)]"
                  >
                    GitHub
                  </a>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
