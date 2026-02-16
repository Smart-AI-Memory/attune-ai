import { Metadata } from 'next';
import Link from 'next/link';
import DebugWizard from '@/components/debug-wizard/DebugWizard';

export const metadata: Metadata = {
  title: 'Memory-Enhanced Debugging Wizard | Attune AI',
  description:
    'AI debugging assistant that remembers past bugs and their fixes. Correlate current errors with historical patterns for faster resolution.',
  keywords: [
    'debugging',
    'AI debugging',
    'error analysis',
    'bug fixing',
    'developer tools',
    'memory-enhanced',
    'pattern matching',
  ],
  openGraph: {
    title: 'Memory-Enhanced Debugging Wizard | Attune AI',
    description:
      'AI that remembers past bugs. Find fixes faster with historical pattern correlation.',
    type: 'website',
  },
};

export default function DebugWizardPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-lg">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <Link href="/" className="flex items-center gap-3 hover:opacity-80">
                <span className="text-2xl">D</span>
                <div>
                  <h1 className="text-xl font-bold">Attune AI</h1>
                  <p className="text-white/80 text-sm">Memory-Enhanced Debugging</p>
                </div>
              </Link>
            </div>
            <nav className="flex items-center gap-6">
              <Link href="/docs" className="text-white/80 hover:text-white text-sm">
                Docs
              </Link>
              <Link href="/pricing" className="text-white/80 hover:text-white text-sm">
                Pricing
              </Link>
              <Link
                href="/docs/installation"
                className="px-4 py-2 bg-white/20 hover:bg-white/30 rounded-lg text-sm"
              >
                Install Locally
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Feature Banner */}
      <div className="bg-purple-50 border-b border-purple-200">
        <div className="max-w-6xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-purple-500">L</span>
              <div>
                <p className="text-sm text-purple-800">
                  <strong>Level 4+ Empathy:</strong> AI that correlates current errors with
                  historical bug patterns
                </p>
              </div>
            </div>
            <Link
              href="/framework"
              className="text-sm text-purple-600 hover:text-purple-800"
            >
              Learn about Empathy Levels
            </Link>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main id="main-content" className="max-w-6xl mx-auto px-4 py-8">
        {/* Intro Section */}
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">
            Debug Smarter with AI Memory
          </h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Stop debugging the same bugs over and over. Our AI remembers past errors and their
            fixes, helping you resolve issues faster with historical pattern matching.
          </p>
        </div>

        {/* How It Works */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <div className="bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
              <span className="text-2xl text-purple-600">1</span>
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">Paste Your Error</h3>
            <p className="text-sm text-gray-600">
              Enter the error message, stack trace, and relevant code snippet.
            </p>
          </div>
          <div className="bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
              <span className="text-2xl text-purple-600">2</span>
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">AI Analyzes Patterns</h3>
            <p className="text-sm text-gray-600">
              Our AI classifies the error and searches historical patterns for matches.
            </p>
          </div>
          <div className="bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
              <span className="text-2xl text-purple-600">3</span>
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">Get Fix Recommendations</h3>
            <p className="text-sm text-gray-600">
              Receive targeted fix suggestions based on how similar bugs were resolved.
            </p>
          </div>
        </div>

        {/* The Wizard */}
        <DebugWizard />

        {/* Memory Benefit Explainer */}
        <div className="mt-12 bg-gradient-to-r from-purple-50 to-indigo-50 rounded-xl p-8 border border-purple-200">
          <h3 className="text-xl font-bold text-purple-900 mb-4">
            Why Memory-Enhanced Debugging?
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div>
              <h4 className="font-semibold text-red-700 mb-2">Without Persistent Memory</h4>
              <ul className="space-y-2 text-sm text-gray-700">
                <li className="flex items-start gap-2">
                  <span className="text-red-500">X</span>
                  Every debugging session starts from zero
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-red-500">X</span>
                  Same bugs diagnosed repeatedly across team
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-red-500">X</span>
                  Fix knowledge lost between sessions
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-red-500">X</span>
                  No learning from collective experience
                </li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-green-700 mb-2">With Persistent Memory</h4>
              <ul className="space-y-2 text-sm text-gray-700">
                <li className="flex items-start gap-2">
                  <span className="text-green-500">V</span>
                  AI remembers past bugs and fixes
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-500">V</span>
                  &quot;This looks like bug #247 from 3 months ago&quot;
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-500">V</span>
                  Recommends proven fixes instantly
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-500">V</span>
                  Team knowledge compounds over time
                </li>
              </ul>
            </div>
          </div>
        </div>

        {/* Local Installation CTA */}
        <div className="mt-12 bg-gray-900 text-white rounded-xl p-8">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-bold mb-2">Want Unlimited Features?</h3>
              <p className="text-gray-400">
                Install locally for unlimited files, folder uploads, and full pattern history.
                Your data stays on your machine.
              </p>
            </div>
            <div className="flex gap-4">
              <Link
                href="/docs/installation"
                className="px-6 py-3 bg-purple-600 hover:bg-purple-700 rounded-lg font-semibold"
              >
                Install Guide
              </Link>
              <a
                href="https://github.com/smart-ai-memory/attune-ai"
                target="_blank"
                rel="noopener noreferrer"
                className="px-6 py-3 bg-white/10 hover:bg-white/20 rounded-lg font-semibold"
              >
                View on GitHub
              </a>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-gray-100 border-t border-gray-200 mt-12">
        <div className="max-w-6xl mx-auto px-4 py-8">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">
              Part of the{' '}
              <Link href="/" className="text-purple-600 hover:text-purple-800">
                Attune AI
              </Link>
              {' '}- Five-level AI collaboration with persistent memory
            </div>
            <div className="flex items-center gap-6 text-sm text-gray-600">
              <Link href="/privacy" className="hover:text-gray-900">
                Privacy
              </Link>
              <Link href="/terms" className="hover:text-gray-900">
                Terms
              </Link>
              <Link href="/docs" className="hover:text-gray-900">
                Documentation
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
