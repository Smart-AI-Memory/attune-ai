import Link from 'next/link';
import Footer from '@/components/Footer';

export default function PluginsPage() {
  return (
    <div className="min-h-screen">
      {/* Header */}
      <nav className="border-b border-[var(--border)] py-4">
        <div className="container flex justify-between items-center">
          <Link href="/" className="text-xl font-bold text-gradient">
            Empathy
          </Link>
          <div className="flex gap-6">
            <Link href="/framework" className="text-sm hover:text-[var(--primary)]">Framework</Link>
            <Link href="/docs" className="text-sm hover:text-[var(--primary)]">Docs</Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="py-20 gradient-primary text-white">
        <div className="container">
          <div className="max-w-3xl mx-auto text-center">
            <h1 className="text-5xl font-bold mb-6">
              Commercial Plugins
            </h1>
            <p className="text-2xl mb-8 opacity-90">
              Production-ready Level 4 Anticipatory AI for Software Development and Healthcare
            </p>
            <a href="https://github.com/Smart-AI-Memory/attune-ai" target="_blank" rel="noopener noreferrer" className="btn bg-white text-[var(--primary)] hover:bg-gray-100">
              View on GitHub
            </a>
          </div>
        </div>
      </section>

      {/* Software Development Plugin */}
      <section className="py-20">
        <div className="container">
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-12">
              <div className="text-6xl mb-4">💻</div>
              <h2 className="text-4xl font-bold mb-4">Software Development Plugin</h2>
              <p className="text-xl text-[var(--text-secondary)]">
                Transform how you build software with anticipatory intelligence
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8 mb-12">
              <div className="bg-[var(--border)] bg-opacity-30 p-6 rounded-lg">
                <h3 className="text-xl font-bold mb-3">Enhanced Testing Wizard</h3>
                <p className="text-[var(--text-secondary)] mb-4">
                  Goes beyond code coverage to predict which untested code will cause bugs.
                </p>
                <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Test quality analysis</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Bug-risk prediction</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Brittle test detection</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Smart test suggestions</span>
                  </li>
                </ul>
              </div>

              <div className="bg-[var(--border)] bg-opacity-30 p-6 rounded-lg">
                <h3 className="text-xl font-bold mb-3">Performance Profiling Wizard</h3>
                <p className="text-[var(--text-secondary)] mb-4">
                  Predicts performance degradation before it becomes critical.
                </p>
                <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Trajectory analysis</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Bottleneck prediction</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>N+1 query detection</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Performance forecasting</span>
                  </li>
                </ul>
              </div>

              <div className="bg-[var(--border)] bg-opacity-30 p-6 rounded-lg">
                <h3 className="text-xl font-bold mb-3">Security Analysis Wizard</h3>
                <p className="text-[var(--text-secondary)] mb-4">
                  Identifies which vulnerabilities will actually be exploited.
                </p>
                <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>OWASP pattern detection</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Exploit likelihood scoring</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Attack surface analysis</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Prioritized remediation</span>
                  </li>
                </ul>
              </div>
            </div>

            <div className="bg-[var(--primary)] bg-opacity-10 border-l-4 border-[var(--primary)] p-6 rounded-r-lg">
              <h3 className="text-xl font-bold mb-2">10 Smart Wizards</h3>
              <p className="text-[var(--text-secondary)]">
                The framework includes 10 specialized wizards covering security audits, code review, bug prediction,
                performance analysis, refactoring, test generation, documentation, dependency checks, release prep, and research.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Healthcare Plugin */}
      <section className="py-20 bg-[var(--border)] bg-opacity-30">
        <div className="container">
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-12">
              <div className="text-6xl mb-4">🏥</div>
              <h2 className="text-4xl font-bold mb-4">Healthcare Plugin</h2>
              <p className="text-xl text-[var(--text-secondary)]">
                Anticipatory intelligence for patient care and clinical decision support
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8 mb-12">
              <div className="bg-[var(--background)] p-6 rounded-lg">
                <h3 className="text-xl font-bold mb-3">Patient Trajectory Wizard</h3>
                <p className="text-[var(--text-secondary)] mb-4">
                  Predicts patient deterioration before clinical crisis occurs.
                </p>
                <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Vital sign trend analysis</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Early warning scores</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Deterioration prediction</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Intervention recommendations</span>
                  </li>
                </ul>
              </div>

              <div className="bg-[var(--background)] p-6 rounded-lg">
                <h3 className="text-xl font-bold mb-3">Treatment Optimization Wizard</h3>
                <p className="text-[var(--text-secondary)] mb-4">
                  Anticipates medication interactions and treatment complications.
                </p>
                <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Drug interaction prediction</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Adverse event forecasting</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Dosage optimization</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Treatment trajectory analysis</span>
                  </li>
                </ul>
              </div>

              <div className="bg-[var(--background)] p-6 rounded-lg">
                <h3 className="text-xl font-bold mb-3">Risk Assessment Wizard</h3>
                <p className="text-[var(--text-secondary)] mb-4">
                  Identifies high-risk patients proactively for early intervention.
                </p>
                <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Multi-factor risk scoring</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Readmission prediction</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Complication forecasting</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Resource allocation guidance</span>
                  </li>
                </ul>
              </div>
            </div>

            <div className="bg-[var(--secondary)] bg-opacity-10 border-l-4 border-[var(--secondary)] p-6 rounded-r-lg">
              <h3 className="text-xl font-bold mb-2">Clinical Grade Predictions</h3>
              <p className="text-[var(--text-secondary)]">
                The Healthcare Plugin is designed for clinical decision support, built with medical
                professionals and validated against real-world patient data.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Licensing */}
      <section className="py-20">
        <div className="container">
          <div className="max-w-3xl mx-auto">
            <h2 className="text-3xl font-bold text-center mb-12">Licensing</h2>

            <div className="space-y-6">
              <div className="bg-[var(--border)] bg-opacity-30 p-6 rounded-lg">
                <h3 className="text-xl font-bold mb-3">Fair Source License</h3>
                <ul className="space-y-2 text-[var(--text-secondary)]">
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Free for students, educators, and teams with 5 or fewer employees</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Full access to all 10 wizards and 14 workflows</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Source-available for reading and modification</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[var(--success)]">✓</span>
                    <span>Community support via GitHub</span>
                  </li>
                </ul>
              </div>

              <div className="bg-[var(--border)] bg-opacity-30 p-6 rounded-lg">
                <h3 className="text-xl font-bold mb-3">Commercial Licensing</h3>
                <p className="text-[var(--text-secondary)] mb-4">
                  For businesses with 6+ employees, <Link href="/contact?topic=volume" className="text-[var(--primary)] hover:underline">contact us</Link> for commercial licensing options.
                </p>
                <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
                  <li className="flex items-start gap-2">
                    <span>•</span>
                    <span>One license covers all environments (dev, staging, production, CI/CD)</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span>•</span>
                    <span>Email support and priority bug fixes</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span>•</span>
                    <span>Volume discounts available for larger teams</span>
                  </li>
                </ul>
              </div>

              <div className="bg-[var(--accent)] bg-opacity-10 border-l-4 border-[var(--accent)] p-6 rounded-r-lg">
                <h3 className="text-xl font-bold mb-2">Enterprise Options</h3>
                <p className="text-[var(--text-secondary)]">
                  Need custom wizard development, dedicated support, or on-premises deployment?
                  <Link href="/contact?topic=volume" className="text-[var(--primary)] hover:underline ml-1">Contact sales</Link> for enterprise pricing.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 gradient-primary text-white">
        <div className="container">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-4xl font-bold mb-6">
              Ready to Get Started?
            </h2>
            <p className="text-xl mb-8 opacity-90">
              Free for small teams. Fair pricing for everyone else.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a href="https://github.com/Smart-AI-Memory/attune-ai" target="_blank" rel="noopener noreferrer" className="btn bg-white text-[var(--primary)] hover:bg-gray-100 text-lg px-8 py-4">
                Get Started Free
              </a>
              <Link href="/pricing" className="btn border-2 border-white text-white hover:bg-white hover:text-[var(--primary)] text-lg px-8 py-4">
                View Pricing
              </Link>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
