import type { Metadata } from 'next';
import Link from 'next/link';
import Image from 'next/image';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata } from '@/lib/metadata';
import { getPricingSummary } from '@/lib/features';

export const metadata: Metadata = generateMetadata({
  title: 'Open Source - Apache 2.0',
  description: 'Attune AI is now fully open source under Apache 2.0. Free for everyone, commercial use included.',
  url: 'https://smartaimemory.com/pricing',
});

export default function PricingPage() {
  return (
    <>
      <Navigation />
      <main className="min-h-screen pt-16">
        {/* Hero Section */}
        <section className="py-20 gradient-primary text-white relative overflow-hidden">
          <div className="absolute inset-0" aria-hidden="true">
            <Image
              src="/images/AdobeStock_1773561909.jpeg"
              alt=""
              fill
              className="object-cover opacity-30 mix-blend-overlay"
              priority
            />
          </div>
          <div className="container relative">
            <div className="max-w-3xl mx-auto text-center">
              <div className="flex justify-center mb-6">
                <Image
                  src="/images/icons/briefcase.svg"
                  alt=""
                  width={56}
                  height={56}
                  className="invert opacity-90"
                />
              </div>
              <h1 className="text-5xl font-bold mb-6">
                Free & Open Source
              </h1>
              <p className="text-2xl mb-8 opacity-90">
                Apache License 2.0 — Free for everyone. Build whatever you want.
              </p>
              <a
                href="https://github.com/Smart-AI-Memory/attune-ai"
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-secondary text-lg px-8 py-4 inline-block"
              >
                View on GitHub →
              </a>
            </div>
          </div>
        </section>

        {/* Open Source Benefits */}
        <section className="py-20">
          <div className="container">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-4xl font-bold text-center mb-12">
                Now Fully Open Source
              </h2>

              <div className="grid md:grid-cols-2 gap-8 mb-12">
                <div className="bg-[var(--background)] border-2 border-[var(--border)] rounded-lg p-8">
                  <div className="text-4xl mb-4">🎉</div>
                  <h3 className="text-2xl font-bold mb-4">No Cost, Ever</h3>
                  <p className="text-[var(--text-secondary)]">
                    Use Attune AI completely free in personal projects, startups, or large enterprises.
                    No hidden fees, no usage limits, no license keys.
                  </p>
                </div>

                <div className="bg-[var(--background)] border-2 border-[var(--border)] rounded-lg p-8">
                  <div className="text-4xl mb-4">🔓</div>
                  <h3 className="text-2xl font-bold mb-4">Commercial Friendly</h3>
                  <p className="text-[var(--text-secondary)]">
                    Build and sell commercial products using Attune AI. Apache 2.0 is approved by most
                    legal teams and includes patent protection.
                  </p>
                </div>

                <div className="bg-[var(--background)] border-2 border-[var(--border)] rounded-lg p-8">
                  <div className="text-4xl mb-4">🛠️</div>
                  <h3 className="text-2xl font-bold mb-4">Fork & Modify</h3>
                  <p className="text-[var(--text-secondary)]">
                    Customize the framework for your needs. Create derivative works, private forks, or contribute
                    back to the community.
                  </p>
                </div>

                <div className="bg-[var(--background)] border-2 border-[var(--border)] rounded-lg p-8">
                  <div className="text-4xl mb-4">🤝</div>
                  <h3 className="text-2xl font-bold mb-4">Community Driven</h3>
                  <p className="text-[var(--text-secondary)]">
                    Contribute features, fix bugs, or just star the repo. We welcome all contributors and
                    value community feedback.
                  </p>
                </div>
              </div>

              {/* What You Get */}
              <div className="bg-gradient-to-br from-[var(--primary)] to-[var(--accent)] rounded-lg p-8 text-white">
                <h3 className="text-2xl font-bold mb-6 text-center">Everything Included</h3>
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="flex items-start gap-2">
                    <span className="text-white mt-1">✓</span>
                    <span className="text-sm">{getPricingSummary()}</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-white mt-1">✓</span>
                    <span className="text-sm">Progressive tier escalation (70-85% cost savings)</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-white mt-1">✓</span>
                    <span className="text-sm">Intelligent caching (85% hit rates)</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-white mt-1">✓</span>
                    <span className="text-sm">Multi-agent orchestration</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-white mt-1">✓</span>
                    <span className="text-sm">Claude-native features (prompt caching, 200K context)</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-white mt-1">✓</span>
                    <span className="text-sm">Full source code access</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-white mt-1">✓</span>
                    <span className="text-sm">Community support on GitHub</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-white mt-1">✓</span>
                    <span className="text-sm">Commercial use rights</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Why Open Source */}
        <section className="py-20 bg-[var(--border)] bg-opacity-30">
          <div className="container">
            <div className="max-w-3xl mx-auto">
              <h2 className="text-4xl font-bold text-center mb-12">
                Why We Went Open Source
              </h2>

              <div className="bg-[var(--background)] border border-[var(--border)] rounded-lg p-8 mb-8">
                <h3 className="text-xl font-bold mb-3">Adoption Over Revenue</h3>
                <p className="text-[var(--text-secondary)] mb-4">
                  We realized our Fair Source license was limiting adoption without generating meaningful revenue.
                  Developers want to use proven, open source tools—especially in the AI space where alternatives
                  like LangChain and LangGraph are fully open.
                </p>
                <p className="text-[var(--text-secondary)]">
                  Going Apache 2.0 lets us focus on what matters: building the best AI orchestration framework
                  and growing a community of users and contributors.
                </p>
              </div>

              <div className="bg-[var(--background)] border border-[var(--border)] rounded-lg p-8 mb-8">
                <h3 className="text-xl font-bold mb-3">Sustainable Through Services</h3>
                <p className="text-[var(--text-secondary)] mb-4">
                  Open source doesn&apos;t mean no business model. We&apos;ll monetize through:
                </p>
                <ul className="space-y-2 text-[var(--text-secondary)]">
                  <li>• <strong>Managed hosting</strong> - Attune Cloud for teams</li>
                  <li>• <strong>Enterprise features</strong> - SSO, audit logs, team management</li>
                  <li>• <strong>Support contracts</strong> - SLAs and priority assistance</li>
                  <li>• <strong>Consulting services</strong> - Help teams implement AI workflows</li>
                </ul>
                <p className="text-[var(--text-secondary)] mt-4">
                  But first, we need adoption. And that means being fully open source.
                </p>
              </div>

              <div className="bg-[var(--background)] border border-[var(--border)] rounded-lg p-8">
                <h3 className="text-xl font-bold mb-3">Community First</h3>
                <p className="text-[var(--text-secondary)]">
                  The best developer tools are built by communities, not companies. By going open source, we&apos;re
                  inviting the world to help shape Attune AI&apos;s future. Your feedback, contributions, and
                  support are what will make this project successful.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Future Plans */}
        <section className="py-20">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-4xl font-bold mb-6">
                Future Enterprise Features
              </h2>
              <p className="text-xl text-[var(--text-secondary)] mb-8">
                The core framework will always be free and open source. In the future, we may offer optional
                enterprise features for teams:
              </p>
              <div className="grid md:grid-cols-2 gap-6 text-left mb-12">
                <div className="bg-[var(--background)] border border-[var(--border)] rounded-lg p-6">
                  <h3 className="font-bold mb-2">Attune Cloud</h3>
                  <p className="text-sm text-[var(--text-secondary)]">
                    Managed hosting with automatic updates, monitoring, and team collaboration features.
                  </p>
                </div>
                <div className="bg-[var(--background)] border border-[var(--border)] rounded-lg p-6">
                  <h3 className="font-bold mb-2">Enterprise Support</h3>
                  <p className="text-sm text-[var(--text-secondary)]">
                    Priority support, SLA guarantees, and direct access to maintainers.
                  </p>
                </div>
                <div className="bg-[var(--background)] border border-[var(--border)] rounded-lg p-6">
                  <h3 className="font-bold mb-2">Advanced Security</h3>
                  <p className="text-sm text-[var(--text-secondary)]">
                    SSO, SAML, audit logs, compliance reports, and security scanning.
                  </p>
                </div>
                <div className="bg-[var(--background)] border border-[var(--border)] rounded-lg p-6">
                  <h3 className="font-bold mb-2">Custom Workflows</h3>
                  <p className="text-sm text-[var(--text-secondary)]">
                    Professional services to build custom AI workflows for your specific needs.
                  </p>
                </div>
              </div>
              <p className="text-[var(--text-secondary)]">
                <strong>Note:</strong> These features don&apos;t exist yet. We&apos;re focused on building adoption
                and community first. Interested in enterprise features? <Link href="/contact" className="text-[var(--primary)] hover:underline">Let us know</Link>.
              </p>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-20 gradient-primary text-white">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-4xl font-bold mb-6">
                Ready to Get Started?
              </h2>
              <p className="text-xl mb-8 opacity-90">
                Free and open source forever. Build the next generation of AI applications.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <a
                  href="https://github.com/Smart-AI-Memory/attune-ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-secondary text-lg px-8 py-4"
                >
                  Star on GitHub
                </a>
                <Link
                  href="/framework-docs/tutorials/quickstart/"
                  className="btn btn-outline-white text-lg px-8 py-4"
                >
                  View Documentation
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
