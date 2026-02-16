import Link from 'next/link';
import Image from 'next/image';
import Footer from '@/components/Footer';

export default function FrameworkPage() {
  return (
    <div className="min-h-screen">
      {/* Header */}
      <nav className="border-b border-[var(--border)] py-4">
        <div className="container flex justify-between items-center">
          <Link href="/" className="text-xl font-bold text-gradient">
            Attune AI
          </Link>
          <div className="flex gap-6">
            <Link href="/docs" className="text-sm hover:text-[var(--primary)]">Docs</Link>
            <Link href="/plugins" className="text-sm hover:text-[var(--primary)]">Plugins</Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="py-20 relative overflow-hidden">
        <div className="absolute inset-0" aria-hidden="true">
          <Image
            src="/images/AdobeStock_1773561909.jpeg"
            alt=""
            fill
            className="object-cover opacity-10"
            priority
          />
          <div className="absolute inset-0 bg-gradient-to-b from-[var(--background)] via-transparent to-[var(--background)]" />
        </div>
        <div className="container relative">
          <div className="max-w-4xl mx-auto text-center">
            <div className="flex justify-center mb-6">
              <Image
                src="/images/icons/square-terminal.svg"
                alt=""
                width={56}
                height={56}
                className="opacity-70"
              />
            </div>
            <h1 className="text-5xl font-bold mb-6">
              Power Tools for <span className="text-gradient">Claude Code</span>
            </h1>
            <p className="text-2xl text-[var(--text-secondary)] mb-8">
              Enhanced workflows, Socratic agent creation, and intelligent orchestration for VS Code power users
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a
                href="https://github.com/Smart-AI-Memory/attune-ai"
                className="btn btn-primary"
                target="_blank"
                rel="noopener noreferrer"
              >
                View on GitHub
              </a>
              <Link href="/docs" className="btn btn-outline">
                Read Documentation
              </Link>
            </div>
            <p className="mt-6 text-sm text-[var(--muted)]">
              Apache 2.0 License • Free for Students & Small Teams • Community Driven
            </p>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 bg-[var(--border)] bg-opacity-30">
        <div className="container">
          <h2 className="text-4xl font-bold text-center mb-12">Core Features</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-6xl mx-auto">
            <div className="bg-[var(--background)] p-6 rounded-lg">
              <div className="mb-4">
                <Image src="/images/icons/heart-handshake.svg" alt="" width={32} height={32} className="opacity-70" />
              </div>
              <h3 className="text-xl font-bold mb-3">5-Level Empathy System</h3>
              <p className="text-[var(--text-secondary)]">
                Built-in framework for creating AI that progresses from reactive to anticipatory intelligence.
              </p>
            </div>

            <div className="bg-[var(--background)] p-6 rounded-lg border-2 border-[var(--primary)] border-opacity-50">
              <div className="mb-4">
                <Image src="/images/icons/file-terminal.svg" alt="" width={32} height={32} className="opacity-70" />
              </div>
              <h3 className="text-xl font-bold mb-3">Code Health Assistant</h3>
              <p className="text-[var(--text-secondary)]">
                Automated code quality checks, auto-fix capabilities, and health trend tracking via CLI.
              </p>
            </div>

            <div className="bg-[var(--background)] p-6 rounded-lg border-2 border-[var(--primary)] border-opacity-50">
              <div className="mb-4">
                <Image src="/images/icons/briefcase.svg" alt="" width={32} height={32} className="opacity-70" />
              </div>
              <h3 className="text-xl font-bold mb-3">Smart Model Routing</h3>
              <p className="text-[var(--text-secondary)]">
                80-96% cost reduction with intelligent routing: Haiku for simple tasks, Sonnet for code, Opus for architecture.
              </p>
            </div>

            <div className="bg-[var(--background)] p-6 rounded-lg border-2 border-purple-500 border-opacity-50">
              <div className="mb-4 text-3xl">🧭</div>
              <h3 className="text-xl font-bold mb-3">Meta-Orchestration <span className="text-xs font-normal text-purple-500 ml-2">v4.6</span></h3>
              <p className="text-[var(--text-secondary)]">
                6 composition patterns (Sequential, Parallel, Debate, Teaching, Refinement, Adaptive) + 7 agent templates. Agents compose themselves automatically.
              </p>
            </div>

            <div className="bg-[var(--background)] p-6 rounded-lg">
              <div className="mb-4">
                <Image src="/images/icons/square-terminal.svg" alt="" width={32} height={32} className="opacity-70" />
              </div>
              <h3 className="text-xl font-bold mb-3">Plugin Architecture</h3>
              <p className="text-[var(--text-secondary)]">
                Extensible system for building domain-specific wizards and tools.
              </p>
            </div>

            <div className="bg-[var(--background)] p-6 rounded-lg">
              <div className="mb-4">
                <Image src="/images/icons/file-terminal.svg" alt="" width={32} height={32} className="opacity-70" />
              </div>
              <h3 className="text-xl font-bold mb-3">Pattern Recognition</h3>
              <p className="text-[var(--text-secondary)]">
                Advanced pattern matching and analysis for identifying trends and trajectories.
              </p>
            </div>

            <div className="bg-[var(--background)] p-6 rounded-lg">
              <div className="mb-4">
                <Image src="/images/icons/briefcase.svg" alt="" width={32} height={32} className="opacity-70" />
              </div>
              <h3 className="text-xl font-bold mb-3">Trajectory Prediction</h3>
              <p className="text-[var(--text-secondary)]">
                Core algorithms for predicting future states based on current trajectories.
              </p>
            </div>

            <div className="bg-[var(--background)] p-6 rounded-lg border-2 border-[var(--primary)] border-opacity-50">
              <div className="mb-4 text-3xl">🎯</div>
              <h3 className="text-xl font-bold mb-3">Socratic Agent Builder <span className="text-xs font-normal text-[var(--primary)] ml-2">NEW</span></h3>
              <p className="text-[var(--text-secondary)]">
                Create custom agents through guided questions. Describe what you need, get production-ready agents.
              </p>
            </div>

            <div className="bg-[var(--background)] p-6 rounded-lg">
              <div className="mb-4">
                <Image src="/images/icons/briefcase-medical.svg" alt="" width={32} height={32} className="opacity-70" />
              </div>
              <h3 className="text-xl font-bold mb-3">Enterprise Security</h3>
              <p className="text-[var(--text-secondary)]">
                Built-in PII scrubbing, audit logging, and compliance controls.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Quick Start */}
      <section className="py-20">
        <div className="container">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-4xl font-bold text-center mb-12">Quick Start</h2>

            <div className="space-y-8">
              <div>
                <h3 className="text-2xl font-bold mb-4">Installation</h3>
                <pre className="bg-[var(--foreground)] text-[var(--background)] p-4 rounded-lg overflow-x-auto">
                  <code>pip install attune-ai</code>
                </pre>
              </div>

              <div>
                <h3 className="text-2xl font-bold mb-4">Socratic Agent Creation</h3>
                <pre className="bg-[var(--foreground)] text-[var(--background)] p-6 rounded-lg overflow-x-auto text-sm">
{`from attune.socratic import SocraticWorkflowBuilder

# Describe your goal - the framework guides you through questions
builder = SocraticWorkflowBuilder()
session = builder.start_session("I want to automate code reviews")

# Get clarifying questions
form = builder.get_next_questions(session)
print(form.questions[0].text)
# "What programming languages does your team primarily use?"

# Answer questions
session = builder.submit_answers(session, {
    "languages": ["python", "typescript"],
    "focus_areas": ["security", "performance"]
})

# Generate optimized workflow when ready
if builder.is_ready_to_generate(session):
    workflow = builder.generate_workflow(session)
    print(f"Generated {len(workflow.agents)} agents")`}
                </pre>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Architecture */}
      <section className="py-20 bg-[var(--border)] bg-opacity-30">
        <div className="container">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-4xl font-bold text-center mb-12">Architecture</h2>

            <div className="grid md:grid-cols-2 gap-8">
              <div>
                <h3 className="text-2xl font-bold mb-4">Core Components</h3>
                <ul className="space-y-3">
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--primary)] font-mono text-sm mt-1">BaseWizard</span>
                    <span className="text-[var(--text-secondary)] text-sm">
                      Abstract base class for all wizards
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--primary)] font-mono text-sm mt-1">PatternLibrary</span>
                    <span className="text-[var(--text-secondary)] text-sm">
                      Pattern recognition and matching
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--primary)] font-mono text-sm mt-1">TrajectoryAnalyzer</span>
                    <span className="text-[var(--text-secondary)] text-sm">
                      Trend analysis and prediction
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--primary)] font-mono text-sm mt-1">ContextManager</span>
                    <span className="text-[var(--text-secondary)] text-sm">
                      Context handling and state management
                    </span>
                  </li>
                </ul>
              </div>

              <div>
                <h3 className="text-2xl font-bold mb-4">Orchestration System <span className="text-sm font-normal text-purple-500">v2.9.0</span></h3>
                <ul className="space-y-3">
                  <li className="flex items-start gap-2">
                    <span className="text-purple-500 font-mono text-sm mt-1">SmartRouter</span>
                    <span className="text-[var(--text-secondary)] text-sm">
                      Natural language wizard dispatch
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-purple-500 font-mono text-sm mt-1">MemoryGraph</span>
                    <span className="text-[var(--text-secondary)] text-sm">
                      Cross-wizard knowledge sharing
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-purple-500 font-mono text-sm mt-1">ChainExecutor</span>
                    <span className="text-[var(--text-secondary)] text-sm">
                      Auto-chaining wizard workflows
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-purple-500 font-mono text-sm mt-1">WizardRegistry</span>
                    <span className="text-[var(--text-secondary)] text-sm">
                      10+ wizards with domain metadata
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-purple-500 font-mono text-sm mt-1">SocraticWorkflowBuilder</span>
                    <span className="text-[var(--text-secondary)] text-sm">
                      Guided agent creation through questions
                    </span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Community */}
      <section className="py-20">
        <div className="container">
          <div className="max-w-4xl mx-auto text-center">
            <h2 className="text-4xl font-bold mb-6">Join the Community</h2>
            <p className="text-xl text-[var(--text-secondary)] mb-12">
              Attune AI is Apache 2.0 licensed and welcomes contributions from developers worldwide.
            </p>

            <div className="grid md:grid-cols-3 gap-6">
              <a
                href="https://github.com/Smart-AI-Memory/attune-ai"
                className="p-6 border-2 border-[var(--border)] rounded-lg hover:border-[var(--primary)] transition-colors"
                target="_blank"
                rel="noopener noreferrer"
              >
                <div className="mb-3">
                  <Image src="/images/icons/file-terminal.svg" alt="" width={32} height={32} className="opacity-70" />
                </div>
                <h3 className="text-lg font-bold mb-2">Contribute on GitHub</h3>
                <p className="text-sm text-[var(--text-secondary)]">
                  Submit PRs, report issues, or help improve the docs
                </p>
              </a>

              <a
                href="https://github.com/Smart-AI-Memory/attune-ai/discussions"
                className="p-6 border-2 border-[var(--border)] rounded-lg hover:border-[var(--primary)] transition-colors"
                target="_blank"
                rel="noopener noreferrer"
              >
                <div className="mb-3">
                  <Image src="/images/icons/heart-handshake.svg" alt="" width={32} height={32} className="opacity-70" />
                </div>
                <h3 className="text-lg font-bold mb-2">Join Discussions</h3>
                <p className="text-sm text-[var(--text-secondary)]">
                  Ask questions and share your wizards
                </p>
              </a>

              <Link
                href="/framework-docs/"
                className="p-6 border-2 border-[var(--border)] rounded-lg hover:border-[var(--primary)] transition-colors"
              >
                <div className="mb-3">
                  <Image src="/images/icons/briefcase.svg" alt="" width={32} height={32} className="opacity-70" />
                </div>
                <h3 className="text-lg font-bold mb-2">Read the Docs</h3>
                <p className="text-sm text-[var(--text-secondary)]">
                  Learn to build with Attune AI
                </p>
              </Link>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
