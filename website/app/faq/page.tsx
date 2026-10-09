import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata, generateStructuredData } from '@/lib/metadata';
import { HARNESS_FAQ_ITEMS } from '@/lib/harness-faq';

interface FAQItem {
  question: string;
  answer: string | ReactNode;
  answerText?: string; // Plain text version for structured data
}

interface FAQCategory {
  category: string;
  questions: FAQItem[];
}

const faqData: FAQCategory[] = [
  {
    category: 'Attune Harness',
    questions: [...HARNESS_FAQ_ITEMS],
  },
  {
    category: 'Attune AI — General',
    questions: [
      {
        question: 'What is Attune AI?',
        answer: 'Attune AI combines specification development, AI workflows, project memory, retrieval and verification tools. It is a separate project from Attune Harness, released under Apache 2.0. Provider access and setup depend on the workflow you choose.',
      },
      {
        question: 'What is the reliability loop?',
        answer: 'Specify, Ground, Build, Remember and Verify describe a way to organize development: agree requirements, consult project sources, implement tasks, retain useful findings and check the result. This sequence is a working practice; it does not guarantee correct output or enforce every step in every workflow.',
      },
      {
        question: 'What is Attune AI built on?',
        answer: 'Attune AI brings together project memory, structured forms, AI workflows, retrieval through attune-rag and verification tools. Their availability and behavior depend on the installed version and the integration in use. Review the selected workflow and its checks before relying on its output.',
      },
      {
        question: 'Where can I find the Attune AI capability reference?',
        answer: 'The retained Attune AI documentation describes workflows, MCP tools, skills, wizards and template kinds. Use the reference for your installed version and inspect its available commands; a website count is not evidence that a capability is available in your environment.',
      },
      {
        question: "What happened to attune-gui?",
        answer: (
          <>
            <code className="font-mono">attune-gui</code> was the local dashboard that sat on top of the attune-ai framework. The project was parked in July 2026: the repository is archived and no further releases are planned. Released versions stay installable from PyPI (<code className="font-mono">pip install attune-gui</code>), and the previously announced fold into <code className="font-mono">attune-ai[gui]</code> was cancelled.{' '}
            <Link href="/migrate" className="text-[var(--primary)] hover:underline">
              See the archive notice
            </Link>{' '}
            for details.
          </>
        ),
        answerText: "attune-gui was the local dashboard that sat on top of the attune-ai framework. The project was parked in July 2026: the repository is archived and no further releases are planned. Released versions stay installable from PyPI (pip install attune-gui), and the previously announced fold into attune-ai[gui] was cancelled. See /migrate for the archive notice.",
      },
      {
        question: 'Do I need a dashboard?',
        answer: (
          <>
            A dashboard is not required for terminal workflows. CLI and plugin capabilities depend on your installed version and host. The earlier standalone <code className="font-mono">attune-gui</code> dashboard is archived; see the <Link href="/migrate" className="text-[var(--primary)] hover:underline">archive notice</Link> before relying on an existing installation.
          </>
        ),
        answerText: 'A dashboard is not required for terminal workflows. CLI and plugin capabilities depend on your installed version and host. The earlier standalone attune-gui dashboard is archived; see the archive notice before relying on an existing installation.',
      },
    ],
  },
  {
    category: 'Attune AI — Licensing & Pricing',
    questions: [
      {
        question: 'How much does Attune AI cost?',
        answer: 'Attune AI is open source under Apache 2.0. Hosted model calls and other external services may incur separate charges. Check the authentication route, provider terms and permissions for the workflow you intend to run.',
      },
      {
        question: 'What is the Apache 2.0 License?',
        answer: 'Apache 2.0 permits use, modification and redistribution under its conditions. Redistribution obligations include preserving the license and relevant notices, and marking changed files. Read the license for the full terms, including patent provisions and warranty limits.',
      },
      {
        question: 'Can I use Attune AI for commercial projects?',
        answer: 'Yes, Apache 2.0 permits commercial use subject to its conditions. Preserve required license and attribution notices when distributing the software. Model access and other services have their own terms and charges.',
      },
    ],
  },
  {
    category: 'Attune AI — Technical',
    questions: [
      {
        question: 'How does retrieval grounding help me check answers?',
        answer: 'attune-rag retrieves project sources to supply context and citations for review. Check the cited material and the resulting answer. A retrieval evaluation measures a particular corpus, query set and configuration; it does not establish accuracy for every generated answer.',
      },
      {
        question: 'What does verification check?',
        answer: 'Verification tools can check properties such as imports, command-line flags, links and capability counts against project sources. Inspect which checks ran, their results and any unchecked behavior. Passing those checks does not establish that all generated content is correct.',
      },
      {
        question: 'Is my code sent anywhere?',
        answer: 'Local memory storage does not mean every Attune AI workflow stays on your machine. Hosted model calls can send the supplied code, prompts or task context to a provider. The location of Redis and embedding services depends on the configured setup. Review the workflow and its destinations before execution.',
      },
      {
        question: 'Do I need an API key?',
        answer: 'Authentication depends on the host and workflow. A host-native Claude Code integration can use its supported login; a direct API route needs the credentials and billing required by that provider. Check the selected route before execution rather than assuming a subscription covers every call.',
      },
      {
        question: 'What platforms are supported?',
        answer: 'Attune AI requires Python 3.10 or later. Check its installation guide and the requirements of your selected workflow, host and operating system. Python package availability does not establish compatibility with every IDE or integration.',
      },
    ],
  },
  {
    category: 'Attune AI — Wizards',
    questions: [
      {
        question: 'What are wizards?',
        answer: 'Wizards are guided, multi-step workflows. Their questions, analysis and actions depend on the selected wizard. Consult the wizard reference for your installed Attune AI version and check its permissions before running it.',
      },
      {
        question: 'How do I run a wizard?',
        answer: 'Use the wizard guide for your installed Attune AI version. Host commands and Python callbacks need the setup described by that guide; consult the retained documentation before running an example.',
      },
      {
        question: 'Can I create custom wizards?',
        answer: 'Yes! Two approaches: (1) YAML-based — create a .attune/wizards/my-wizard.yaml file with step definitions, no Python required. (2) Python-based — subclass BaseWizard for advanced logic like workflow delegation, conditional steps, and custom result processing. See the Custom Wizard Development guide.',
      },
    ],
  },
  {
    category: 'Attune AI — Use Cases',
    questions: [
      {
        question: 'What can I build with Attune AI?',
        answer: 'Attune AI provides workflows for code review, security scanning, test generation, bug prediction and refactor planning, alongside specification and memory tools. Use them to support development, then inspect the output and run checks appropriate to the change.',
      },
      {
        question: 'How does the spec engine work?',
        answer: 'The spec engine runs via /spec. It guides you Socratically through requirements, design, and tasks with an approval gate, so a feature starts from an agreed spec rather than an open-ended prompt — the first stage of the reliability loop.',
      },
      {
        question: 'What happened to the Fair Source License?',
        answer: 'The current Attune AI license is Apache 2.0. If you use an earlier release, inspect the license distributed with that release. This reference does not claim a reason for the historical licensing change.',
      },
    ],
  },
  {
    category: 'Attune AI — Support & Community',
    questions: [
      {
        question: 'Where can I get help?',
        answer: 'Use the project documentation and GitHub community channels. Report Attune AI bugs in its issue tracker; use the Harness issue tracker for Harness. A pilot or support arrangement would need a separate discussion and agreement.',
      },
      {
        question: 'How do I report bugs?',
        answer: (
          <>
            Report bugs via{' '}
            <Link href="https://github.com/Smart-AI-Memory/attune-ai/issues" className="text-[var(--primary)] hover:underline" target="_blank" rel="noopener noreferrer">
              GitHub Issues
            </Link>
            . Include your environment details, steps to reproduce, and expected vs actual behavior.
          </>
        ),
        answerText: 'Report bugs via GitHub Issues at https://github.com/Smart-AI-Memory/attune-ai/issues. Include your environment details, steps to reproduce, and expected vs actual behavior.',
      },
      {
        question: 'Can I contribute to the project?',
        answer: 'Yes! We welcome contributions. Check out our GitHub repository for contribution guidelines. The framework is fully open source under Apache 2.0, making it easy to fork, modify, and contribute back.',
      },
    ],
  },
];

