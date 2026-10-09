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
        <h1 id="hero-title">Delegate with clear scope.<br />Keep the evidence.</h1>
        <p className={styles["intro"]}>Work with your agent to develop a specification, plan a change, and review build, repair and test results. Harness keeps the agreed scope and task evidence available so you can decide what happens next.</p>
        <Link className={styles["cta"] + " " + styles["primary"]} href="#collaborate">Collaborate <span aria-hidden="true">↗</span></Link>
        <p className={styles["secondary-paths"]}><Link href="#pilot">Discuss a pilot</Link><Link href="#sponsor">Sponsor open-source milestones</Link></p>
      </div>
      <figure className={styles["evidence-card"]} aria-labelledby="chain-title">
        <p className={styles["eyebrow"]}>Attune Harness</p>
        <h2 id="chain-title">A task you can inspect.</h2>
        <ol className={styles["evidence-chain"]}>
          <li><span className={styles["step-number"]} aria-hidden="true">01</span><div><strong>Agree the scope</strong><span>Goal, limits and acceptance criteria</span></div></li>
          <li><span className={styles["step-number"]} aria-hidden="true">02</span><div><strong>Authorize the work</strong><span>Permitted actions and recorded output</span></div></li>
          <li><span className={styles["step-number"]} aria-hidden="true">03</span><div><strong>Check the result</strong><span>Independent checks, outcome and errors</span></div></li>
        </ol>
        <figcaption>Illustrative workflow. A real receipt records what ran and what the checks established.</figcaption>
      </figure>
    </section>

    <section className={styles["section"] + " " + styles["wrap"] + " " + styles["harness"]} id="harness" aria-labelledby="harness-title">
      <div>
        <p className={styles["eyebrow"]}>The lead project · Attune Harness</p>
        <h2 id="harness-title">Make the work inspectable.</h2>
        <p className={styles["harness-intro"]}>Develop the specification, agree with the scope, and inspect the evidence as work progresses.</p>
      </div>
      <div className={styles["harness-copy"]}>
        <p>Complex work starts with a specification you can review: requirements, constraints and acceptance criteria. Harness supports the next steps with explicit scope, retained decisions and checks you can inspect.</p>
        <div className={styles["principles"]}>
          <div><h3>Develop a reviewable specification.</h3><p>Work with your agent to record requirements, constraints and acceptance criteria before implementation.</p></div>
          <div><h3>Agree to the plan and scope.</h3><p>Inspect the allowed files, proposed work and acceptance checkpoint before authorizing execution.</p></div>
          <div><h3>Build and repair within limits.</h3><p>Use scoped workflows with permitted files and declared verification checks alongside your agents.</p></div>
          <div><h3>Review independently against evidence.</h3><p>Assign a separate reviewer to assess a document against project sources. Keep unsupported claims and uncertainty visible.</p></div>
          <div><h3>Test the change and keep the results.</h3><p>Run checks on captured changes. Inspect what ran, what passed and what failed before deciding the next step.</p></div>
          <div><h3>Keep decisions and continue.</h3><p>Inspect saved task state and recover context from supported, configured sources before resuming work.</p></div>
        </div>
        <p>See what passed, what failed and what needs another look. Harness keeps the output and check results together so you can review the work before deciding what to do next.</p>
        <div className={styles["principles"]}>
          <div><h3>Authorization has limits.</h3><p>Accepting intent and authorizing execution are separate decisions. Paid calls need their own authorization.</p></div>
          <div><h3>Evidence has limits too.</h3><p>A passing check establishes what it tested. It does not guarantee every output is correct.</p></div>
        </div>
        <div className={styles["release"]}>
          <p><strong>Published: Attune Harness 1.3.0.</strong> <Link href="https://pypi.org/project/attune-harness/1.3.0/">Package and release guide</Link></p>
          <p className={styles["candidate"]}>Browser forms guide intake and intent approval. Each workflow retains its own execution permissions and checks.</p>
          <details>
            <summary>Read the evidence and limits</summary>
            <p>In one exporter comparison, command-line checks found three defects that direct serializer checks had missed.</p>
            <p>The result applies to that example. General model reliability needs separate assessment.</p>
            <p><Link href="https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/plan-build-native-results.md">Read the comparison and its limits</Link></p>
            <p>A passing check establishes what it tested. Native planning and building remain experimental. Claude Code and Codex have documented setup paths; Antigravity integration is unverified in this review. Native MCP panel delivery remains unverified. <Link href="https://pypi.org/project/attune-harness/1.3.0/#what-is-qualified-and-what-is-not">Review the qualification guide</Link>.</p>
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
      <p className={styles["candidate"]}>Scoped recall and saved review checkpoints are supported. Automatic access to all chat history is not implied; the richer opportunity-ranking and selection journey remains proposed. <Link href="https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/specs/task-opportunities/journey.md">Review the current boundary</Link>.</p>
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
