import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata as generateSEOMetadata, generateStructuredData } from '@/lib/metadata';

export const metadata: Metadata = generateSEOMetadata({
  title: 'Best AI Agent Frameworks 2026 — CrewAI, LangGraph, AutoGen & Attune AI',
  description:
    'The definitive 2026 guide to AI agent frameworks: CrewAI, LangGraph, AutoGen, and Attune AI. Compare multi-agent support, cost, Claude compatibility, and developer experience.',
  url: 'https://smartaimemory.com/compare/best-ai-agent-frameworks-2026',
  keywords: [
    'best AI agent frameworks 2026',
    'LangGraph vs CrewAI 2026',
    'AI agent framework comparison',
    'CrewAI LangGraph AutoGen Attune',
    'multi-agent AI Python 2026',
  ],
});

const frameworks = [
  {
    name: 'Attune AI',
    tagline: 'Claude-native developer workflows',
    strengths: [
      'First-class Claude Code integration',
      'Cost-optimized tier routing (CHEAP → CAPABLE → PREMIUM)',
      '10 built-in code wizards',
      'Workflow-first design (low learning curve)',
    ],
    weaknesses: ['Smaller community', 'Claude-focused (not multi-LLM)'],
    bestFor: 'Claude Code developers who want cost optimization + automation',
    install: 'pip install attune-ai',
    license: 'Apache 2.0',
    href: 'https://smartaimemory.com',
  },
  {
    name: 'CrewAI',
    tagline: 'Role-based multi-agent crews',
    strengths: [
      '100K+ developer community',
      'Role-based agent composition',
      'Enterprise support available',
      'Large ecosystem of examples',
    ],
    weaknesses: ['Manual cost management', 'No Claude Code integration'],
    bestFor: 'Teams needing a mature, well-documented multi-agent framework',
    install: 'pip install crewai',
    license: 'Apache 2.0',
    href: 'https://crewai.com',
  },
  {
    name: 'LangGraph',
    tagline: 'Graph-based agent orchestration',
    strengths: [
      'Cyclical workflows with graph nodes',
      'Time-travel debugging',
      'Human-in-the-loop first-class',
      'LangChain ecosystem integration',
    ],
    weaknesses: ['Steep learning curve', 'Graph complexity overhead'],
    bestFor: 'Developers needing complex, branching, cyclical agent workflows',
    install: 'pip install langgraph',
    license: 'MIT',
    href: 'https://langchain-ai.github.io/langgraph/',
  },
  {
    name: 'AutoGen',
    tagline: 'Microsoft multi-agent conversations',
    strengths: [
      'Conversational multi-agent',
      'Strong code execution sandbox',
      'Microsoft research backing',
      'Active development',
    ],
    weaknesses: ['Conversation-centric model may not fit all use cases'],
    bestFor: 'Research and enterprise teams wanting Microsoft-backed multi-agent',
    install: 'pip install pyautogen',
    license: 'MIT',
    href: 'https://microsoft.github.io/autogen/',
  },
];

export default function BestFrameworks2026Page() {
  const breadcrumbSchema = generateStructuredData('breadcrumb', {
    items: [
      { name: 'Home', url: 'https://smartaimemory.com' },
      { name: 'Compare', url: 'https://smartaimemory.com/compare' },
      {
        name: 'Best AI Agent Frameworks 2026',
        url: 'https://smartaimemory.com/compare/best-ai-agent-frameworks-2026',
      },
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
                Best AI Agent Frameworks in 2026
              </h1>
              <p className="text-xl text-[var(--text-secondary)]">
                A no-nonsense comparison of the top AI agent frameworks for Python
                developers in 2026: CrewAI, LangGraph, AutoGen, and Attune AI.
                We cover strengths, weaknesses, and what each is best for.
              </p>
              <p className="mt-4 text-sm text-[var(--muted)]">
                Last updated: February 2026
              </p>
            </div>
          </div>
        </section>

        {/* Framework Cards */}
        <section className="py-16">
          <div className="container">
            <div className="max-w-4xl mx-auto space-y-8">
              {frameworks.map((fw) => (
                <div
                  key={fw.name}
                  className="p-8 rounded-xl border-2 border-[var(--border)] hover:border-[var(--primary)] transition-colors"
                >
                  <div className="flex items-start justify-between gap-4 mb-4">
                    <div>
                      <h2 className="text-2xl font-bold">{fw.name}</h2>
                      <p className="text-[var(--muted)]">{fw.tagline}</p>
                    </div>
                    <span className="text-xs font-mono bg-[var(--border)] px-2 py-1 rounded">
                      {fw.license}
                    </span>
                  </div>

                  <div className="grid sm:grid-cols-2 gap-6 mb-6">
                    <div>
                      <h3 className="font-semibold mb-2 text-green-700 dark:text-green-400">
                        Strengths
                      </h3>
                      <ul className="space-y-1 text-sm text-[var(--text-secondary)]">
                        {fw.strengths.map((s) => (
                          <li key={s}>✅ {s}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <h3 className="font-semibold mb-2 text-red-700 dark:text-red-400">
                        Weaknesses
                      </h3>
                      <ul className="space-y-1 text-sm text-[var(--text-secondary)]">
                        {fw.weaknesses.map((w) => (
                          <li key={w}>⚠️ {w}</li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-4">
                    <div className="text-sm">
                      <span className="text-[var(--muted)]">Best for: </span>
                      <span className="font-medium">{fw.bestFor}</span>
                    </div>
                    <code className="text-xs bg-[var(--border)] px-2 py-1 rounded font-mono ml-auto">
                      {fw.install}
                    </code>
                  </div>
                </div>
              ))}
            </div>

            {/* TL;DR */}
            <div className="max-w-4xl mx-auto mt-16">
              <h2 className="text-2xl font-bold mb-6">TL;DR — Which Should You Choose?</h2>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="border-b-2 border-[var(--border)]">
                      <th className="text-left py-3 px-4 font-bold">If you need...</th>
                      <th className="text-left py-3 px-4 font-bold">Use</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b border-[var(--border)]">
                      <td className="py-3 px-4">Claude Code-native integration + cost optimization</td>
                      <td className="py-3 px-4 font-bold text-[var(--primary)]">Attune AI</td>
                    </tr>
                    <tr className="border-b border-[var(--border)] bg-[var(--border)] bg-opacity-30">
                      <td className="py-3 px-4">Largest community, mature ecosystem</td>
                      <td className="py-3 px-4 font-bold">CrewAI</td>
                    </tr>
                    <tr className="border-b border-[var(--border)]">
                      <td className="py-3 px-4">Complex cyclical workflows, human-in-the-loop</td>
                      <td className="py-3 px-4 font-bold">LangGraph</td>
                    </tr>
                    <tr className="border-b border-[var(--border)] bg-[var(--border)] bg-opacity-30">
                      <td className="py-3 px-4">Conversational agents with code execution</td>
                      <td className="py-3 px-4 font-bold">AutoGen</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="mt-12 text-center">
                <h2 className="text-2xl font-bold mb-4">
                  Building with Claude Code? Start with Attune AI.
                </h2>
                <p className="text-[var(--text-secondary)] mb-6">
                  Free, open source, and takes 2 minutes to install.
                </p>
                <div className="flex justify-center gap-4">
                  <Link href="/framework-docs/" className="btn btn-primary">
                    Get Started
                  </Link>
                  <Link href="/compare/crewai-vs-attune" className="btn btn-outline">
                    CrewAI vs Attune AI →
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
