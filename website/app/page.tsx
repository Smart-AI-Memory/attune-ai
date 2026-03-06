import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import GitHubStarsBadge from '@/components/GitHubStarsBadge';
import TestsBadge from '@/components/TestsBadge';
import { FEATURES } from '@/lib/features';
import { generateStructuredData } from '@/lib/metadata';

// Map canonical features to homepage display with links
const featureLinks: Record<string, string> = {
  'socratic-builder': '/framework-docs/',
  'workflows': '/workflows',
  'agent-templates': '/framework-docs/',
  'wizards': '/wizards',
  'model-routing': '/framework-docs/',
  'memory': '/framework-docs/',
  'security': '/framework-docs/',
  'prompt-caching': '/faq#how-does-prompt-caching-save-money',
  'semantic-caching': '/faq#what-is-semantic-caching',
};

// Select and order features for homepage
const homepageFeatureIds = [
  'socratic-builder',
  'prompt-caching',
  'workflows',
  'agent-templates',
  'semantic-caching',
  'wizards',
];

const features = homepageFeatureIds
  .map(id => FEATURES.find(f => f.id === id)!)
  .filter(Boolean)
  .map(f => ({
    icon: f.icon,
    title: f.name,
    description: f.benefitDescription,
    link: featureLinks[f.id] || '/framework-docs/',
  }));

const codeExample = `from attune.orchestration import MetaOrchestrator

# Let the framework compose the right agent team automatically
orchestrator = MetaOrchestrator()
plan = orchestrator.analyze_and_compose(
    task="Boost test coverage to 90%",
    context={"current_coverage": 75, "focus": "auth module"}
)

print(f"Strategy: {plan.strategy.value}")      # sequential
print(f"Agents: {[a.role for a in plan.agents]}")  # [Analyzer, Generator, Validator]
print(f"Estimated cost: \${plan.estimated_cost:.2f}")

# Compose into executable team with tier escalation (CHEAP → CAPABLE → PREMIUM)
team = orchestrator.compose_team(task="Boost test coverage to 90%")
result = await team.execute()
print(f"Success: {result.success}")
print(f"Total cost: \${result.total_cost:.2f}")`;


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
        <section className="relative overflow-hidden py-20 sm:py-28" aria-label="Hero">
          <div className="absolute inset-0" aria-hidden="true">
            <div className="absolute inset-0 bg-gradient-to-br from-[var(--primary)] via-transparent to-[var(--secondary)] opacity-5" />
          </div>
          <div className="container relative">
            <div className="max-w-4xl mx-auto text-center animate-fade-in">
              {/* Credibility Badges */}
              <div className="flex flex-wrap gap-3 justify-center mb-8">
                <GitHubStarsBadge />
                <TestsBadge />
                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[var(--border)] text-sm font-medium">
                  <span className="w-2 h-2 rounded-full bg-green-500"></span>
                  v3.9.0 Stable
                </span>
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-6">
                AI Workflows & Agent Orchestration for{' '}
                <span className="text-gradient">Claude Code</span>
              </h1>
              <p className="text-xl text-[var(--text-secondary)] mb-8 max-w-3xl mx-auto">
                Enhanced workflows and intelligent orchestration for Claude Code.
                Create custom agents through guided Socratic questions—no boilerplate, just describe what you need.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
                <Link
                  href="/framework-docs/getting-started/"
                  className="btn btn-primary text-lg px-8 py-4"
                  aria-label="Get started with the framework"
                >
                  pip install attune-ai
                </Link>
                <Link
                  href="/workflows"
                  className="btn btn-outline text-lg px-8 py-4"
                  aria-label="Explore Workflows"
                >
                  Explore Workflows
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* Code Example */}
        <section className="py-16 bg-[var(--border)] bg-opacity-30" aria-label="Code example">
          <div className="container">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl font-bold text-center mb-8">
                Get Started in 5 Lines of Python
              </h2>
              <div className="bg-[#1e1e1e] rounded-xl overflow-hidden shadow-2xl">
                <div className="flex items-center gap-2 px-4 py-3 bg-[#2d2d2d] border-b border-[#3d3d3d]">
                  <div className="w-3 h-3 rounded-full bg-[#ff5f56]"></div>
                  <div className="w-3 h-3 rounded-full bg-[#ffbd2e]"></div>
                  <div className="w-3 h-3 rounded-full bg-[#27ca40]"></div>
                  <span className="ml-2 text-sm text-gray-400">main.py</span>
                </div>
                <pre className="p-6 overflow-x-auto text-sm">
                  <code className="text-gray-300">{codeExample}</code>
                </pre>
              </div>
            </div>
          </div>
        </section>

        {/* Features Grid */}
        <section className="py-20" aria-label="Features">
          <div className="container">
            <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4">
              Built-in AI Workflow Features
            </h2>
            <p className="text-center text-[var(--text-secondary)] mb-12 max-w-2xl mx-auto">
              Advanced capabilities for developers who want more from Claude Code.
            </p>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
              {features.map((feature) => (
                <Link
                  key={feature.title}
                  href={feature.link}
                  className="group bg-[var(--background)] p-6 rounded-xl border-2 border-[var(--border)] hover:border-[var(--primary)] hover:shadow-lg transition-all"
                >
                  <div className="text-4xl mb-4">{feature.icon}</div>
                  <h3 className="text-xl font-bold mb-2 group-hover:text-[var(--primary)] transition-colors">
                    {feature.title}
                  </h3>
                  <p className="text-[var(--text-secondary)]">
                    {feature.description}
                  </p>
                </Link>
              ))}
            </div>
          </div>
        </section>


        {/* How It Works */}
        <section className="py-20" aria-label="How it works">
          <div className="container">
            <div className="max-w-4xl mx-auto bg-gradient-to-r from-[var(--primary)] to-[var(--secondary)] rounded-2xl p-8 md:p-12 text-white">
              <div className="flex flex-col md:flex-row items-center gap-8">
                <div className="flex-1">
                  <p className="text-sm font-medium opacity-80 mb-2">SOCRATIC AGENT BUILDER</p>
                  <h3 className="text-2xl md:text-3xl font-bold mb-4">
                    Describe It. We Build It.
                  </h3>
                  <p className="opacity-90 mb-6">
                    Tell us what you need in plain English. The framework asks clarifying questions,
                    suggests capabilities, and generates production-ready agents and teams automatically.
                  </p>
                  <Link
                    href="/framework-docs/getting-started/"
                    className="inline-flex items-center gap-2 bg-white text-[var(--primary)] px-6 py-3 rounded-lg font-medium hover:bg-opacity-90 transition-colors"
                  >
                    Try It Now
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M5 12h14" />
                      <path d="m12 5 7 7-7 7" />
                    </svg>
                  </Link>
                </div>
                <div className="flex-shrink-0">
                  <div className="w-32 h-32 md:w-40 md:h-40 bg-white bg-opacity-20 rounded-2xl flex items-center justify-center">
                    <span className="text-6xl md:text-7xl">🎯</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-20 bg-[var(--border)] bg-opacity-30" aria-label="Call to action">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-3xl sm:text-4xl font-bold mb-4">
                Start Building AI Workflows Today
              </h2>
              <p className="text-xl text-[var(--text-secondary)] mb-8">
                Join power users enhancing their Claude Code workflow.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  href="/framework-docs/getting-started/"
                  className="btn btn-primary text-lg px-8 py-4"
                >
                  Read the Docs
                </Link>
                <a
                  href="https://github.com/Smart-AI-Memory/attune-ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-outline text-lg px-8 py-4"
                >
                  Star on GitHub
                </a>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
