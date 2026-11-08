import { HARNESS_PACKAGE_URL, HARNESS_RELEASE_NOTICE, HARNESS_PREPARATION_NOTICE, HARNESS_GET_STARTED, HARNESS_PREPARATION, HARNESS_SOURCE_ROOT } from '@/lib/harness-release';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata } from '@/lib/metadata';
import styles from './page.module.css';

export const metadata = generateMetadata();

export default function Home() {
  return (<>
    <Navigation />
    <main id="main-content" className={styles.site}>

    <section className={styles["hero"] + " " + styles["wrap"]} aria-labelledby="hero-title">
      <div>
        <p className={styles["eyebrow"]}>Open-source tools for AI-assisted engineering</p>
        <h1 id="hero-title">Turn a goal into a plan.<br />Put agents to work.<br />Check the results.</h1>
        <p className={styles["intro"]}>Plan a change, review a document, repair files, run tests or return to saved work with your assistant in Codex or Claude Code. Harness keeps the output and check results so you can see what happened and decide what to do next.</p>
        <Link className={styles["cta"] + " " + styles["primary"]} href="/harness/help/goals/">Choose your next task <span aria-hidden="true">↗</span></Link>
        <p className={styles["secondary-paths"]}><Link href={HARNESS_GET_STARTED}>Get started</Link><Link href="/harness/learn/">Learn Harness</Link><Link href="#collaborate">Work with us</Link></p>
      </div>
      <aside className={styles["evidence-card"]} aria-labelledby="chain-title">
        <p className={styles["eyebrow"]}>Attune Harness</p>
        <h2 id="chain-title">From idea to a result you can review</h2>
        <ol className={styles["evidence-chain"]} role="list">
          <li><span className={styles["step-number"]} aria-hidden="true">01</span><div><strong>Define what done means</strong><span>Turn your idea into a clear goal, scope, and plan with your agent.</span></div></li>
          <li><span className={styles["step-number"]} aria-hidden="true">02</span><div><strong>Keep the context with the work</strong><span>Build, review, and repair with the task’s scope and evidence alongside it.</span></div></li>
          <li><span className={styles["step-number"]} aria-hidden="true">03</span><div><strong>Know where you stand</strong><span>See what changed, what the checks established, and what still needs attention. Decide what happens next.</span></div></li>
        </ol>
      </aside>
    </section>

    <section className={styles["section"] + " " + styles["wrap"] + " " + styles["harness"]} id="harness" aria-labelledby="harness-title">
      <div>
        <p className={styles["eyebrow"]}>The lead project · Attune Harness</p>
        <h2 id="harness-title">Make progress you can review.</h2>
        <p className={styles["harness-intro"]}>Choose a useful goal, agree on the work and checks, and review the result.</p>
      </div>
      <div className={styles["harness-copy"]}>
        <p>Start with the problem you want to solve. Your assistant helps prepare the work, presents what needs your review and uses Harness to carry out the steps you authorize.</p>
        <div className={styles["principles"]}>
          <div><h3>Turn an idea into a plan.</h3><p>Develop the goal, affected files, tasks and checks with your assistant before implementation.</p></div>
          <div><h3>Build in reviewable steps.</h3><p>Give configured agents the accepted tasks, then inspect their work against the agreed checks.</p></div>
          <div><h3>Check a document’s claims.</h3><p>Compare a document with your criteria and supporting sources. Inspect findings and unresolved questions.</p></div>
          <div><h3>Repair a problem and test the fix.</h3><p>Check a proposed repair against a test fixed before the repair begins.</p></div>
          <div><h3>See which tests ran.</h3><p>Preview the tests selected for a code change, then inspect their output and results.</p></div>
          <div><h3>Pick up saved work.</h3><p>Read the saved decisions and results before choosing the next action with your assistant.</p></div>
        </div>
        <p>See what passed, what failed and what needs another look. Harness keeps the output and check results together so you can review the work before deciding what to do next.</p>
        <div className={styles["principles"]}>
          <div><h3>Decide what runs.</h3><p>Accepting intent and authorizing execution are separate decisions. Paid calls need their own authorization.</p></div>
          <div><h3>Understand the checks.</h3><p>A passing check establishes what it tested. It does not guarantee every output is correct.</p></div>
        </div>
        <div className={styles["release"]}>
          <p><strong>{HARNESS_RELEASE_NOTICE}</strong> <Link href={HARNESS_GET_STARTED}>Get started</Link> · <Link href={HARNESS_PACKAGE_URL}>Published package</Link></p>
          <p className={styles["candidate"]}>{HARNESS_PREPARATION_NOTICE} <Link href={HARNESS_PREPARATION}>Explore the archived 1.7.0 preparation guide</Link>.</p>
          <p className={styles["candidate"]}>Browser forms guide intake and intent approval. Each workflow retains its own execution permissions and checks.</p>
          <details>
            <summary>Read the evidence and limits</summary>
            <p>In one exporter comparison, command-line checks found three defects that direct serializer checks had missed.</p>
            <p>The result applies to that example. General model reliability needs separate assessment.</p>
            <p><Link href="https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/plan-build-native-results.md">Read the comparison and its limits</Link></p>
            <p>A passing check establishes what it tested. Native planning and building remain experimental. Claude Code and Codex have documented setup paths; Antigravity integration is unverified in this review. Native MCP panel delivery remains unverified. <Link href={`${HARNESS_PACKAGE_URL}#user-content-what-is-qualified-and-what-is-not`}>Review the qualification guide</Link>.</p>
          </details>
        </div>
      </div>
    </section>

    <section className={styles["section"] + " " + styles["wrap"]} id="context" aria-labelledby="context-title">
      <div className={styles["section-heading"]}>
        <div><p className={styles["eyebrow"]}>Context and useful next steps</p><h2 id="context-title">Find the next opportunity in work you already have.</h2></div>
        <p>A bounded workflow with your agent: bring relevant context, review possible follow-up work, and decide what is worth pursuing.</p>
      </div>
      <div className={styles["paths"]}>
        <article className={styles["path"]}><h3>Bring the relevant context.</h3><p>Use project evidence and supported memory sources you explicitly provide or configure.</p></article>
        <article className={styles["path"]}><h3>Keep the next step visible.</h3><p>Retain an opportunity-review checkpoint with its goal, progress, evidence and unfinished review.</p></article>
        <article className={styles["path"]}><h3>Choose what to pursue.</h3><p>Assess the proposed benefit and uncertainty. A saved suggestion grants no execution authority.</p></article>
      </div>
      <p className={styles["candidate"]}>Scoped recall and saved review checkpoints are supported. Automatic access to all chat history is not implied; the richer opportunity-ranking and selection journey remains proposed. <Link href={`${HARNESS_SOURCE_ROOT}/docs/specs/task-opportunities/journey.md`}>Review the current boundary</Link>.</p>
    </section>

    <section className={styles["section"] + " " + styles["wrap"]} aria-labelledby="paths-title">
      <div className={styles["section-heading"]}>
        <div><p className={styles["eyebrow"]}>Help shape what comes next</p><h2 id="paths-title">Three ways to take part.</h2></div>
        <p>Proposed paths for contributors, potential pilot customers and open-source sponsors.</p>
      </div>
      <div className={styles["paths"]}>
        <article className={styles["path"]} id="collaborate">
          <p className={styles["path-label"]}>Start by building together</p>
          <h3>Collaborate</h3>
          <p>Help improve specification development, planning, build and repair workflows, and independent checks. Bring a reproducible problem, a design question or a contribution.</p>
          <details><summary>Explore collaboration</summary><p>A starting conversation could identify a useful contribution, its scope and how to check it. Documentation, usability and real workflow evidence matter alongside code.</p><p><Link href="/contact/">Start a conversation <span aria-hidden="true">↗</span></Link></p></details>
        </article>
        <article className={styles["path"]} id="pilot">
          <p className={styles["path-label"]}>Explore a possible customer engagement</p>
          <h3>Discuss a pilot</h3>
          <p>Explore one workflow guided by a specification, from a clear goal and agreed scope to evidence you can review. Define what a possible pilot would need to demonstrate.</p>
          <details><summary>Explore a pilot</summary><p>Possible starting points include developing a specification with explicit acceptance criteria, reviewing a generated document against project evidence, or checking a scoped agent-assisted change. Scope, responsibilities and commercial terms would need separate agreement.</p><p><Link href="/contact/">Start a conversation <span aria-hidden="true">↗</span></Link></p></details>
        </article>
        <article className={styles["path"]} id="sponsor">
          <p className={styles["path-label"]}>Support work in the open</p>
          <h3>Sponsor open-source milestones</h3>
          <p>Discuss support for an open-source milestone in specification workflows, independent checks or usable documentation, with its scope, evidence and limits stated up front.</p>
          <details><summary>Explore sponsorship</summary><p>A discussion could connect support with an agreed milestone in usability, documentation or verification. Milestones and any sponsorship terms remain to be defined.</p><p><Link href="/contact/">Start a conversation <span aria-hidden="true">↗</span></Link></p></details>
        </article>
      </div>
    </section>

    <section className={styles["section"] + " " + styles["wrap"]} id="portfolio" aria-labelledby="portfolio-title">
      <div className={styles["section-heading"]}>
        <div><p className={styles["eyebrow"]}>Supporting tools and earlier work</p><h2 id="portfolio-title">Project references.</h2></div>
        <p>Harness is the current focus. Supporting libraries and earlier project references remain available.</p>
      </div>
      <div className={styles["portfolio"]}>
        <article className={styles["product"]}><p className={styles["role"]}>Earlier project · Memory and workflows</p><h3>Attune AI</h3><span className={styles["version"]}><span>v16.4.0</span></span><p>Reference for the earlier project’s memory and workflow tools. Existing code and documentation remain available.</p><Link href="https://github.com/Smart-AI-Memory/attune-ai">Attune AI reference <span aria-hidden="true">↗</span></Link></article>
        <article className={styles["product"]}><p className={styles["role"]}>Structured questions and decisions</p><h3>Attune Forms</h3><p>Make questions and choices easier to review, with structured answers validated on return.</p><Link href="https://github.com/Smart-AI-Memory/attune-forms">Explore Attune Forms <span aria-hidden="true">↗</span></Link></article>
        <article className={styles["product"]}><p className={styles["role"]}>Retrieval with citations</p><h3>Attune RAG</h3><p>Retrieve relevant project sources and return citation records for the next step.</p><Link href="https://github.com/Smart-AI-Memory/attune-rag">Explore Attune RAG <span aria-hidden="true">↗</span></Link></article>
      </div>
    </section>

    <section className={styles["section"] + " " + styles["wrap"] + " " + styles["about"]} aria-labelledby="about-title">
      <div><p className={styles["eyebrow"]}>Built by Patrick Roebuck</p><h2 id="about-title">Developed in the open.</h2></div>
      <p>The direction is practical: make agent work easier to authorize, inspect and evaluate. The next step is to find useful problems to work on together.</p>
    </section>

    </main>
    <Footer />
  </>);
}
