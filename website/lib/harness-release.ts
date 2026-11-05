// Published installation and preparation have separate, source-bound identities.
import build from '@/public/harness-help-static/build.json';
import published from '@/public/harness-help-static/release-1.6.0.json';
import source from '@/public/harness-help-static/import.json';

export const HARNESS_PUBLISHED_VERSION = build.published_version;
export const HARNESS_TARGET_VERSION = '1.7.0';
export const HARNESS_GET_STARTED = '/harness/help/get-started/';
export const HARNESS_PREPARATION = '/harness/help/1-7-0-preparation/';
export const HARNESS_PACKAGE_URL = `https://pypi.org/project/attune-harness/${HARNESS_PUBLISHED_VERSION}/`;
export const HARNESS_SOURCE_ROOT = `https://github.com/Smart-AI-Memory/attune-harness/blob/${published.source_commit}`;
export const HARNESS_PREPARATION_SOURCE_ROOT = `https://github.com/Smart-AI-Memory/attune-harness/blob/${source.source_commit}`;
export const HARNESS_INSTALL_COMMAND = `uv tool install --python 3.12 'attune-harness==${HARNESS_PUBLISHED_VERSION}'`;
export const HARNESS_RELEASE_NOTICE = `Published: Attune Harness ${HARNESS_PUBLISHED_VERSION}.`;
export const HARNESS_PREPARATION_NOTICE = `Harness ${HARNESS_TARGET_VERSION} is in preparation. Use the published release for installation.`;
