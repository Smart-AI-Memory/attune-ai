import type { Metadata } from 'next';
import { generateMetadata as generateSEOMetadata } from '@/lib/metadata';

export const metadata: Metadata = generateSEOMetadata({
  title: 'Contact Us',
  description: 'Get in touch with the Smart AI Memory team. Questions about the framework, partnerships, or technical support.',
  url: 'https://smartaimemory.com/contact',
  keywords: [
    'contact Smart AI Memory',
    'AI framework support',
    'partnership inquiry',
    'technical support',
  ],
});

export default function ContactLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
