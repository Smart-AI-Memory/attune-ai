import { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Multi-Model Workflows | Attune AI',
  description:
    'Cost-optimized multi-model workflows with 3-tier model routing using Haiku, Sonnet, and Opus.',
  keywords: [
    'multi-model',
    'workflow',
    'cost optimization',
    'LLM routing',
    'model tiers',
    'AI costs',
    'Claude',
  ],
  openGraph: {
    title: 'Multi-Model Workflows | Attune AI',
    description:
      'Track cost savings from intelligent model routing. Optimize AI spend with 3-tier workflows.',
    type: 'website',
  },
};

export default function WorkflowsPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <Link href="/" className="flex items-center gap-3 hover:opacity-80">
                <span className="text-2xl font-bold">W</span>
                <div>
                  <h1 className="text-xl font-bold">Attune AI</h1>
                  <p className="text-white/80 text-sm">Multi-Model Workflows</p>
                </div>
              </Link>
            </div>
            <nav className="flex items-center gap-6">
              <Link href="/docs" className="text-white/80 hover:text-white text-sm">
                Docs
              </Link>
              <Link
                href="/framework-docs/getting-started/"
                className="bg-white/20 hover:bg-white/30 px-4 py-2 rounded-lg text-sm font-medium"
              >
                Get Started
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Hero */}
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white pb-12 pt-6">
        <div className="max-w-6xl mx-auto px-4">
          <div className="flex items-center gap-3 mb-2">
            <h2 className="text-3xl font-bold">Multi-Model Workflows</h2>
          </div>
          <p className="text-white/80 max-w-2xl">
            Cost-optimized workflows with intelligent 3-tier model routing.
            Every task starts on the cheapest tier and escalates only when needed.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <div className="bg-white/10 rounded-lg px-4 py-2">
              <span className="text-sm text-white/60">Cheap Tier</span>
              <p className="font-semibold">Haiku</p>
            </div>
            <div className="bg-white/10 rounded-lg px-4 py-2">
              <span className="text-sm text-white/60">Capable Tier</span>
              <p className="font-semibold">Sonnet</p>
            </div>
            <div className="bg-white/10 rounded-lg px-4 py-2">
              <span className="text-sm text-white/60">Premium Tier</span>
              <p className="font-semibold">Opus</p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <main id="main-content" className="max-w-6xl mx-auto px-4 py-12">
        <div className="text-center">
          <p className="text-lg text-gray-600 mb-8">
            Run workflows from Claude Code using the <code className="bg-gray-100 px-2 py-1 rounded">/attune</code> command
            or the CLI with <code className="bg-gray-100 px-2 py-1 rounded">attune workflow run</code>.
          </p>
          <div className="flex gap-4 justify-center">
            <Link
              href="/workflows"
              className="bg-indigo-600 text-white px-6 py-3 rounded-lg hover:bg-indigo-700 transition-colors"
            >
              Browse Workflows
            </Link>
            <Link
              href="/framework-docs/getting-started/"
              className="border border-gray-300 text-gray-700 px-6 py-3 rounded-lg hover:border-gray-400 transition-colors"
            >
              Quick Start Guide
            </Link>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-6xl mx-auto px-4 py-8">
          <div className="flex justify-between items-center">
            <p className="text-sm text-gray-500">
              Attune AI - Cost-optimized AI workflows
            </p>
            <div className="flex gap-6">
              <Link href="/docs" className="text-sm text-gray-500 hover:text-gray-700">
                Documentation
              </Link>
              <Link href="https://github.com/Smart-AI-Memory/attune-ai" className="text-sm text-gray-500 hover:text-gray-700">
                GitHub
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
