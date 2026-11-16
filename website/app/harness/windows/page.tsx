import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata } from '@/lib/metadata';
import styles from './page.module.css';

const SOURCE = 'https://github.com/Smart-AI-Memory/attune-harness/blob/f2baa8b1f9c0acaab2109cbc7facfb029c596586';
const RELEASE_RUN = 'https://github.com/Smart-AI-Memory/attune-harness/actions/runs/43830794405';

export const metadata = generateMetadata({
  title: 'Windows compatibility — Attune Harness 1.8.1',
  description: 'Windows 11, PowerShell and ARM64 guidance for Attune Harness 1.8.1: tested configurations, the path-quoting fix and remaining validation work.',
  url: 'https://smartaimemory.com/harness/windows/',
});

export default function WindowsCompatibilityPage() {
  return (
    <>
      <Navigation />
      <main id="main-content" className={styles.page}>
        <div className={styles.wrap}>
          <nav aria-label="Breadcrumb" className={styles.breadcrumb}>
            <Link href="/">Home</Link><span aria-hidden="true">/</span><Link href="/harness/help/">Harness Help</Link><span aria-hidden="true">/</span><span aria-current="page">Windows</span>
          </nav>

          <header className={styles.hero}>
            <p className={styles.eyebrow}>Attune Harness 1.8.1 · Checked November 16, 2026</p>
            <h1>Work with Harness on Windows.</h1>
            <p className={styles.intro}>Version 1.8.1 fixes prepared PowerShell commands containing Windows paths with spaces, special characters and trailing backslashes. Choose your configuration and see what the tests establish.</p>
            <div className={styles.actions}>
              <a href="#configurations" className={styles.primary}>Check your configuration</a>
              <a href={`${SOURCE}/docs/installation.md#install-181-with-pipx-or-a-virtual-environment`}>Read the 1.8.1 installation guide</a>
            </div>
          </header>

          <section className={styles.section} aria-labelledby="changes-title">
            <h2 id="changes-title">What improves in 1.8.1</h2>
            <div className={styles.benefits}>
              <article>
                <h3>Keep your paths intact</h3>
                <p>Prepared commands preserve spaces, dollar signs, backticks, apostrophes and Unicode characters in Windows PowerShell 5.1 and PowerShell 7.</p>
              </article>
              <article>
                <h3>Keep the next option separate</h3>
                <p>In PowerShell 5.1, a path with whitespace and a trailing backslash no longer consumes the option that follows it.</p>
              </article>
            </div>
            <p>The fix covers setup, plan and repair previews, review intake, and roundtable preparation. When a response is JSON, decode the command value before using it. <a href={`${SOURCE}/docs/release-notes-1.8.1.md#use-your-windows-project-paths`}>Read the release notes</a>.</p>
          </section>

          <section id="configurations" className={styles.section} aria-labelledby="configurations-title">
            <h2 id="configurations-title">Check your configuration</h2>
            <p>Server tests, Windows 11 desktop observations and native ARM64 Python are separate profiles. Results below keep the package version and interpreter that were actually tested.</p>
            <p className={styles.scrollHint}>Scroll the table horizontally to compare all three columns.</p>
            <div className={styles.tableRegion} role="region" aria-label="Windows compatibility by configuration" tabIndex={0}>
              <table>
                <caption>Evidence available for Harness 1.8.1 and earlier Windows runs</caption>
                <thead><tr><th scope="col">Configuration</th><th scope="col">What the evidence shows</th><th scope="col">What remains open</th></tr></thead>
                <tbody>
                  <tr>
                    <th scope="row">Windows Server 2022 and 2025<span>x64 CPython 3.12.10</span></th>
                    <td><strong>Published 1.8.1 wheel passed.</strong> Each server passed 4,550 base tests, with 281 skips, two deselections and two passing subtests. Each also passed 94 offline SDK tests. <a href={RELEASE_RUN}>Release checks</a>.</td>
                    <td>These server results do not establish Windows 11 desktop or browser acceptance.</td>
                  </tr>
                  <tr>
                    <th scope="row">Windows 11 on x64 hardware<span>x64 CPython 3.12.10</span></th>
                    <td><strong>Published 1.8.0 report workflow passed.</strong> Three runs completed across PowerShell 5.1 and 7. Both probes passed 77 tests per run; HTML bytes and protected-file hashes matched. <a href={`${SOURCE}/docs/project-plan.md#windows-11-parity-checkpoint`}>Desktop checkpoint</a>.</td>
                    <td>A fresh 1.8.1 desktop walkthrough, browser inspection and investigation of a separate timed-out run.</td>
                  </tr>
                  <tr>
                    <th scope="row">Windows 11 on ARM64 hardware<span>x64 CPython 3.12.10 under emulation</span></th>
                    <td><strong>227 fix-candidate checks passed</strong> in Parallels across PowerShell 5.1 and 7. They covered argument transport, preparation and intake, including trailing backslashes. <a href={`${SOURCE}/docs/release-readiness-1.8.1.md#earlier-compatibility-evidence`}>Candidate evidence</a>.</td>
                    <td>The tested candidate still had 1.8.0 metadata. Its fix ships in 1.8.1, but this was not a fresh 1.8.1 desktop installation test or native ARM64 Python run.</td>
                  </tr>
                  <tr>
                    <th scope="row">Windows 11 on ARM64 hardware<span>Native ARM64 CPython 3.12</span></th>
                    <td><strong>Binary-only base installation is blocked.</strong> Version 1.8.1 retains <code>tiktoken==0.12.0</code> and <code>cryptography==50.0.2</code>. Neither release provides a Windows ARM64 wheel in the checked PyPI file inventory.</td>
                    <td>Dependency resolution, source-build validation and native ARM64 runtime qualification. The retained 1.8.0 installation attempt stopped at tiktoken; no native Harness workflow ran.</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className={styles.note}>The supplemental <code>windows-latest</code> CI job also uses a Windows Server image. It does not replace a Windows 11 desktop check. <a href="https://github.com/actions/runner-images#available-images">GitHub runner images</a>.</p>
          </section>

          <section className={styles.section} aria-labelledby="architecture-title">
            <h2 id="architecture-title">Choose the right Python architecture</h2>
            <p>An ARM64 Windows device can run x64 Python under emulation. That is the interpreter used in the Parallels results above. Native ARM64 Python is a separate installation and validation path.</p>
            <p>To compare your machine with the recorded desktop configurations, use x64 CPython 3.12 in a fresh environment on fixed local NTFS. Keep existing working environments and saved tasks intact. Start with the <a href={`${SOURCE}/docs/installation.md#install-181-with-pipx-or-a-virtual-environment`}>versioned installation guide</a>, then choose a <a href={`${SOURCE}/docs/supported-journeys.md#windows-capabilities-and-reliability`}>documented Windows workflow</a>.</p>
            <p>Record the hardware architecture, Windows build, Python version and architecture, shell version, and installed Harness version with each result. Python reporting <code>win-amd64</code> identifies its target architecture; it does not prove that the hardware is x64.</p>
          </section>

          <section className={styles.section} aria-labelledby="remaining-title">
            <h2 id="remaining-title">What still needs validation</h2>
            <ul className={styles.checklist}>
              <li><strong>Windows 11 user journeys:</strong> run the revised quickstart with published 1.8.1 and inspect the generated report and status pages in a Windows browser.</li>
              <li><strong>Timeouts and recovery:</strong> investigate the unresolved desktop timeout, verify that every owned child process stops, and check recovery without silently repeating uncertain work.</li>
              <li><strong>Native ARM64 Python:</strong> resolve the installation dependencies, then qualify the installed runtime and its workflows.</li>
              <li><strong>Broader integrations:</strong> complete the separate storage, filesystem, live-provider and Windows Redis service checks before extending those claims.</li>
            </ul>
            <p>Plan acceptance and execution remain separate decisions. Passing software checks does not establish model quality or full Windows parity. <a href={`${SOURCE}/docs/windows-reliability.md`}>Read the reliability requirements</a>.</p>
          </section>

          <section className={styles.section} aria-labelledby="sources-title">
            <h2 id="sources-title">Check the sources</h2>
            <ul className={styles.sources}>
              <li><a href="https://pypi.org/project/attune-harness/1.8.1/#files">Published Harness 1.8.1 files</a> · <a href={RELEASE_RUN}>Publishing run and Windows release checks</a></li>
              <li><a href={`${SOURCE}/docs/release-notes-1.8.1.md`}>1.8.1 release notes</a> · <a href="https://github.com/Smart-AI-Memory/attune-harness/pull/364">PowerShell fix and review</a></li>
              <li><a href={`${SOURCE}/pyproject.toml`}>1.8.1 dependency pins</a> · <a href="https://pypi.org/project/tiktoken/0.12.0/#files">tiktoken files</a> · <a href="https://pypi.org/project/cryptography/50.0.2/#files">cryptography files</a></li>
            </ul>
            <details className={styles.identity}>
              <summary>Exact 1.8.1 release identity</summary>
              <dl>
                <dt>Source commit</dt><dd><code>f2baa8b1f9c0acaab2109cbc7facfb029c596586</code></dd>
                <dt>Wheel</dt><dd><code>attune_harness-1.8.1-py3-none-any.whl</code></dd>
                <dt>Wheel SHA-256</dt><dd><code>f83e924599b0eb0b3d40c428a80cb8fc5794c22cf2341752702cccf2f98ceaae</code></dd>
              </dl>
            </details>
            <p className={styles.note}>The earlier <a href={`${SOURCE}/docs/release-readiness-1.7.0.md`}>1.7.0 release rehearsal</a> and <a href={`${SOURCE}/docs/windows-offline-report.md`}>PowerShell 5.1 offline-report rehearsal</a> retain their original versions and limits. Matching generated HTML bytes is separate from inspecting the report in a desktop browser.</p>
          </section>
        </div>
      </main>
      <Footer />
    </>
  );
}
