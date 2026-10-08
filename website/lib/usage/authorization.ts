import { timingSafeEqual } from 'node:crypto';
import type { NextRequest } from 'next/server';

/** Constant-time string compare that tolerates unequal lengths. */
function secretsMatch(a: string, b: string): boolean {
  const ab = Buffer.from(a, 'utf8');
  const bb = Buffer.from(b, 'utf8');
  if (ab.length !== bb.length) return false;
  return timingSafeEqual(ab, bb);
}

/**
 * Authorize the caller. Fails closed: with no secret in the environment
 * nothing is authorized, so a misconfigured deploy cannot leak counts.
 */
export function isAuthorized(req: NextRequest): boolean {
  // Each header is compared against ITS OWN secret. Picking one secret
  // (`CRON_SECRET || ADMIN_SECRET`) and checking both headers against it
  // meant that once CRON_SECRET existed, the admin header was compared
  // against the cron secret and the manual path could never authorize.
  const cron = process.env.CRON_SECRET;
  const admin = process.env.ADMIN_SECRET;
  if (!cron && !admin) return false;

  const auth = req.headers.get('authorization');
  if (cron && auth?.startsWith('Bearer ') && secretsMatch(auth.slice(7), cron)) return true;

  const header = req.headers.get('x-admin-secret');
  if (admin && header && secretsMatch(header, admin)) return true;

  return false;
}
