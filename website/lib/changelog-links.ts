import historicalLinks from './changelog-historical-links.json';

const repository = 'https://github.com/Smart-AI-Memory/attune-ai';
const archived: Record<string, string | null> = historicalLinks;

/** Resolve repository-relative release references without rewriting website URLs. */
export function resolveChangelogLink(href: string): string | null {
  if (!href || /^(?:[a-z][a-z0-9+.-]*:|[/#?])/i.test(href)) return href;
  const [, target, suffix] = href.match(/^([^?#]*)(.*)$/)!;
  const relativePath = target.replace(/^\.\//, '');
  if (Object.hasOwn(archived, relativePath)) {
    const destination = archived[relativePath];
    return destination === null ? null : destination + suffix;
  }
  // Unknown repository paths stay visible; the content test checks they exist.
  const kind = relativePath.endsWith('/') ? 'tree' : 'blob';
  return `${repository}/${kind}/main/${relativePath}${suffix}`;
}
