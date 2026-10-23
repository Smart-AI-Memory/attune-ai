import type { Metadata } from 'next';
import guide from '@/content/harness-help/goal-guide.generated.json';
import { HARNESS_PUBLISHED, HARNESS_VERSION } from '@/lib/harness-help/release';
import GuideControls from './GuideControls';
import './goals.css';

export const metadata: Metadata = {
  title: 'What do you want to accomplish?',
  description: `Choose a goal and follow prompts, instructions and review points for Harness ${HARNESS_VERSION}.`,
  alternates: { canonical: 'https://smartaimemory.com/harness/help/goals/' },
  robots: { index: HARNESS_PUBLISHED, follow: true },
};

export default function GoalsPage() {
  return (
    <GuideControls data={guide.data}>
      {/* The projector validates the checked-in content before it is rendered. */}
      <div dangerouslySetInnerHTML={{ __html: guide.html }} />
    </GuideControls>
  );
}
