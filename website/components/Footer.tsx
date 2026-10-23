import { HARNESS_PACKAGE_URL } from '@/lib/harness-release';
import Link from 'next/link';
import styles from './Footer.module.css';

const linkClass = 'text-sm text-[var(--text-secondary)] hover:text-[var(--primary)] transition-colors';

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t border-[var(--border)] bg-[var(--background)]" role="contentinfo">
      <div className="container py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
          <div>
            <Link href="/" className="text-xl font-bold text-gradient hover:opacity-80 transition-opacity">Smart AI Memory</Link>
            <p className="mt-4 text-sm text-[var(--text-secondary)]">Attune Harness for AI-assisted engineering: clearer decisions, checkable work and context you can revisit.</p>
            <a href="https://github.com/Smart-AI-Memory/attune-harness" target="_blank" rel="noopener noreferrer" className={linkClass + ' inline-block mt-4'}>Attune Harness on GitHub</a>
          </div>
          <div>
            <h3 className={styles.heading}>Attune Harness</h3>
            <ul className="space-y-2">
              <li><Link href="/#harness" className={linkClass}>What you can do</Link></li>
              <li><Link href="/harness/help/" className={linkClass}>Harness Help Center</Link></li>
              <li><Link href="/harness/help/goals/" className={linkClass}>Browse all goals</Link></li>
              <li><Link href="/#context" className={linkClass}>Context and next steps</Link></li>
              <li><Link href="/#collaborate" className={linkClass}>Collaborate</Link></li>
              <li><Link href="/blog" className={linkClass}>Blog</Link></li>
              <li><Link href="/contact" className={linkClass}>Contact</Link></li>
            </ul>
          </div>
          <div>
            <h3 className={styles.heading}>Resources</h3>
            <ul className="space-y-2">
              <li><a href={HARNESS_PACKAGE_URL} target="_blank" rel="noopener noreferrer" className={linkClass}>Harness package and release guide</a></li>
              <li><Link href="/#portfolio" className={linkClass}>Supporting tools and earlier work</Link></li>
              <li><Link href="/faq/#attune-ai-reference-questions" className={linkClass}>Historical project references</Link></li>
              <li><Link href="/pricing" className={linkClass}>Harness open-source license</Link></li>
              <li><Link href="/discipline" className={linkClass}>The Discipline</Link></li>
            </ul>
          </div>
        </div>
        <div className="pt-8 border-t border-[var(--border)] flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="text-sm text-[var(--muted)] text-center md:text-left">
            &copy; {currentYear} Smart AI Memory &middot; <a href="https://github.com/Smart-AI-Memory/attune-ai/blob/main/LICENSE" target="_blank" rel="noopener noreferrer" className="hover:text-[var(--primary)]">Apache 2.0 License</a>
          </div>
          <div className="flex gap-6 text-xs text-[var(--muted)]">
            <Link href="/privacy" className="hover:text-[var(--primary)]">Privacy</Link>
            <Link href="/terms" className="hover:text-[var(--primary)]">Terms</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
