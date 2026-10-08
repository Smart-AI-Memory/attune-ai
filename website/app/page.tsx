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
        <p className={styles["eyebrow"]}>Open-source tools for accountable AI work</p>
        <h1 id="hero-title">Delegate with clear scope.<br />Keep the evidence.</h1>
        <p className={styles["intro"]}>Attune Harness runs agent tasks, checks results independently against criteria you supply, and keeps the output, check results and errors for review.</p>
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

    <section className={styles["section"] + " " + styles["wrap"]} aria-labelledby="paths-title">
      <div className={styles["section-heading"]}>
        <div><p className={styles["eyebrow"]}>Help shape what comes next</p><h2 id="paths-title">Three ways to take part.</h2></div>
        <p>Proposed paths for contributors, potential pilot customers and open-source sponsors.</p>
      </div>
      <div className={styles["paths"]}>
        <article className={styles["path"]} id="collaborate">
          <p className={styles["path-label"]}>Start by building together</p>
          <h3>Collaborate</h3>
          <p>Help build and test tools for accountable agent work. Bring a reproducible problem, a design question or a contribution.</p>
          <details><summary>Explore collaboration</summary><p>A starting conversation could identify a useful contribution, its scope and how to check it. Documentation, usability and real workflow evidence matter alongside code.</p><p><Link href="/contact/">Start a conversation <span aria-hidden="true">↗</span></Link></p></details>
        </article>
        <article className={styles["path"]} id="pilot">
          <p className={styles["path-label"]}>Explore a possible customer engagement</p>
          <h3>Discuss a pilot</h3>
          <p>Start with one bounded workflow and a result we can check. Assess the fit and define what a possible pilot would need to demonstrate.</p>
          <details><summary>Explore a pilot</summary><p>Possible starting points include reviewing a generated document against project evidence or checking a scoped agent-assisted change. Scope, responsibilities and commercial terms would need separate agreement.</p><p><Link href="/contact/">Start a conversation <span aria-hidden="true">↗</span></Link></p></details>
        </article>
        <article className={styles["path"]} id="sponsor">
          <p className={styles["path-label"]}>Support work in the open</p>
          <h3>Sponsor open-source milestones</h3>
          <p>Discuss support for a clearly scoped open-source milestone, with its evidence and limits stated up front.</p>
          <details><summary>Explore sponsorship</summary><p>A discussion could connect support with an agreed milestone in usability, documentation or verification. Milestones and any sponsorship terms remain to be defined.</p><p><Link href="/contact/">Start a conversation <span aria-hidden="true">↗</span></Link></p></details>
        </article>
      </div>
    </section>

    <section className={styles["section"] + " " + styles["wrap"] + " " + styles["harness"]} id="harness" aria-labelledby="harness-title">
      <div>
        <p className={styles["eyebrow"]}>The lead project · Attune Harness</p>
        <h2 id="harness-title">Make the work inspectable.</h2>
        <p className={styles["harness-intro"]}>Plan, build, review, fix and test with an explicit scope and retained evidence.</p>
      </div>
      <div className={styles["harness-copy"]}>
        <p>Trustworthy delegation starts with knowing what was authorized, what happened and how the result was checked. Harness records these so you can judge the outcome.</p>
        <div className={styles["principles"]}>
          <div><h3>Authorization has limits.</h3><p>Accepting intent and authorizing execution are separate decisions. Paid calls need their own authorization.</p></div>
          <div><h3>Evidence has limits too.</h3><p>A passing check establishes what it tested. It does not guarantee every output is correct.</p></div>
        </div>
        <div className={styles["release"]}>
          <p><strong>Published: Attune Harness 1.3.0.</strong> <Link href="https://pypi.org/project/attune-harness/1.3.0/">Package and release guide</Link></p>
          <p className={styles["candidate"]}>Browser forms guide intake and intent approval. Each workflow retains its own execution permissions and checks.</p>
          <details><summary>Read the evidence and limits</summary><p>A passing check establishes what it tested. Model adapters and platform support have qualification limits; native MCP panel delivery remains unverified. <Link href="https://pypi.org/project/attune-harness/1.3.0/#what-is-qualified-and-what-is-not">Review the qualification guide</Link>.</p></details>
        </div>
      </div>
    </section>

    <section className={styles["section"] + " " + styles["wrap"]} id="portfolio" aria-labelledby="portfolio-title">
      <div className={styles["section-heading"]}>
        <div><p className={styles["eyebrow"]}>The wider portfolio</p><h2 id="portfolio-title">Memory. Decisions. Sources.</h2></div>
        <p>Related projects with distinct roles. Harness leads; the existing tools remain available.</p>
      </div>
      <div className={styles["portfolio"]}>
        <article className={styles["product"]}><p className={styles["role"]}>Project memory and workflows</p><h3>Attune AI</h3><span className={styles["version"]}><span>v16.4.0</span></span><p>Keep project decisions and lessons available across sessions, with workflows for AI coding agents.</p><Link href="https://github.com/Smart-AI-Memory/attune-ai">Explore Attune AI <span aria-hidden="true">↗</span></Link></article>
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
