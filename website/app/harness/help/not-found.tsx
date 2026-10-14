import Link from 'next/link';
import { HELP_ROOT, topicHref } from '@/lib/harness-help/topics';

export default function HelpNotFound() {
  return <>
    <h1>Help topic unavailable</h1>
    <p>This topic is not part of the Harness 1.3.0 guide.</p>
    <p><Link href={HELP_ROOT}>Browse all help topics</Link> or <Link href={topicHref('dependencies')}>check version guidance</Link>.</p>
  </>;
}
