import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata as generateSEOMetadata, generateStructuredData } from '@/lib/metadata';

export const metadata: Metadata = generateSEOMetadata({
  title: 'LangGraph vs Attune AI — 2026 Comparison for Claude Code Developers',
  description:
    'LangGraph vs Attune AI: compare graph-based agent orchestration with workflow-first AI developer tooling for Claude Code in 2026.',
  url: 'https://smartaimemory.com/compare/langgraph-vs-attune',
  keywords: [
    'LangGraph vs Attune AI',
    'LangGraph alternative',
    'Claude Code agent framework',
    'LangChain alternative',
    'AI agent orchestration comparison 2026',
  ],
});

const rows = [
  { feature: 'Claude-native integration', attune: '✅ First-class', langgraph: '⚠️ Via LangChain adapter' },
  { feature: 'Orchestration model', attune: 'Workflow-first (linear + parallel)', langgraph: 'Graph-based (nodes + edges)' },
  { feature: 'Prompt caching (90% cost savings)', attune: '✅ Built-in', langgraph: '❌ Manual setup' },
  { feature: 'Code wizards', attune: '✅ 10 built-in', langgraph: '❌ None' },
  { feature: 'Claude Code CLI integration', attune: '✅ Plugin-native', langgraph: '❌ None' },
  { feature: 'Learning curve', attune: 'Low (workflow DSL)', langgraph: 'Steep (graph theory required)' },
  { feature: 'Agent state persistence', attune: '✅ Built-in', langgraph: '✅ Checkpointing built-in' },
  { feature: 'Human-in-the-loop', attune: '⚠️ Via Socratic prompts', langgraph: '✅ First-class' },
  { feature: 'Open source license', attune: '✅ Apache 2.0', langgraph: '✅ MIT' },
  { feature: 'Installation', attune: 'pip install attune-ai', langgraph: 'pip install langgraph' },
];

export default function LangGraphVsAttunePage() {
  const breadcrumbSchema = generateStructuredData('breadcrumb', {
    items: [
      { name: 'Home', url: 'https://smartaimemory.com' },
      { name: 'Compare', url: 'https://smartaimemory.com/compare' },
      { name: 'LangGraph vs Attune AI', url: 'https://smartaimemory.com/compare/langgraph-vs-attune' },
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
                LangGraph vs Attune AI
              </h1>
              <p className="text-xl text-[var(--text-secondary)]">
                LangGraph brings graph-based agent orchestration to the LangChain
                ecosystem — powerful for complex, cyclical workflows. Attune AI takes
                a workflow-first approach that&apos;s easier to get started with and
                purpose-built for Claude Code developers.
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
                      <th className="text-left py-3 px-4 font-bold">LangGraph</th>
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
                        <td className="py-3 px-4">{row.langgraph}</td>
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
                    <li>• You use Claude Code and want seamless CLI integration</li>
                    <li>• You want linear workflows without graph theory overhead</li>
                    <li>• Cost optimization (prompt caching) is important</li>
                    <li>• You need built-in code wizards for everyday developer tasks</li>
                  </ul>
                </div>
                <div className="p-6 rounded-xl border border-[var(--border)]">
                  <h3 className="text-lg font-bold mb-3">Choose LangGraph if...</h3>
                  <ul className="space-y-2 text-[var(--text-secondary)]">
                    <li>• You need cyclical, graph-based agent flows</li>
                    <li>• Human-in-the-loop interrupts are a core requirement</li>
                    <li>• You&apos;re already in the LangChain ecosystem</li>
                    <li>• You need time-travel debugging and state branching</li>
                  </ul>
                </div>
              </div>

              {/* CTA */}
              <div className="mt-12 p-8 bg-gradient-to-r from-[var(--primary)] to-[var(--primary-dark,var(--primary))] rounded-xl text-white text-center">
                <h2 className="text-2xl font-bold mb-3">Try Attune AI for Claude Code</h2>
                <p className="mb-6 opacity-90">
                  Free, open source, and installed in seconds.
                </p>
                <div className="bg-black bg-opacity-30 rounded-lg p-3 font-mono text-sm mb-6 inline-block">
                  pip install attune-ai
                </div>
                <div className="flex justify-center gap-4">
                  <Link href="/framework-docs/" className="btn bg-white text-[var(--primary)] hover:bg-opacity-90">
                    Read the Docs
                  </Link>
                  <Link href="/compare" className="btn btn-outline border-white text-white hover:bg-white hover:text-[var(--primary)]">
                    More Comparisons
                  </Link>
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
