import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata as generateSEOMetadata } from '@/lib/metadata';

export const metadata: Metadata = generateSEOMetadata({
  title: 'Attune AI vs Other AI Agent Frameworks — 2026 Comparison',
  description:
    'Compare Attune AI with CrewAI, LangGraph, and other AI agent frameworks. See which is best for Claude Code developers in 2026.',
  url: 'https://smartaimemory.com/compare',
  keywords: [
    'AI agent framework comparison',
    'CrewAI alternative',
    'LangGraph alternative',
    'best AI agent frameworks 2026',
    'Claude Code agent framework',
  ],
});

const comparisons = [
  {
    href: '/compare/crewai-vs-attune',
    title: 'CrewAI vs Attune AI',
    description:
      'CrewAI is the most popular multi-agent framework with 100K+ developers. See how Attune AI compares for Claude Code developers who want native integration and cost optimization.',
    tags: ['multi-agent', 'CrewAI', 'Python'],
  },
  {
    href: '/compare/langgraph-vs-attune',
    title: 'LangGraph vs Attune AI',
    description:
      'LangGraph from LangChain brings graph-based agent orchestration. Compare it to Attune AI\'s workflow-first approach for Claude Code power users.',
    tags: ['LangChain', 'graph-based', 'orchestration'],
  },
  {
    href: '/compare/best-ai-agent-frameworks-2026',
    title: 'Best AI Agent Frameworks 2026',
    description:
      'A comprehensive roundup of the top AI agent frameworks in 2026: CrewAI, LangGraph, AutoGen, Attune AI, and more. Find the right one for your stack.',
    tags: ['roundup', '2026', 'comparison'],
  },
];

export default function ComparePage() {
  return (
    <>
      <Navigation />
      <main id="main-content" className="min-h-screen pt-16">
        <section className="py-16 bg-gradient-to-b from-[var(--border)] to-transparent">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h1 className="text-4xl sm:text-5xl font-bold mb-6">
                Attune AI vs the Competition
              </h1>
              <p className="text-xl text-[var(--text-secondary)]">
                See how Attune AI compares to other AI agent frameworks. We focus
                on what matters to Claude Code developers: native integration,
                cost optimization, and workflow-first design.
              </p>
            </div>
          </div>
        </section>

        <section className="py-16">
          <div className="container">
            <div className="max-w-4xl mx-auto grid sm:grid-cols-1 gap-6">
              {comparisons.map((c) => (
                <Link
                  key={c.href}
                  href={c.href}
                  className="group p-8 rounded-xl border-2 border-[var(--border)] hover:border-[var(--primary)] hover:shadow-lg transition-all block"
                >
                  <h2 className="text-2xl font-bold mb-3 group-hover:text-[var(--primary)] transition-colors">
                    {c.title}
                  </h2>
                  <p className="text-[var(--text-secondary)] mb-4">{c.description}</p>
                  <div className="flex flex-wrap gap-2">
                    {c.tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-0.5 bg-[var(--border)] rounded text-xs font-semibold"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