function CategoryQuestions({ category }: { category: FAQCategory }) {
  return (
    <div className="mb-12">
      <h2 className="!text-2xl font-bold mb-6 text-[var(--primary)]">{category.category}</h2>
      <div className="space-y-6">
        {category.questions.map((item) => (
          <details key={item.question} className="bg-[var(--background)] border-2 border-[var(--border)] rounded-lg p-6 hover:border-[var(--primary)] transition-all group">
            <summary className="text-xl font-bold cursor-pointer list-none flex justify-between items-center">
              <span>{item.question}</span>
              <span className="text-[var(--primary)] ml-4 group-open:rotate-180 transition-transform" aria-hidden="true">▼</span>
            </summary>
            <p className="mt-4 text-[var(--text-secondary)] leading-relaxed">{item.answer}</p>
          </details>
        ))}
      </div>
    </div>
  );
}

export const metadata: Metadata = generateMetadata({
  title: 'Attune Harness FAQ',
  description:
    'Answers about Attune Harness: specifications, scoped work, setup, receipts and qualification limits. Earlier Attune AI reference questions remain available for existing users.',
  url: 'https://smartaimemory.com/faq',
  keywords: [
    'Attune Harness FAQ',
    'spec-driven development platform',
    'Claude Code workflows',
    'retrieval grounding',
    'AI verification',
    'project memory',
  ],
});

