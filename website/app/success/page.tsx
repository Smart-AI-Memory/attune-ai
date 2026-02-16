import type { Metadata } from 'next';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata } from '@/lib/metadata';

export const metadata: Metadata = generateMetadata({
  title: 'Payment Successful',
  description: 'Thank you for your purchase!',
  url: 'https://smartaimemory.com/success',
});

export default function SuccessPage() {
  return (
    <>
      <Navigation />
      <main id="main-content" className="min-h-screen pt-16">
        <section className="py-20">
          <div className="container">
            <div className="max-w-2xl mx-auto text-center">
              <div className="text-6xl mb-6">✓</div>
              <h1 className="text-4xl font-bold mb-6 text-[var(--success)]">
                Payment Successful!
              </h1>
              <p className="text-xl text-[var(--text-secondary)] mb-8">
                Thank you for your purchase. You should receive a confirmation email shortly.
              </p>

              <div className="bg-[var(--border)] bg-opacity-30 rounded-lg p-8 mb-8">
                <h2 className="text-xl font-bold mb-4">What happens next?</h2>
                <ul className="text-left space-y-3 text-[var(--text-secondary)]">
                  <li className="flex items-start gap-3">
                    <span className="text-[var(--success)]">1.</span>
                    <span>Check your email for order confirmation and receipt</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="text-[var(--success)]">2.</span>
                    <span>If you purchased the book, download links will be sent to your email</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="text-[var(--success)]">3.</span>
                    <span>For license purchases, your license key will be emailed within 24 hours</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="text-[var(--success)]">4.</span>
                    <span>Questions? Contact us at admin@smartaimemory.com</span>
                  </li>
                </ul>
              </div>

              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link href="/" className="btn btn-primary">
                  Return Home
                </Link>
                <Link href="/docs" className="btn btn-outline">
                  View Documentation
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
