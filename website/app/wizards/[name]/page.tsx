import { notFound } from 'next/navigation';
import Link from 'next/link';
import type { Metadata } from 'next';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata as generateSEOMetadata, generateStructuredData } from '@/lib/metadata';
import { wizards, tierColors, tierLabels, getWizardByName } from '@/lib/wizards';

interface PageProps {
  params: Promise<{ name: string }>;
}

export async function generateStaticParams() {
  return wizards.map((w) => ({ name: w.name }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { name } = await params;
  const wizard = getWizardByName(name);

  if (!wizard) {
    return { title: 'Wizard Not Found' };
  }

  return generateSEOMetadata({
    title: `${wizard.displayName} Wizard — AI ${wizard.domain} Tool for Claude Code`,
    description: wizard.longDescription,
    url: `https://smartaimemory.com/wizards/${wizard.name}`,
    keywords: [
      ...wizard.keywords,
      'Claude Code',
      'AI developer tool',
      `AI ${wizard.domain.toLowerCase()} tool`,
      'Attune AI wizard',
    ],
  });
}

export default async function WizardDetailPage({ params }: PageProps) {
  const { name } = await params;
  const wizard = getWizardByName(name);

  if (!wizard) {
    notFound();
  }

  const breadcrumbSchema = generateStructuredData('breadcrumb', {
    items: [
      { name: 'Home', url: 'https://smartaimemory.com' },
      { name: 'Wizards', url: 'https://smartaimemory.com/wizards' },
      {
        name: wizard.displayName,
        url: `https://smartaimemory.com/wizards/${wizard.name}`,
      },
    ],
  });

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbSchema) }}
      />
      <Navigation />
      <main id="main-content" className="min-h-screen pt-16">
        {/* Hero */}
        <section className="py-16 bg-gradient-to-b from-[var(--border)] to-transparent">
          <div className="container">
            <div className="max-w-3xl mx-auto">
              <nav className="mb-6 text-sm text-[var(--muted)]">
                <Link href="/wizards" className="hover:text-[var(--primary)] transition-colors">
                  ← All Wizards
                </Link>
              </nav>
              <div className="flex items-center gap-4 mb-4">
                <span
                  className={`px-3 py-1 text-sm font-medium rounded border ${tierColors[wizard.tier]}`}
                >
                  {wizard.tier} — {tierLabels[wizard.tier]}
                </span>
                <span className="text-[var(--muted)] text-sm">{wizard.domain}</span>
              </div>
              <h1 className="text-4xl sm:text-5xl font-bold mb-6">
                {wizard.displayName} Wizard
              </h1>
              <p className="text-xl text-[var(--text-secondary)]">
                {wizard.longDescription}
              </p>
            </div>
          </div>
        </section>

        {/* Details */}
        <section className="py-16">
          <div className="container">
            <div className="max-w-3xl mx-auto space-y-12">
              {/* CLI Usage */}
              <div>
                <h2 className="text-2xl font-bold mb-4">Usage</h2>
                <div className="bg-[var(--border)] rounded-lg p-4 font-mono text-sm">
                  <span className="text-[var(--muted)]">$ </span>
                  {wizard.cliExample}
                </div>
                <p className="mt-4 text-[var(--text-secondary)]">
                  Requires{' '}
                  <a
                    href="https://pypi.org/project/attune-ai/"
                    className="text-[var(--primary)] hover:underline"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    attune-ai
                  </a>{' '}
                  and a configured Anthropic API key.
                </p>
              </div>

              {/* Install CTA */}
              <div className="bg-[var(--background)] border border-[var(--border)] rounded-xl p-8">
                <h2 className="text-2xl font-bold mb-3">Get Started</h2>
                <p className="text-[var(--text-secondary)] mb-6">
                  Install Attune AI with pip and run your first wizard in minutes.
                </p>
                <div className="bg-[var(--border)] rounded-lg p-4 font-mono text-sm mb-6">
                  <span className="text-[var(--muted)]">$ </span>pip install attune-ai
                </div>
                <div className="flex gap-4">
                  <Link href="/framework-docs/" className="btn btn-primary">
                    View Documentation
                  </Link>
                  <Link href="/wizards" className="btn btn-outline">
                    All Wizards
                  </Link>
                </div>
              </div>

              {/* Related Wizards */}
              <div>
                <h2 className="text-2xl font-bold mb-6">Other Wizards</h2>
                <div className="grid sm:grid-cols-2 gap-4">
                  {wizards
                    .filter((w) => w.name !== wizard.name)
                    .slice(0, 4)
                    .map((w) => (
                      <Link
                        key={w.name}
                        href={`/wizards/${w.name}`}
                        className="group p-4 rounded-lg border border-[var(--border)] hover:border-[var(--primary)] transition-colors block"
                      >
                        <div className="font-semibold group-hover:text-[var(--primary)] transition-colors mb-1">
                          {w.displayName}
                        </div>
                        <div className="text-sm text-[var(--text-secondary)] line-clamp-2">
                          {w.description}
                        </div>
                      </Link>
                    ))}
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
