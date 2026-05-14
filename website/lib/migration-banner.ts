// Migration banner lifecycle config. See contract C-4 in
// docs/specs/website-update-dashboard-and-fold/requirements.md.
//
// Pre-fold (current state): banner is HIDDEN. PR-B will add
// the component that consumes this config and renders on
// the homepage. Phase 2 (v7.0 day) flips the pin to v7.0
// and re-enables.
//
// fallbackHideDate is the safety net: if today is past
// that date and the banner is still rendering, the
// build-time check (scripts/check-migration-banner.ts)
// fails the build, forcing an explicit decision.

export interface MigrationBannerConfig {
  // Show the banner when current package version is >=
  // this value. Empty string disables the banner.
  showFromVersion: string;
  // Hide the banner when current package version is >=
  // this value (exclusive — banner gone in this release).
  hideFromVersion: string;
  // Safety net: if today's date is past this AND the
  // banner is still rendering, build fails.
  fallbackHideDate: string; // ISO YYYY-MM-DD
  // Convenience flag the component reads. Pre-fold this
  // is false; PR-B's homepage wires it.
  enabled: boolean;
}

export const MIGRATION_BANNER: MigrationBannerConfig = {
  showFromVersion: '',
  hideFromVersion: '7.1.0',
  fallbackHideDate: '2026-06-15',
  enabled: false,
};
