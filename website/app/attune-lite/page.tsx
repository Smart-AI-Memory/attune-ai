import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata as generateSEOMetadata } from '@/lib/metadata';
import { liteSkills } from '@/lib/attune-lite-skills';

export const metadata: Metadata = generateSEOMetadata({
  title: 'Attune Lite — Free Claude Code Plugin',
  description:
    '5 AI-powered developer workflows for Claude Code. Code review, security audit, smart testing, bug prediction, and doc generation. Zero config, no dependencies.',
  url: 'https://smartaimemory.com/attune-lite',
  keywords: [
    'Claude Code plugin',
    'Attune Lite',
    'AI code review plugin',
    'AI security audit',
    'AI test generation',
    'bug prediction tool',
    'free Claude Code plugin',
    'Claude Code plugin free',
  ],
});

export default function AttuneLitePage() {
  return (
    <div id="main-content" className="min-h-screen">
      <Navigation />

      {/* Hero */}
      <section className="pt-32 pb-20 gradient-accent text-white">
        <div className="container">
          <div className="max-w-3xl mx-auto text-center">
            <p className="text-sm font-semibold uppercase tracking-wider mb-4 opacity-80">
              Free Claude Code Plugin
            </p>
            <h1 className="text-5xl font-bold mb-6">Attune Lite</h1>
            <p className="text-xl mb-4 opacity-90">
              5 AI-powered developer workflows, right inside Claude Code.
              Zero config. No dependencies. No pip install.
            </p>
            <p className="text-lg mb-8 opacity-75">
              Type a slash command and get a structured, multi-agent report
              in seconds.
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
              <Link
                href="#skills"
                className="btn border-2 border-white text-white hover:bg-white hover:text-[var(--primary)] text-lg px-8 py-4"
              >
                See All 5 Skills
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20">
        <div className="container">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-3xl font-bold text-center mb-12">
              How It Works
            </h2>

            <div className="grid md:grid-cols-3 gap-8">
              <div className="text-center">
                <div className="text-4xl mb-4">1</div>
                <h3 className="text-xl font-bold mb-2">Install</h3>
                <p className="text-[var(--text-secondary)]">
                  Add the plugin to Claude Code. No pip install,
                  no API keys, no config files.
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
          </div>
        </div>
      </section>

      {/* Skills */}
      <section id="skills" className="py-20 bg-[var(--border)] bg-opacity-30">
        <div className="container">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-3xl font-bold text-center mb-4">
              5 Built-in Skills
            </h2>
            <p className="text-center text-[var(--text-secondary)] mb-12 max-w-2xl mx-auto">
              Each skill runs multiple specialized AI agents that analyze
              your code from different angles and produce a unified report.
            </p>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
              {liteSkills.map((skill) => (
                <div
                  key={skill.command}
                  className="bg-[var(--background)] p-6 rounded-lg"
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
          </div>
        </div>
      </section>

      {/* What Makes It Different */}
      <section className="py-20">
        <div className="container">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-3xl font-bold text-center mb-12">
              What Makes It Different
            </h2>

            <div className="grid md:grid-cols-2 gap-8">
              <div className="bg-[var(--border)] bg-opacity-30 p-6 rounded-lg">
                <h3 className="text-xl font-bold mb-3">
                  Prompt-Based, Not Code-Based
                </h3>
                <p className="text-[var(--text-secondary)]">
                  Each skill is a self-contained prompt with agent
                  orchestration instructions. Claude Code executes them
                  natively &mdash; no Python runtime, no subprocess calls,
                  no external dependencies.
                </p>
              </div>

              <div className="bg-[var(--border)] bg-opacity-30 p-6 rounded-lg">
                <h3 className="text-xl font-bold mb-3">
                  Multi-Agent Architecture
                </h3>
                <p className="text-[var(--text-secondary)]">
                  Every skill deploys multiple specialized agents (e.g.,
                  architecture reviewer, security scanner, performance
                  analyst) that each focus on their domain and contribute
                  to a unified report.
                </p>
              </div>

              <div className="bg-[var(--border)] bg-opacity-30 p-6 rounded-lg">
                <h3 className="text-xl font-bold mb-3">
                  Budget-Aware by Design
                </h3>
                <p className="text-[var(--text-secondary)]">
                  Skills are scoped to produce focused, high-value findings
                  rather than exhaustive output. You get the top issues,
                  not a wall of noise.
                </p>
              </div>

              <div className="bg-[var(--border)] bg-opacity-30 p-6 rounded-lg">
                <h3 className="text-xl font-bold mb-3">
                  Structured Output
                </h3>
                <p className="text-[var(--text-secondary)]">
                  Results come as markdown tables with file locations,
                  severity ratings, and actionable descriptions &mdash;
                  ready to act on immediately.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Want More? */}
      <section className="py-20 bg-[var(--border)] bg-opacity-30">
        <div className="container">
          <div className="max-w-3xl mx-auto">
            <div className="bg-[var(--primary)] bg-opacity-10 border-l-4 border-[var(--primary)] p-6 rounded-r-lg">
              <h3 className="text-xl font-bold mb-2">
                Want the Full Experience?
              </h3>
              <p className="text-[var(--text-secondary)] mb-4">
                Attune Lite showcases 5 of Attune AI&apos;s best workflows.
                The full plugin includes 17 workflows, 5 wizards,
                14 agent templates, CLI tooling, MCP integration, and
                multi-agent orchestration.
              </p>
              <Link
                href="/attune-plugin"
                className="btn btn-primary text-sm"
              >
                Compare Both Plugins
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 gradient-accent text-white">
        <div className="container">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-4xl font-bold mb-6">Get Started in Seconds</h2>
            <p className="text-xl mb-8 opacity-90">
              Install the plugin, type a command, and see results. Free and
              open source.
            </p>
            <a
              href="https://github.com/Smart-AI-Memory/attune-lite"
              target="_blank"
              rel="noopener noreferrer"
              className="btn bg-white text-[var(--primary)] hover:bg-gray-100 text-lg px-8 py-4"
            >
              Install Attune Lite
            </a>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
