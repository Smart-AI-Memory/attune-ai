import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata, generateStructuredData } from '@/lib/metadata';

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
    category: 'General',
    questions: [
      {
        question: 'What is Attune AI?',
        answer: 'Attune AI is a spec-driven development platform that combines AI workflows, project memory, retrieval grounding, and verification tools to help teams turn requirements into reliable software. It runs on a Claude subscription or an API key, and is open source under Apache 2.0.',
      },
      {
        question: 'What is the reliability loop?',
        answer: 'The reliability loop is the arc Attune AI takes a requirement through on its way to shipped software: Specify, Ground, Build, Remember, Verify. You write a spec, ground every change in your real code, build with a team of workflows, carry what worked into the next session, and verify the output before it ships.',
      },
      {
        question: 'What is Attune AI built on?',
        answer: 'Memory is the pillar: project memory carries cross-session findings and a retrievable lessons corpus, surfaced at the moment a prompt needs them. Around it ship four supporting capabilities, each real and shipped: dynamic forms (structured human/AI turns), AI workflows (20 workflows for review, tests, bug prediction, and refactors), retrieval grounding (citations back to your source via attune-rag), and verification (fact-checking generated content before it reaches main).',
      },
      {
        question: 'What can Attune AI do, in numbers?',
        answer: 'Attune AI ships 20 workflows, 47 MCP tools, 25 auto-triggering skills, 5 wizards, and 15 template kinds. The spec engine runs via /spec, progressive help via /coach, and cross-session recall via /recall.',
      },
      {
        question: "What's the difference between attune-ai and attune-gui?",
        answer: (
          <>
            Two packages today, one workflow. <code className="font-mono">attune-ai</code> is the framework — workflows, agents, the CLI. <code className="font-mono">attune-gui</code> is the local dashboard that sits on top of it: Living Docs, RAG search, the commands surface, summaries. You install them separately right now (<code className="font-mono">pip install attune-ai</code> and <code className="font-mono">pip install attune-gui</code>) and they talk to the same project directory. In an upcoming release they fold into one install (<code className="font-mono">pip install attune-ai[gui]</code>);{' '}
            <Link href="/migrate" className="text-[var(--primary)] hover:underline">
              see the migration page
            </Link>{' '}
            for the heads-up.
          </>
        ),
        answerText: "Two packages today, one workflow. attune-ai is the framework — workflows, agents, the CLI. attune-gui is the local dashboard that sits on top of it: Living Docs, RAG search, the commands surface, summaries. You install them separately right now (pip install attune-ai and pip install attune-gui) and they talk to the same project directory. In an upcoming release they fold into one install (pip install attune-ai[gui]); see /migrate for the heads-up.",
      },
      {
        question: 'Do I need the dashboard?',
        answer: (
          <>
            No &mdash; the CLI does everything on its own. But the dashboard is where the workflow tells you what to do next: which docs have drifted, which summaries need re-polishing, which commands you ran recently and what they produced. If you&rsquo;re just running one-off workflows, the CLI is fine. If you&rsquo;re maintaining a living help system or iterating on a corpus, the dashboard saves real time.{' '}
            <Link href="/migrate" className="text-[var(--primary)] hover:underline">
              Migration heads-up here
            </Link>{' '}
            if you have <code className="font-mono">attune-gui</code> installed today.
          </>
        ),
        answerText: "No — the CLI does everything on its own. But the dashboard is where the workflow tells you what to do next: which docs have drifted, which summaries need re-polishing, which commands you ran recently and what they produced. If you're just running one-off workflows, the CLI is fine. If you're maintaining a living help system or iterating on a corpus, the dashboard saves real time. Migration heads-up at /migrate if you have attune-gui installed today.",
      },
    ],
  },
  {
    category: 'Licensing & Pricing',
    questions: [
      {
        question: 'How much does Attune AI cost?',
        answer: 'Attune AI is completely free and open source under the Apache License 2.0. Use it in personal projects, startups, or large enterprises at no cost. No license keys, no restrictions, no hidden fees.',
      },
      {
        question: 'What is the Apache 2.0 License?',
        answer: 'Apache 2.0 is a permissive open source license approved by the OSI. It allows you to use, modify, distribute, and sell products built with Attune AI. It includes patent protection and is approved by most enterprise legal teams.',
      },
      {
        question: 'Can I use Attune AI for commercial projects?',
        answer: 'Yes! Apache 2.0 explicitly permits commercial use. Build and sell products using Attune AI without any licensing fees or restrictions.',
      },
    ],
  },
  {
    category: 'Technical',
    questions: [
      {
        question: 'How does retrieval grounding keep answers accurate?',
        answer: 'Retrieval grounding is powered by attune-rag, a core (built-in) dependency. Keyword and semantic retrieval keep generated content anchored to your actual source, with citations back to where each claim came from. Mean faithfulness is measured at ≥ 0.97 and CI-gated — drift fails the build rather than slipping through.',
      },
      {
        question: 'How does verification catch hallucinations?',
        answer: 'Verification fact-checks LLM output against your source-of-truth before a change reaches main: it confirms imports actually import, CLI flags are real, links resolve, and counts match. It closes the loop the spec opened, so generated docs and code stay honest.',
      },
      {
        question: 'Is my code sent anywhere?',
        answer: 'Memory is local-first — nothing is sent to a cloud by default. Findings and the lessons corpus live on your machine. An optional Redis semantic tier is available for richer recall, and it uses local Ollama embeddings, so you stay in control of where your data goes.',
      },
      {
        question: 'Do I need an API key?',
        answer: 'No. Attune AI works on a Claude subscription or an API key — use whichever you have. The platform is open source under Apache 2.0 with no license keys or hidden fees.',
      },
      {
        question: 'Which LLM provider is supported?',
        answer: "Attune AI is built for Anthropic Claude with a Claude-native architecture, so it leverages Anthropic's automatic prompt caching, extended thinking, and optimized tool use.",
      },
      {
        question: 'What platforms are supported?',
        answer: 'The platform is cross-platform and runs on macOS, Linux, and Windows. It requires Python 3.10+ and works with all major development environments including VS Code, JetBrains IDEs, and terminal-based workflows.',
      },
    ],
  },
  {
    category: 'Wizards',
    questions: [
      {
        question: 'What are wizards?',
        answer: 'Wizards are guided, multi-step AI workflows that walk you through complex tasks. Each wizard collects context via questions, runs AI analysis, decomposes work into tasks, and previews results before acting. Attune AI ships with 5 built-in wizards.',
      },
      {
        question: 'How do I run a wizard?',
        answer: 'From Claude Code, type /wizard run debug (or any wizard ID). From Python: from attune.wizards import get_wizard; wizard = get_wizard("debug")(); result = await wizard.run(). See the Getting Started guide for a full walkthrough.',
      },
      {
        question: 'Can I create custom wizards?',
        answer: 'Yes! Two approaches: (1) YAML-based — create a .attune/wizards/my-wizard.yaml file with step definitions, no Python required. (2) Python-based — subclass BaseWizard for advanced logic like workflow delegation, conditional steps, and custom result processing. See the Custom Wizard Development guide.',
      },
    ],
  },
  {
    category: 'Use Cases',
    questions: [
      {
        question: 'What can I build with Attune AI?',
        answer: 'You take requirements through to reliable software: write a spec with /spec, ground changes in your real code, run workflows for code review, security scanning, test generation, bug prediction, and refactor planning, then verify the output before it ships. The lessons corpus and cross-session memory carry what worked into the next session.',
      },
      {
        question: 'How does the spec engine work?',
        answer: 'The spec engine runs via /spec. It guides you Socratically through requirements, design, and tasks with an approval gate, so a feature starts from an agreed spec rather than an open-ended prompt — the first stage of the reliability loop.',
      },
      {
        question: 'What happened to the Fair Source License?',
        answer: 'As of January 28, 2026, we switched from Fair Source 0.9 to Apache 2.0. We realized the licensing restrictions were limiting adoption without generating revenue. Going fully open source lets us focus on building the best platform and growing a community.',
      },
    ],
  },
  {
    category: 'Support & Community',
    questions: [
      {
        question: 'Where can I get help?',
        answer: 'Get community support via GitHub Discussions. Report bugs via GitHub Issues. Enterprise users can reach out for dedicated support options.',
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

export const metadata: Metadata = generateMetadata({
  title: 'Attune AI FAQ — Spec-Driven Development Platform for Claude Code',
  description:
    'Answers to common questions about Attune AI: the reliability loop, AI workflows, project memory, retrieval grounding, verification, licensing, and how it turns requirements into reliable software.',
  url: 'https://smartaimemory.com/faq',
  keywords: [
    'Attune AI FAQ',
    'spec-driven development platform',
    'Claude Code workflows',
    'retrieval grounding',
    'AI verification',
    'project memory',
  ],
});

export default function FAQPage() {
  const structuredData = generateStructuredData('faq', {
    questions: faqData.flatMap(category =>
      category.questions.map(q => ({
        question: q.question,
        answer: q.answerText ?? (typeof q.answer === 'string' ? q.answer : ''),
      }))
    ),
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
                Frequently Asked Questions
              </h1>
              <p className="text-2xl mb-8 opacity-90">
                How Attune AI turns requirements into reliable software
              </p>
            </div>
          </div>
        </section>

        {/* FAQ Sections */}
        <section className="py-20">
          <div className="container">
            <div className="max-w-4xl mx-auto">
              {faqData.map((category, categoryIndex) => (
                <div
                  key={categoryIndex}
                  className="mb-12"
                >
                  <h2 className="text-3xl font-bold mb-6 text-[var(--primary)]">
                    {category.category}
                  </h2>
                  <div className="space-y-6">
                    {category.questions.map((item, questionIndex) => (
                      <details
                        key={questionIndex}
                        className="bg-[var(--background)] border-2 border-[var(--border)] rounded-lg p-6 hover:border-[var(--primary)] transition-all group"
                      >
                        <summary className="text-xl font-bold cursor-pointer list-none flex justify-between items-center">
                          <span>{item.question}</span>
                          <span className="text-[var(--primary)] ml-4 group-open:rotate-180 transition-transform">
                            ▼
                          </span>
                        </summary>
                        <p className="mt-4 text-[var(--text-secondary)] leading-relaxed">
                          {item.answer}
                        </p>
                      </details>
                    ))}
                  </div>
                </div>
              ))}
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
                We&apos;re here to help. Reach out to our team or join the community.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <a
                  href="/contact"
                  className="btn btn-primary text-lg px-8 py-4"
                >
                  Contact Us
                </a>
                <a
                  href="https://github.com/Smart-AI-Memory/attune-ai/discussions"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-outline text-lg px-8 py-4"
                >
                  Join Community
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
