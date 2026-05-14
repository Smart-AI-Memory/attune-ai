#!/usr/bin/env tsx
// Build-time guard for the migration banner.
//
// Fails the build if today's date is past
// MIGRATION_BANNER.fallbackHideDate AND the banner is
// still enabled. Forces an explicit decision to either
// retire the banner or push out the safety date rather
// than letting a stale banner linger silently.
//
// See contract C-4 in
// docs/specs/website-update-dashboard-and-fold/requirements.md.

import { MIGRATION_BANNER } from '../lib/migration-banner';

function parseDate(iso: string): Date {
  const parsed = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) {
    throw new Error(
      `migration-banner.ts: fallbackHideDate "${iso}" is not a valid ISO date (YYYY-MM-DD).`,
    );
  }
  return parsed;
}

function main(): void {
  const fallback = parseDate(MIGRATION_BANNER.fallbackHideDate);
  const today = new Date();

  if (MIGRATION_BANNER.enabled && today > fallback) {
    console.error(
      [
        '✗ Migration banner is still enabled but the fallback hide date',
        `  (${MIGRATION_BANNER.fallbackHideDate}) has passed.`,
        '',
        '  Either:',
        '    - Set MIGRATION_BANNER.enabled = false in website/lib/migration-banner.ts',
        '    - Or push out fallbackHideDate to a new safety net.',
      ].join('\n'),
    );
    process.exit(1);
  }

  console.info(
    `✓ Migration banner check passed (enabled=${MIGRATION_BANNER.enabled}, fallbackHideDate=${MIGRATION_BANNER.fallbackHideDate}).`,
  );
}

main();
