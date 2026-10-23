// Website entry points read the canonical Help export after the #2574 cutover.
import release from '@/public/harness-help-static/build.json';
import preparation from '@/public/harness-help-static/preparation.json';

export const HARNESS_VERSION = release.version;
export const HARNESS_RELEASE_SLUG = release.version.replaceAll('.', '-');
export const HARNESS_PUBLISHED = release.status === 'published';
export const HARNESS_SOURCE_REF = HARNESS_PUBLISHED
  ? release.behavior_commit
  : preparation.documentation_commit;
export const HARNESS_SOURCE_ROOT = `https://github.com/Smart-AI-Memory/attune-harness/blob/${HARNESS_SOURCE_REF}`;
export const HARNESS_PACKAGE_URL = `https://pypi.org/project/attune-harness/${HARNESS_PUBLISHED ? HARNESS_VERSION : release.published_version}/`;
export const HARNESS_RELEASE_NOTICE = HARNESS_PUBLISHED
  ? `Released Harness ${HARNESS_VERSION}.`
  : `Preparation for Harness ${HARNESS_VERSION}; not yet released. Use published ${release.published_version} until publication.`;
