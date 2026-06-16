import { describe, it, expect, beforeEach } from 'vitest';
import { rateLimit, _resetRateLimit } from '../lib/usage/rate-limit';

beforeEach(() => _resetRateLimit());

describe('rateLimit', () => {
  it('allows up to max within the window, then blocks', () => {
    const opts = { max: 3, windowMs: 1000, now: 1000 };
    expect(rateLimit('ip-a', opts)).toBe(true);
    expect(rateLimit('ip-a', opts)).toBe(true);
    expect(rateLimit('ip-a', opts)).toBe(true);
    expect(rateLimit('ip-a', opts)).toBe(false); // 4th exceeds max=3
  });

  it('tracks each key independently', () => {
    const opts = { max: 1, windowMs: 1000, now: 1000 };
    expect(rateLimit('ip-a', opts)).toBe(true);
    expect(rateLimit('ip-b', opts)).toBe(true); // different key, fresh budget
    expect(rateLimit('ip-a', opts)).toBe(false);
  });

  it('forgets hits older than the window', () => {
    expect(rateLimit('ip-a', { max: 1, windowMs: 1000, now: 1000 })).toBe(true);
    expect(rateLimit('ip-a', { max: 1, windowMs: 1000, now: 1500 })).toBe(false); // still in window
    expect(rateLimit('ip-a', { max: 1, windowMs: 1000, now: 2500 })).toBe(true); // window passed
  });
});
