import release from '@/content/harness-help/release.json';

export const HARNESS_VERSION = release.version;
export const HARNESS_RELEASE_SLUG = release.slug;
export const HARNESS_PUBLISHED = release.status === 'published';
export const HARNESS_SOURCE_REF = release.source_ref;
export const HARNESS_SOURCE_ROOT = `https://github.com/Smart-AI-Memory/attune-harness/blob/${HARNESS_SOURCE_REF}`;
export const HARNESS_PACKAGE_URL = `https://pypi.org/project/attune-harness/${HARNESS_PUBLISHED ? HARNESS_VERSION : release.published_version}/`;
export const HARNESS_RELEASE_NOTICE = HARNESS_PUBLISHED
  ? `Released Harness ${HARNESS_VERSION}.`
  : `Preparation for Harness ${HARNESS_VERSION}; not yet released. Use published ${release.published_version} until publication.`;
