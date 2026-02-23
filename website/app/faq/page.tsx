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
        answer: 'Attune AI is a production-ready framework for AI-powered developer workflows with cost optimization and multi-agent orchestration. It includes 13 agent templates, dynamic team composition, persistent agent state, 10+ integrated workflows, and a tier-based LLM routing system that saves 34-86% on API costs.',
      },
      {
        question: 'What is multi-agent orchestration?',
        answer: 'Multi-agent orchestration lets you compose teams of specialized AI agents that collaborate on complex tasks. Attune AI supports parallel, sequential, two-phase, and delegation strategies with quality gates to ensure results meet your standards. The MetaOrchestrator analyzes tasks and automatically selects optimal agent teams.',
      },
      {
        question: 'What is Agent State Persistence?',
        answer: 'Agent State Persistence stores execution history, checkpoints, and accumulated metrics for each agent across sessions. This enables recovery from interruptions, performance tracking over time, and pattern learning. State is stored locally in JSON files under .attune/agents/state/.',
      },
      {
        question: 'What is Dynamic Team Composition?',
        answer: 'Dynamic Team Composition allows you to build agent teams at runtime from 13 pre-built templates or custom configurations. Teams can execute with different strategies (parallel, sequential, two-phase, delegation) and enforce quality gates. You can also compose entire workflows into teams using the WorkflowComposer.',
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
        question: 'Which LLM providers are supported?',
        answer: 'Attune AI is built exclusively for Anthropic Claude with a Claude-native architecture. This enables automatic prompt caching (up to 90% cost savings on cached tokens), extended thinking, and optimized tool use. Agent and team creation features (dynamic composition, SDK integration) work with the Anthropic Agent SDK for enhanced capabilities.',
      },
      {
        question: 'What are agent templates?',
        answer: 'Agent templates are pre-built agent archetypes with defined roles, capabilities, tier preferences, and quality gates. Attune AI includes 13 templates: security auditor, code reviewer, test coverage analyzer, documentation writer, performance optimizer, architecture analyst, refactoring specialist, dependency checker, bug predictor, release coordinator, integration tester, API designer, and DevOps engineer.',
      },
      {
        question: 'How is the framework tested?',
        answer: 'Attune AI has 14,800+ comprehensive tests covering unit tests, integration tests, and cross-platform compatibility. Core modules are rigorously tested for security, agent state persistence, dynamic team orchestration, workflow coordination, and meta-workflow functionality.',
      },
      {
        question: 'How does prompt caching save money?',
        answer: 'Attune AI leverages Anthropic\'s automatic prompt caching out of the box — no configuration required. Cached input tokens cost just 10% of the standard price, delivering up to 90% cost savings and up to 85% faster responses. The framework\'s Claude-native architecture is designed around caching: system prompts, tool definitions, and conversation history are automatically cached and reused across requests.',
      },
      {
        question: 'What is semantic caching?',
        answer: 'On top of Anthropic\'s API-level caching, Attune AI includes an optional HybridCache powered by sentence-transformers. It detects semantically similar prompts (95%+ cosine similarity) and reuses cached responses, avoiding redundant API calls entirely. Hash-only caching achieves ~30% hit rate; with semantic matching enabled, measured hit rates reach ~57% on workflows like security audits. Install with pip install attune-ai[developer] to enable it automatically.',
      },
      {
        question: 'What platforms are supported?',
        answer: 'The framework is cross-platform and runs on macOS, Linux, and Windows. It requires Python 3.10+ and works with all major development environments including VS Code, JetBrains IDEs, and terminal-based workflows.',
      },
    ],
  },
  {
    category: 'Wizards',
    questions: [
      {
        question: 'What are wizards?',
        answer: 'Wizards are guided, multi-step AI workflows that walk you through complex tasks like debugging, security audits, refactoring, and test generation. Each wizard collects context via questions, runs AI analysis, decomposes work into tasks, and previews results before acting. Attune AI ships with 5 built-in wizards: debug, test-gen, refactor, security, and release-prep.',
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
        answer: 'You can build AI-powered developer workflows for software development (bug prediction, security scanning, test generation, code review), orchestrate multi-agent teams for complex analysis tasks, and compose workflows into coordinated pipelines. The framework also supports healthcare use cases with clinical decision support.',
      },
      {
        question: 'What happened to the Fair Source License?',
        answer: 'As of January 28, 2026, we switched from Fair Source 0.9 to Apache 2.0. We realized the licensing restrictions were limiting adoption without generating revenue. Going fully open source lets us focus on building the best framework and growing a community.',
      },
      {
        question: 'Is the framework production-ready?',
        answer: 'Yes! The framework is v3.3.0 Production/Stable with 14,800+ comprehensive tests, extensive documentation, persistent agent state, dynamic team composition, and is being used in production software development tools and AI workflows.',
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
  title: 'FAQ',
  description: 'Frequently asked questions about Attune AI, open source licensing, and technical details.',
  url: 'https://smartaimemory.com/faq',
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

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(structuredData),
        }}
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
                Everything you need to know about Attune AI
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
