import Link from 'next/link';
import { topics, topicHref } from '@/lib/harness-help/topics';

export default function HelpHome() {
  return (
    <>
      <p className="help-eyebrow">Attune Harness · 1.3.0</p>
      <h1>What do you want to do?</h1>
      <p className="help-lead">Start with an outcome. Follow a short process, check its result, and see what needs your decision next.</p>
      <p className="help-callout">Opening a form, saving answers, accepting intent and executing work are separate actions. The guide marks those boundaries at the point you need them.</p>
      <div className="help-cards">
        {topics.map((topic, index) => (
          <article key={topic.slug} className="help-card">
            <p className="help-eyebrow">{String(index + 1).padStart(2, '0')} · {topic.kind}</p>
            <h2><Link href={topicHref(topic.slug)}>{topic.title}</Link></h2>
            <p>{topic.goal}</p>
          </article>
        ))}
      </div>
      <section className="help-learning" aria-labelledby="learning-title">
        <h2 id="learning-title">Learn at your own pace</h2>
        <p>The four task walkthroughs reuse the verified instruction source for <strong>Start and continue work</strong> (Navigation), <strong>Specification Workflow</strong>, <strong>Four Workflows</strong> and <strong>Session Continuity</strong>. Each includes example setup, the expected result and its limits.</p>
        <p>The same instructions support guided class exercises and self-paced tutorials. Editorial framing for articles, posts or future books can reuse them with their version and evidence intact.</p>
        <Link href={topicHref('get-started')}>Begin with a local result →</Link>
      </section>
    </>
  );
}
