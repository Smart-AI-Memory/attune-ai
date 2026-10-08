import { timingSafeEqual } from 'node:crypto';

/** Constant-time string compare that tolerates unequal lengths. */
function secretsMatch(a: string, b: string): boolean {
  const ab = Buffer.from(a, 'utf8');
  const bb = Buffer.from(b, 'utf8');
  if (ab.length !== bb.length) return false;
  return timingSafeEqual(ab, bb);
}

/**
 * Fails closed: with ADMIN_SECRET unset or EMPTY nothing is authorized.
 * A plain `secret !== process.env.ADMIN_SECRET` let `{"secret": ""}`
 * through whenever the variable existed with no value (found live
 * 2026-09-04 — the production variable had been empty for 80 days).
 */
export function isAuthorized(secret: unknown): boolean {
  const admin = process.env.ADMIN_SECRET;
  if (!admin) return false;
  return typeof secret === 'string' && secretsMatch(secret, admin);
}
