import type { Metadata } from 'next';
import { generateMetadata as generateSEOMetadata } from '@/lib/metadata';

export const metadata: Metadata = generateSEOMetadata({
  title: 'Distributed Memory Demo',
  description: 'Interactive demo of multi-agent shared memory, pattern conflict resolution, and team coordination in the Attune AI framework.',
  url: 'https://smartaimemory.com/demo/distributed-memory',
  keywords: [
    'distributed memory',
    'multi-agent demo',
    'pattern conflict resolution',
    'AI agent coordination',
  ],
});

export default function DemoLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
