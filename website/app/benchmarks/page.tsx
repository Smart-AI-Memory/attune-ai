import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata as genMeta, generateStructuredData } from '@/lib/metadata';
import { METRICS } from '@/lib/features';

export const metadata: Metadata = genMeta({
  title: 'Benchmarks & Methodology',
  description:
    'How Attune AI measures its published numbers: test suite floor, ' +
    'enforced coverage, and RAG faithfulness — each with the CI gate ' +
    'that keeps it honest and links to the live source.',
  url: 'https://smartaimemory.com/benchmarks',
});

const REPO = 'https://github.com/Smart-AI-Memory/attune-ai';

interface Methodology {
  stat: string;
  label: string;
  what: string;
  how: string;
  gate: string;
  sources: Array<{ label: string; href: string }>;
}

const METHODOLOGIES: Methodology[] = [
  {
    stat: METRICS.testsFloor,
    label: 'automated tests',
    what:
      'The number of tests pytest collects across the full suite — unit, ' +
      'integration, security, workflow, and gate tests. We publish a round ' +
      'FLOOR, not a live count, so the number can only understate.',
    how:
      'Reproduce with: pip install -e ".[dev]" && pytest --collect-only -q. ' +
      'The final line reports the collected total.',
    gate:
      'scripts/check_badge_freshness.py runs inside the CI coverage job and ' +
      'fails the build in both directions: if the floor ever overstates the ' +
      'real count, or if the real count exceeds the floor by more than 5,000 ' +
      '(a stale floor is treated as a bug too).',
    sources: [
      { label: 'Freshness guard script', href: `${REPO}/blob/main/scripts/check_badge_freshness.py` },
      { label: 'Test suite', href: `${REPO}/tree/main/tests` },
    ],
  },
  {
    stat: `${METRICS.coverageFloorPct}%`,
    label: 'coverage floor, CI-enforced',
    what:
      'The minimum line coverage the project accepts — a floor the build ' +
      'enforces, not a marketing average. Actual coverage sits at or above ' +
      'it by construction.',
    how:
      'Enforced identically in three places: pytest runs with ' +
      '--cov-fail-under=85 (pyproject.toml), and Codecov gates both the ' +
      'project total and every patch at 85%. One number everywhere — a PR ' +
      'that drops changed-code coverage below the floor cannot merge.',
    gate:
      'The threshold itself is drift-guarded: a unit test fails CI if the ' +
      'configured coverage gate is ever lowered.',
    sources: [
      { label: 'pyproject.toml', href: `${REPO}/blob/main/pyproject.toml` },
      { label: 'codecov.yml', href: `${REPO}/blob/main/codecov.yml` },
      { label: 'Live coverage on Codecov', href: 'https://codecov.io/gh/Smart-AI-Memory/attune-ai' },
    ],
  },
  {
    stat: METRICS.ragFaithfulness,
    label: 'mean RAG faithfulness',
    what:
      'How well answers produced through attune-rag (the retrieval engine ' +
      'inside Attune) stay grounded in the retrieved source, scored on a ' +
      '40-query golden set over N=20 runs. The published number is the ' +
      'measured mean: 0.97.',
    how:
      'The evaluation harness, golden set, and scoring live in the ' +
      'attune-rag repository and run in its CI — the benchmark is ' +
      'versioned with the code it measures.',
    gate:
      'The CI regression gate is locked at mean faithfulness ≥ 0.9686: a ' +
      'PR that drops the mean below that threshold fails the build. Note ' +
      'the distinction — 0.97 is the measured mean, 0.9686 is the locked ' +
      'floor beneath it.',
    sources: [
      { label: 'Methodology decision record', href: `${REPO}/blob/main/docs/rag/faithfulness-decision-2026-04-19.md` },
      { label: 'attune-rag repository', href: 'https://github.com/Smart-AI-Memory/attune-rag' },
    ],
  },
];

export default function BenchmarksPage() {
  const breadcrumbSchema = generateStructuredData('breadcrumb', {
    items: [
      { name: 'Home', url: 'https://smartaimemory.com' },
      { name: 'Benchmarks', url: 'https://smartaimemory.com/benchmarks' },
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
        <section className="py-20 px-6">
          <div className="max-w-3xl mx-auto text-center">
            <span className="text-xs font-bold text-[var(--primary)] tracking-[0.2em] uppercase mb-4 block">
              Benchmarks &amp; methodology
            </span>
            <h1 className="text-4xl md:text-5xl font-extrabold mb-6">
              Where the numbers come from
            </h1>
            <p className="text-lg text-[var(--text-secondary)] leading-relaxed">
              Every figure we publish is either a CI-enforced floor or a
              measurement with a versioned harness behind it. Nothing on this
              site is an adoption claim, an estimate, or a peak cherry-picked
              from a lucky run. Each number below names its gate and links to
              the live source.
            </p>
          </div>
        </section>

        <section className="pb-24 px-6" aria-label="Methodologies">
          <div className="max-w-4xl mx-auto space-y-8">
            {METHODOLOGIES.map((m) => (
              <article
                key={m.label}
                className="bg-[var(--surface)] rounded-2xl p-8 border border-[var(--border)]/40"
              >
                <div className="flex items-baseline gap-3 mb-5">
                  <span className="text-4xl font-extrabold text-[var(--primary)]">{m.stat}</span>
                  <h2 className="text-lg font-bold">{m.label}</h2>
                </div>
                <dl className="space-y-4 text-sm leading-relaxed">
                  <div>
                    <dt className="font-bold text-[var(--foreground)] mb-1">What it measures</dt>
                    <dd className="text-[var(--text-secondary)]">{m.what}</dd>
                  </div>
                  <div>
                    <dt className="font-bold text-[var(--foreground)] mb-1">How it&apos;s produced</dt>
                    <dd className="text-[var(--text-secondary)]">{m.how}</dd>
                  </div>
                  <div>
                    <dt className="font-bold text-[var(--foreground)] mb-1">The gate that keeps it honest</dt>
                    <dd className="text-[var(--text-secondary)]">{m.gate}</dd>
                  </div>
                </dl>
                <div className="flex flex-wrap gap-4 mt-6 pt-5 border-t border-[var(--border)]/40">
                  {m.sources.map((s) => (
                    <a
                      key={s.href}
                      href={s.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs font-bold text-[var(--primary)] hover:opacity-80 transition-opacity"
                    >
                      {s.label} &rarr;
                    </a>
                  ))}
                </div>
              </article>
            ))}

            <div className="text-center pt-8">
              <p className="text-sm text-[var(--text-muted)] mb-6 max-w-2xl mx-auto">
                Found a number on this site that doesn&apos;t match the code?
                That&apos;s a bug — the repository is the source of truth.
              </p>
              <Link
                href="/"
                className="text-sm font-bold text-[var(--primary)] hover:opacity-80 transition-opacity"
              >
                &larr; Back to overview
              </Link>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