export default function FAQPage() {
  const structuredData = generateStructuredData('faq', {
    questions: [...HARNESS_FAQ_ITEMS],
  });
  const breadcrumbSchema = generateStructuredData('breadcrumb', {
    items: [
      { name: 'Home', url: 'https://smartaimemory.com' },
      { name: 'FAQ', url: 'https://smartaimemory.com/faq' },
    ],
  });

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(structuredData),
        }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbSchema) }}
      />
      <Navigation />
      <main id="main-content" className="min-h-screen pt-16">
        {/* Hero Section */}
        <section className="py-20 gradient-primary text-white">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h1 className="text-5xl font-bold mb-6">
                Attune Harness FAQ
              </h1>
              <p className="text-2xl mb-8 opacity-90">
                Specifications, scoped work and checkable results.
              </p>
              <p className="text-sm opacity-90">
                Start with Harness. Earlier project references are available separately below.
              </p>
              <div className="flex flex-wrap justify-center gap-4 mt-8">
                <Link href="/docs#quickstart" className="btn btn-primary">Harness Quick Start</Link>
                <a href="https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/cli-guide.md" className="btn btn-outline !text-white !border-white/60 hover:!bg-white/15">Read the release guide</a>
              </div>
            </div>
          </div>
        </section>

        {/* FAQ Sections */}
        <section className="py-20">
          <div className="container">
            <div className="max-w-4xl mx-auto">
              <CategoryQuestions category={faqData[0]} />
              <details id="attune-ai-reference-questions" className="border border-[var(--border)] rounded-lg p-6">
                <summary className="min-h-11 flex items-center text-lg font-semibold cursor-pointer">Earlier Attune AI references</summary>
                <p className="my-6 text-sm text-[var(--text-secondary)]">These references apply to the earlier project. Open them if you maintain an existing Attune AI installation.</p>
                {faqData.slice(1).map((category) => <CategoryQuestions key={category.category} category={category} />)}
              </details>
            </div>
          </div>
        </section>

        {/* Still Have Questions CTA */}
        <section className="py-20 bg-[var(--border)] bg-opacity-30">
          <div className="container">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-4xl font-bold mb-6">
                Still Have Questions?
              </h2>
              <p className="text-xl text-[var(--text-secondary)] mb-8">
                Read the release guide for setup and qualification details,
                or get in touch about a specific question.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <a
                  href="/contact"
                  className="btn btn-primary text-lg px-8 py-4"
                >
                  Contact
                </a>
                <a
                  href="https://github.com/Smart-AI-Memory/attune-harness/issues"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-outline text-lg px-8 py-4"
                >
                  Harness issues
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
