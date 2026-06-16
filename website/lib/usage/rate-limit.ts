/**
 * Best-effort per-IP rate limiter for the public usage endpoint.
 *
 * In-memory + per serverless instance, so it resets on cold start and
 * does NOT coordinate across instances. That is deliberate: the usage
 * data is best-effort and the endpoint is spoofable by design (see
 * phase2-design.md). This limiter exists to blunt accidental floods and
 * trivial abuse, not to be an adversarial control.
 *
 * Copyright 2026 Smart-AI-Memory
 * Licensed under Apache 2.0
 */

const WINDOW_MS = 60_000;
const MAX_PER_WINDOW = 120;
/** Bound the map so a spray of unique IPs can't grow it without limit. */
const MAX_KEYS = 10_000;

const hits = new Map<string, number[]>();

export interface RateLimitOptions {
  windowMs?: number;
  max?: number;
  now?: number;
}

/**
 * Record a hit for `key` and return whether it is within the limit.
 *
 * @returns true if allowed, false if the key has exceeded `max` hits in
 *   the trailing `windowMs`.
 */
export function rateLimit(key: string, opts: RateLimitOptions = {}): boolean {
  const windowMs = opts.windowMs ?? WINDOW_MS;
  const max = opts.max ?? MAX_PER_WINDOW;
  const now = opts.now ?? Date.now();
  const cutoff = now - windowMs;

  if (hits.size > MAX_KEYS) hits.clear();

  const recent = (hits.get(key) ?? []).filter((t) => t > cutoff);
  if (recent.length >= max) {
    hits.set(key, recent);
    return false;
  }
  recent.push(now);
  hits.set(key, recent);
  return true;
}

/** Test seam: drop all recorded hits. */
export function _resetRateLimit(): void {
  hits.clear();
}
