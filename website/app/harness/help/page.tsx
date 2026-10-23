import Link from 'next/link';
import { topics, topicHref } from '@/lib/harness-help/topics';
import { HARNESS_PUBLISHED, HARNESS_RELEASE_SLUG, HARNESS_VERSION } from '@/lib/harness-help/release';

export default function HelpHome() {
  return (
    <>
      <p className="help-eyebrow">Attune Harness · {HARNESS_VERSION}{!HARNESS_PUBLISHED && ' preparation'}</p>
      <h1>What do you want to do?</h1>
      <p className="help-lead">Choose the result you need, then follow its instructions, examples and review points.</p>
      <section className="help-goal-hero" aria-labelledby="goal-guide-title">
        <p className="help-eyebrow">Start with your goal</p>
        <h2 id="goal-guide-title"><Link href={topicHref('goals')}>What do you want to accomplish?</Link></h2>
        <p>Explore 21 goals and six testing FAQs. Expand a topic to find a starter prompt, steps, expected results and the decisions you need to make.</p>
        <Link className="help-goal-link" href={topicHref('goals')}>Browse all goals →</Link>
      </section>
      <p><Link href={topicHref(HARNESS_RELEASE_SLUG)}>Get started with Harness {HARNESS_VERSION}</Link> for installation, integrations and release limits.</p>
      <p className="help-callout">Opening a form, saving answers, accepting intent and executing work are separate actions. The guide marks those boundaries at the point you need them.</p>
      <h2>Installation and command reference</h2>
      <div className="help-cards">
        {topics.filter((topic) => topic.version === HARNESS_VERSION).map((topic) => (
          <article key={topic.slug} className="help-card">
            <p className="help-eyebrow">{topic.kind} · {topic.version}</p>
            <h2><Link href={topicHref(topic.slug)}>{topic.title}</Link></h2>
            <p>{topic.goal}</p>
          </article>
        ))}
      </div>
      <section aria-labelledby="historical-guides-title">
        <h2 id="historical-guides-title">Earlier versioned guides</h2>
        <p>These guides retain the instructions and evidence for their named versions.</p>
        <ul>{topics.filter((topic) => topic.version !== HARNESS_VERSION).map((topic) => (
          <li key={topic.slug}><Link href={topicHref(topic.slug)}>{topic.title}</Link> — Harness {topic.version ?? '1.3.0'}</li>
        ))}</ul>
      </section>
      <section className="help-learning" aria-labelledby="learning-title">
        <h2 id="learning-title">Historical 1.3.0 walkthroughs</h2>
        <p>The four task walkthroughs reuse the verified instruction source for <strong>Start and continue work</strong> (Navigation), <strong>Specification Workflow</strong>, <strong>Four Workflows</strong> and <strong>Session Continuity</strong>. Each includes example setup, the expected result and its limits.</p>
        <p>The same instructions support guided class exercises and self-paced tutorials. Editorial framing for articles, posts or future books can reuse them with their version and evidence intact.</p>
        <Link href={topicHref('get-started')}>Begin with a local result →</Link>
      </section>
    </>
  );
}
