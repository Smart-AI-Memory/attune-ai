import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import GitHubStarsBadge from '@/components/GitHubStarsBadge';
import TestsBadge from '@/components/TestsBadge';
import { generateStructuredData } from '@/lib/metadata';

const codeExample = `from attune.workflows import list_workflows

# See all 18 available workflows
workflows = list_workflows()
for wf in workflows:
    print(f"{wf['name']:20s} stages={len(wf.get('stages', []))}")

# Run a security audit on your codebase
from attune.workflows.security_audit import SecurityAuditWorkflow

audit = SecurityAuditWorkflow()
result = await audit.execute(path="./src")
print(f"Score: {result.final_output.get('health_score')}/100")
print(f"Cost: \${result.cost_report.total_cost:.2f}")`;


export default function Home() {
  const softwareSchema = generateStructuredData('product');

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(softwareSchema),
        }}
      />
      <Navigation />
      <main id="main-content" className="min-h-screen pt-16">
        {/* Hero Section */}
        <section className="relative overflow-hidden px-6 py-24 md:py-32" aria-label="Hero">
          <div className="max-w-7xl mx-auto">
            <div className="grid lg:grid-cols-2 gap-16 items-center">
              <div className="z-10">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--surface-container-high)] text-[var(--primary)] text-xs font-bold tracking-widest mb-6 uppercase">
                  <span>v5.1.2</span>
                  <span className="w-1 h-1 rounded-full bg-[var(--primary)]"></span>
                  <span className="opacity-80">18 Workflows</span>
                </div>
                <h1 className="text-5xl md:text-7xl font-extrabold tracking-tighter mb-8 leading-[1.1]">
                  AI Workflows &amp; Agent Orchestration{' '}
                  <span className="text-[var(--primary)]">for Claude Code</span>
                </h1>
                <p className="text-lg md:text-xl text-[var(--text-secondary)] mb-10 max-w-xl leading-relaxed">
                  18 multi-agent workflows for code review, security, testing,
                  and release. 30 MCP tools. 10 auto-invoking skills. Just
                  type <code className="bg-[var(--surface-container-high)] px-1.5 py-0.5 rounded text-sm">/attune</code> and go.
                </p>
                <div className="flex flex-col sm:flex-row gap-4">
                  <div className="flex items-center bg-[var(--foreground)] text-[var(--background)] px-4 py-3 rounded-lg font-mono text-sm group cursor-pointer border border-white/10">
                    <span className="opacity-50 mr-2">$</span>
                    <span>pip install 'attune-ai[developer]'</span>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="ml-4 opacity-40 group-hover:opacity-100 transition-opacity">
                      <rect width="14" height="14" x="8" y="8" rx="2" ry="2"/>
                      <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>
                    </svg>
                  </div>
                  <Link
                    href="/workflows"
                    className="bg-[var(--surface-container-high)] text-[var(--foreground)] px-8 py-3 rounded-lg font-bold hover:bg-[var(--surface-container-highest)] transition-colors text-center"
                  >
                    Explore Workflows
                  </Link>
                </div>
                {/* Trust badges */}
                <div className="flex flex-wrap gap-3 mt-8">
                  <GitHubStarsBadge />
                  <TestsBadge />
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[var(--surface-container-high)] text-xs font-medium">
                    Apache 2.0
                  </span>
                </div>
              </div>

              {/* Agent orchestrator visual */}
              <div className="relative">
                <div className="relative z-10 rounded-2xl overflow-hidden bg-[var(--surface-container-low)] p-8 border border-[var(--border)]/15 shadow-2xl">
                  <div className="flex items-center gap-2 mb-6">
                    <div className="w-3 h-3 rounded-full bg-red-500/40"></div>
                    <div className="w-3 h-3 rounded-full bg-yellow-500/40"></div>
                    <div className="w-3 h-3 rounded-full bg-green-500/40"></div>
                    <span className="ml-auto text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-widest">Attune AI v5.1.2</span>
                  </div>
                  <div className="space-y-4">
                    <div className="h-4 bg-[var(--surface-container-high)] rounded w-3/4"></div>
                    <div className="h-4 bg-[var(--surface-container-high)] rounded w-1/2"></div>
                    <div className="grid grid-cols-3 gap-4 py-4">
                      <div className="h-20 rounded-lg bg-[var(--primary)]/10 border border-[var(--primary)]/20 flex flex-col items-center justify-center">
                        <span className="text-2xl mb-1">🔍</span>
                        <span className="text-[10px] font-bold text-[var(--primary)]">SCAN</span>
                      </div>
                      <div className="h-20 rounded-lg bg-[var(--secondary)]/10 border border-[var(--secondary)]/20 flex flex-col items-center justify-center">
                        <span className="text-2xl mb-1">🧠</span>
                        <span className="text-[10px] font-bold text-[var(--secondary)]">ANALYZE</span>
                      </div>
                      <div className="h-20 rounded-lg bg-[var(--surface-container-highest)] border border-[var(--border)]/30 flex flex-col items-center justify-center">
                        <span className="text-2xl mb-1">📋</span>
                        <span className="text-[10px] font-bold text-[var(--text-secondary)]">REPORT</span>
                      </div>
                    </div>
                    <div className="h-4 bg-[var(--surface-container-high)] rounded w-full opacity-60"></div>
                    <div className="h-4 bg-[var(--surface-container-high)] rounded w-2/3 opacity-60"></div>
                  </div>
                  {/* Floating insight */}
                  <div className="absolute -bottom-4 -right-4 glass-panel p-5 rounded-xl shadow-xl max-w-[220px]">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm">✨</span>
                      <span className="text-[10px] font-bold text-[var(--foreground)] tracking-wider uppercase">Workflow Result</span>
                    </div>
                    <p className="text-xs text-[var(--text-secondary)] leading-relaxed">Security audit complete. Score: <span className="text-[var(--secondary)] font-bold">95/100</span>. Cost: $0.03.</p>
                  </div>
                </div>
                {/* Background blur */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[140%] h-[140%] bg-gradient-to-tr from-[var(--surface-container-high)]/50 to-transparent rounded-full blur-3xl -z-10"></div>
              </div>
            </div>
          </div>
        </section>

        {/* Code Example Section */}
        <section className="py-24 bg-[var(--surface-container-low)]" aria-label="Code example">
          <div className="max-w-7xl mx-auto px-6">
            <div className="flex flex-col md:flex-row gap-16 items-start">
              <div className="md:w-1/3">
                <h2 className="text-3xl font-extrabold mb-6">Start Building in Seconds.</h2>
                <p className="text-[var(--text-secondary)] mb-8 leading-relaxed">
                  Install from PyPI and run your first workflow. No API key needed in Claude Code — workflows run as skills using your subscription.
                </p>
                <ul className="space-y-4">
                  <li className="flex items-center gap-3">
                    <span className="text-[var(--secondary)]">✓</span>
                    <span className="font-medium text-sm">Native Claude Code Plugin</span>
                  </li>
                  <li className="flex items-center gap-3">
                    <span className="text-[var(--secondary)]">✓</span>
                    <span className="font-medium text-sm">30 MCP Tools Built In</span>
                  </li>
                  <li className="flex items-center gap-3">
                    <span className="text-[var(--secondary)]">✓</span>
                    <span className="font-medium text-sm">Open Source — Apache 2.0</span>
                  </li>
                </ul>
              </div>
              <div className="md:w-2/3 w-full">
                <div className="bg-[#213145] rounded-xl overflow-hidden shadow-2xl">
                  <div className="flex items-center px-4 py-2 bg-[#2a3b50] border-b border-white/5">
                    <span className="text-[10px] font-mono text-white/50 uppercase tracking-widest">workflow_example.py</span>
                    <div className="ml-auto flex gap-1.5">
                      <div className="w-2.5 h-2.5 rounded-full bg-white/10"></div>
                      <div className="w-2.5 h-2.5 rounded-full bg-white/10"></div>
                    </div>
                  </div>
                  <div className="p-6 font-mono text-sm overflow-x-auto">
                    <pre className="text-white/90 leading-relaxed"><code>{codeExample}</code></pre>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Features Grid */}
        <section className="py-32 px-6 max-w-7xl mx-auto" aria-label="Features">
          <div className="text-center mb-20">
            <span className="text-xs font-bold text-[var(--primary)] tracking-[0.2em] uppercase mb-4 block">Core Capabilities</span>
            <h2 className="text-4xl md:text-5xl font-extrabold">What Attune AI Does</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="group bg-[var(--surface)] rounded-2xl p-8 hover:bg-[var(--surface-container-low)] transition-all duration-300 hover:scale-[1.02]">
              <div className="w-14 h-14 rounded-xl bg-[var(--primary)]/10 flex items-center justify-center mb-8 group-hover:bg-[var(--primary)] transition-colors">
                <span className="text-3xl group-hover:brightness-0 group-hover:invert transition-all">🤖</span>
              </div>
              <h3 className="text-xl font-bold mb-4">18 Multi-Agent Workflows</h3>
              <p className="text-[var(--text-secondary)] leading-relaxed text-sm">
                Code review, security audit, test generation, release prep — each runs a specialist team of 2-6 Claude subagents with intelligent model routing.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="group bg-[var(--surface)] rounded-2xl p-8 hover:bg-[var(--surface-container-low)] transition-all duration-300 hover:scale-[1.02]">
              <div className="w-14 h-14 rounded-xl bg-[var(--secondary)]/10 flex items-center justify-center mb-8 group-hover:bg-[var(--secondary)] transition-colors">
                <span className="text-3xl group-hover:brightness-0 group-hover:invert transition-all">💬</span>
              </div>
              <h3 className="text-xl font-bold mb-4">Socratic Discovery</h3>
              <p className="text-[var(--text-secondary)] leading-relaxed text-sm">
                Workflows ask clarifying questions before executing — what scope? which files? what depth? — so you get exactly the analysis you need.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="group bg-[var(--surface)] rounded-2xl p-8 hover:bg-[var(--surface-container-low)] transition-all duration-300 hover:scale-[1.02]">
              <div className="w-14 h-14 rounded-xl bg-[var(--surface-container-high)] flex items-center justify-center mb-8 group-hover:bg-[var(--foreground)] transition-colors">
                <span className="text-3xl group-hover:brightness-0 group-hover:invert transition-all">🧙</span>
              </div>
              <h3 className="text-xl font-bold mb-4">Smart Wizards</h3>
              <p className="text-[var(--text-secondary)] leading-relaxed text-sm">
                Pre-configured workflow templates for Claude Code. Deploy multi-step guided workflows — from security audits to release prep — without writing boilerplate.
              </p>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="max-w-7xl mx-auto px-6 pb-24" aria-label="Call to action">
          <div className="grid lg:grid-cols-5 gap-8 items-center">
            <div className="lg:col-span-3 hero-gradient rounded-3xl p-12 text-white relative overflow-hidden">
              <div className="relative z-10">
                <h3 className="text-3xl font-extrabold mb-6">Ready to automate your dev workflows?</h3>
                <p className="text-white/80 text-lg mb-8 max-w-lg">
                  Install from PyPI. Type <code className="bg-white/20 px-1.5 py-0.5 rounded text-sm">/attune</code> in Claude Code. Go.
                </p>
                <div className="flex flex-col sm:flex-row gap-4">
                  <Link
                    href="/framework-docs/getting-started/"
                    className="bg-white text-[var(--primary)] px-8 py-3 rounded-lg font-bold hover:bg-[var(--surface-container-low)] transition-colors text-center"
                  >
                    Read the Docs
                  </Link>
                  <a
                    href="https://github.com/Smart-AI-Memory/attune-ai"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="border border-white/30 text-white px-8 py-3 rounded-lg font-bold hover:bg-white/10 transition-colors text-center"
                  >
                    Star on GitHub
                  </a>
                </div>
              </div>
              <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2 blur-3xl"></div>
            </div>

            <div className="lg:col-span-2 space-y-6">
              <div className="p-6 border border-[var(--border)]/15 rounded-2xl bg-[var(--surface-container-low)]">
                <div className="flex items-center gap-4 mb-3">
                  <span className="text-[var(--primary)]">🔒</span>
                  <span className="font-bold">Security Built In</span>
                </div>
                <p className="text-xs text-[var(--text-secondary)]">
                  Path traversal protection, SSRF validation, rate limiting, module import restrictions, and PreToolUse security hooks.
                </p>
              </div>
              <div className="p-6 border border-[var(--border)]/15 rounded-2xl bg-[var(--surface-container-low)]">
                <div className="flex items-center gap-4 mb-3">
                  <span className="text-[var(--secondary)]">💰</span>
                  <span className="font-bold">Cost-Optimized Routing</span>
                </div>
                <p className="text-xs text-[var(--text-secondary)]">
                  Opus for security, Sonnet for analysis, Haiku for scanning. Right model per task with configurable budget caps ($0.50 – $5.00).
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
