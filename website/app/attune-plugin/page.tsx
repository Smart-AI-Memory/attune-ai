import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata as generateSEOMetadata } from '@/lib/metadata';
import { liteSkills } from '@/lib/attune-lite-skills';

export const metadata: Metadata = generateSEOMetadata({
  title: 'Attune Plugins for Claude Code',
  description:
    'Free Claude Code plugins by Smart AI Memory. Attune Lite: 5 AI-powered workflows for the plugin marketplace. Attune AI: the full developer workflow OS with 17 workflows, wizards, and agents.',
  url: 'https://smartaimemory.com/attune-plugin',
  keywords: [
    'Claude Code plugin',
    'Claude Code extension',
    'AI code review',
    'AI security audit',
    'AI test generation',
    'bug prediction',
    'Claude Code workflows',
    'Attune AI plugin',
    'Attune Lite',
    'free Claude Code plugin',
  ],
});

export default function AttunePluginPage() {
  return (
    <div id="main-content" className="min-h-screen">
      <Navigation />

      {/* Hero */}
      <section className="pt-32 pb-20 gradient-primary text-white">
        <div className="container">
          <div className="max-w-3xl mx-auto text-center">
            <p className="text-sm font-semibold uppercase tracking-wider mb-4 opacity-80">
              Claude Code Plugins by Smart AI Memory
            </p>
            <h1 className="text-5xl font-bold mb-6">Attune Plugins</h1>
            <p className="text-xl mb-4 opacity-90">
              AI-powered developer workflows, right inside Claude Code.
              Two plugins, one mission: make every dev workflow faster.
            </p>
            <p className="text-lg mb-8 opacity-75">
              Start with Attune Lite from the marketplace, or install the
              full Attune AI plugin for the complete experience.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a
                href="https://github.com/Smart-AI-Memory/attune-lite"
                target="_blank"
                rel="noopener noreferrer"
                className="btn bg-white text-[var(--primary)] hover:bg-gray-100 text-lg px-8 py-4"
              >
                Get Attune Lite
              </a>
              <a
                href="https://github.com/Smart-AI-Memory/attune-ai"
                target="_blank"
                rel="noopener noreferrer"
                className="btn border-2 border-white text-white hover:bg-white hover:text-[var(--primary)] text-lg px-8 py-4"
              >
                Get Attune AI (Full)
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Attune Lite Section */}
      <section className="py-20">
        <div className="container">
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-12">
              <p className="text-sm font-semibold uppercase tracking-wider text-[var(--secondary)] mb-2">
                Plugin Marketplace
              </p>
              <h2 className="text-4xl font-bold mb-4">
                <Link href="/attune-lite" className="hover:text-[var(--primary)] transition-colors">
                  Attune Lite
                </Link>
              </h2>
              <p className="text-xl text-[var(--text-secondary)] max-w-2xl mx-auto">
                5 curated AI workflows, zero dependencies. Designed for the
                Anthropic plugin marketplace &mdash; install and go.{' '}
                <Link href="/attune-lite" className="text-[var(--primary)] hover:underline">
                  Learn more
                </Link>
              </p>
            </div>

            {/* How It Works */}
            <div className="grid md:grid-cols-3 gap-8 mb-16">
              <div className="text-center">
                <div className="text-4xl mb-4">1</div>
                <h3 className="text-xl font-bold mb-2">Install</h3>
                <p className="text-[var(--text-secondary)]">
                  Add from the plugin marketplace. No pip install, no API
                  keys, no config files.
                </p>
              </div>
              <div className="text-center">
                <div className="text-4xl mb-4">2</div>
                <h3 className="text-xl font-bold mb-2">Type a Command</h3>
                <p className="text-[var(--text-secondary)]">
                  Use any of the 5 slash commands like{' '}
                  <code>/code-review</code> or <code>/security-audit</code>.
                </p>
              </div>
              <div className="text-center">
                <div className="text-4xl mb-4">3</div>
                <h3 className="text-xl font-bold mb-2">Get Results</h3>
                <p className="text-[var(--text-secondary)]">
                  Receive a structured, multi-agent report with findings
                  organized by severity and category.
                </p>
              </div>
            </div>

            {/* Skills Grid */}
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
              {liteSkills.map((skill) => (
                <div
                  key={skill.command}
                  className="bg-[var(--border)] bg-opacity-30 p-6 rounded-lg"
                >
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-3xl">{skill.icon}</span>
                    <div>
                      <h3 className="text-xl font-bold">{skill.title}</h3>
                      <code className="text-sm text-[var(--primary)]">
                        {skill.command}
                      </code>
                    </div>
                  </div>
                  <p className="text-[var(--text-secondary)] mb-4 text-sm">
                    {skill.description}
                  </p>
                  <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
                    {skill.features.map((feature) => (
                      <li key={feature} className="flex items-start gap-2">
                        <span className="text-[var(--success)]">&#10003;</span>
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>

            <div className="mt-8 bg-[var(--secondary)] bg-opacity-10 border-l-4 border-[var(--secondary)] p-6 rounded-r-lg">
              <h3 className="text-xl font-bold mb-2">
                Prompt-Based, Not Code-Based
              </h3>
              <p className="text-[var(--text-secondary)]">
                Each skill is a self-contained prompt with agent orchestration
                instructions baked in. Claude Code executes them natively
                &mdash; no Python runtime, no subprocess calls, no external
                dependencies. Perfect for the plugin marketplace.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Attune AI Full Plugin */}
      <section className="py-20 bg-[var(--border)] bg-opacity-30">
        <div className="container">
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-12">
              <p className="text-sm font-semibold uppercase tracking-wider text-[var(--accent)] mb-2">
                Full Plugin
              </p>
              <h2 className="text-4xl font-bold mb-4">Attune AI</h2>
              <p className="text-xl text-[var(--text-secondary)] max-w-2xl mx-auto">
                The complete developer workflow OS. Everything in Lite, plus
                17 workflows, wizards, agents, CLI tooling, and more.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8 mb-12">
              <div className="bg-[var(--background)] p-6 rounded-lg">
                <h3 className="text-xl font-bold mb-3">17 Workflows</h3>
                <p className="text-[var(--text-secondary)] mb-4">
                  Deep review, refactor planning, dependency checks,
                  release prep, performance audits, and more.
                </p>
                <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">&#10003;</span>
                    <span>Deep multi-pass code review</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">&#10003;</span>
                    <span>Refactor planning</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">&#10003;</span>
                    <span>Dependency analysis</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">&#10003;</span>
                    <span>Release preparation</span>
                  </li>
                </ul>
              </div>

              <div className="bg-[var(--background)] p-6 rounded-lg">
                <h3 className="text-xl font-bold mb-3">5 Wizards</h3>
                <p className="text-[var(--text-secondary)] mb-4">
                  Interactive multi-step guided experiences for complex
                  tasks like debugging, testing, and release prep.
                </p>
                <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">&#10003;</span>
                    <span>Debug wizard</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">&#10003;</span>
                    <span>Refactor wizard</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">&#10003;</span>
                    <span>Release prep wizard</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">&#10003;</span>
                    <span>Security audit wizard</span>
                  </li>
                </ul>
              </div>

              <div className="bg-[var(--background)] p-6 rounded-lg">
                <h3 className="text-xl font-bold mb-3">Agent Orchestration</h3>
                <p className="text-[var(--text-secondary)] mb-4">
                  14 agent templates, multi-agent teams, Socratic
                  discovery, and natural language command routing.
                </p>
                <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">&#10003;</span>
                    <span>14 agent templates</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">&#10003;</span>
                    <span>Socratic discovery UX</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">&#10003;</span>
                    <span>CLI and MCP integration</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">&#10003;</span>
                    <span>Cost-optimized model routing</span>
                  </li>
                </ul>
              </div>
            </div>

            <div className="bg-[var(--accent)] bg-opacity-10 border-l-4 border-[var(--accent)] p-6 rounded-r-lg">
              <h3 className="text-xl font-bold mb-2">
                Also available on PyPI
              </h3>
              <p className="text-[var(--text-secondary)] mb-4">
                Install the full framework with{' '}
                <code>pip install attune-ai</code> to use workflows from the
                command line, integrate with MCP servers, or build custom
                agents on top of the SDK.
              </p>
              <div className="flex flex-col sm:flex-row gap-4">
                <a
                  href="https://github.com/Smart-AI-Memory/attune-ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-primary text-sm"
                >
                  View on GitHub
                </a>
                <a
                  href="https://pypi.org/project/attune-ai/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-outline text-sm"
                >
                  View on PyPI
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Comparison */}
      <section className="py-20">
        <div className="container">
          <div className="max-w-3xl mx-auto">
            <h2 className="text-3xl font-bold text-center mb-12">
              Which Plugin Is Right for You?
            </h2>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b-2 border-[var(--border)]">
                    <th className="py-3 pr-4 text-[var(--text-secondary)] font-semibold">Feature</th>
                    <th className="py-3 px-4 text-center font-semibold">Attune Lite</th>
                    <th className="py-3 pl-4 text-center font-semibold">Attune AI</th>
                  </tr>
                </thead>
                <tbody className="text-sm text-[var(--text-secondary)]">
                  <tr className="border-b border-[var(--border)]">
                    <td className="py-3 pr-4">Workflows</td>
                    <td className="py-3 px-4 text-center">5</td>
                    <td className="py-3 pl-4 text-center">17</td>
                  </tr>
                  <tr className="border-b border-[var(--border)]">
                    <td className="py-3 pr-4">Wizards</td>
                    <td className="py-3 px-4 text-center">&mdash;</td>
                    <td className="py-3 pl-4 text-center">5</td>
                  </tr>
                  <tr className="border-b border-[var(--border)]">
                    <td className="py-3 pr-4">Agent templates</td>
                    <td className="py-3 px-4 text-center">&mdash;</td>
                    <td className="py-3 pl-4 text-center">14</td>
                  </tr>
                  <tr className="border-b border-[var(--border)]">
                    <td className="py-3 pr-4">Plugin marketplace</td>
                    <td className="py-3 px-4 text-center text-[var(--success)]">&#10003;</td>
                    <td className="py-3 pl-4 text-center text-[var(--success)]">&#10003;</td>
                  </tr>
                  <tr className="border-b border-[var(--border)]">
                    <td className="py-3 pr-4">CLI tooling</td>
                    <td className="py-3 px-4 text-center">&mdash;</td>
                    <td className="py-3 pl-4 text-center text-[var(--success)]">&#10003;</td>
                  </tr>
                  <tr className="border-b border-[var(--border)]">
                    <td className="py-3 pr-4">MCP integration</td>
                    <td className="py-3 px-4 text-center">&mdash;</td>
                    <td className="py-3 pl-4 text-center text-[var(--success)]">&#10003;</td>
                  </tr>
                  <tr className="border-b border-[var(--border)]">
                    <td className="py-3 pr-4">PyPI package</td>
                    <td className="py-3 px-4 text-center">&mdash;</td>
                    <td className="py-3 pl-4 text-center text-[var(--success)]">&#10003;</td>
                  </tr>
                  <tr className="border-b border-[var(--border)]">
                    <td className="py-3 pr-4">Dependencies</td>
                    <td className="py-3 px-4 text-center">None</td>
                    <td className="py-3 pl-4 text-center">Python 3.10+</td>
                  </tr>
                  <tr>
                    <td className="py-3 pr-4">Price</td>
                    <td className="py-3 px-4 text-center font-semibold">Free</td>
                    <td className="py-3 pl-4 text-center font-semibold">Free</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 gradient-primary text-white">
        <div className="container">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-4xl font-bold mb-6">Get Started in Seconds</h2>
            <p className="text-xl mb-8 opacity-90">
              Both plugins are free and open source. Pick the one that fits
              your workflow.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a
                href="https://github.com/Smart-AI-Memory/attune-lite"
                target="_blank"
                rel="noopener noreferrer"
                className="btn bg-white text-[var(--primary)] hover:bg-gray-100 text-lg px-8 py-4"
              >
                Install Attune Lite
              </a>
              <a
                href="https://github.com/Smart-AI-Memory/attune-ai"
                target="_blank"
                rel="noopener noreferrer"
                className="btn border-2 border-white text-white hover:bg-white hover:text-[var(--primary)] text-lg px-8 py-4"
              >
                Install Attune AI
              </a>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
