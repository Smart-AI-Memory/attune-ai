// Single source of truth for the GUI install command shown
// on the site. Phase 2 (v7.0 release day) flips
// CANONICAL_INSTALL to POST_FOLD_INSTALL in one line.
// See docs/specs/website-update-dashboard-and-fold/.

export const CANONICAL_INSTALL = 'pip install attune-gui';
export const POST_FOLD_INSTALL = 'pip install attune-ai[gui]';

export interface InstallCommandOptions {
  postFold?: boolean;
}

export function installCommand(opts: InstallCommandOptions = {}): string {
  return opts.postFold ? POST_FOLD_INSTALL : CANONICAL_INSTALL;
}
