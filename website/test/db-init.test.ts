import { describe, it, expect, beforeEach, vi } from 'vitest';

vi.mock('@/lib/db', () => ({ initializeDatabase: vi.fn(async () => undefined) }));

import { initializeDatabase } from '@/lib/db';
import { POST, isAuthorized } from '@/app/api/db/init/route';
import { NextRequest } from 'next/server';

const mockedInit = vi.mocked(initializeDatabase);

function post(body: unknown) {
  return new NextRequest('https://smartaimemory.com/api/db/init', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

beforeEach(() => {
  vi.unstubAllEnvs();
  vi.stubEnv('DATABASE_URL', 'postgres://example');
  mockedInit.mockClear();
});

describe('db/init isAuthorized', () => {
  it('fails closed when ADMIN_SECRET is unset', () => {
    vi.stubEnv('ADMIN_SECRET', '');
    expect(isAuthorized('')).toBe(false);
    expect(isAuthorized(undefined)).toBe(false);
  });

  it('refuses an EMPTY secret even when the variable exists but is blank', () => {
    // The production variable sat blank for 80 days; `secret !== env` let
    // `{"secret": ""}` through. Empty must never authorize.
    vi.stubEnv('ADMIN_SECRET', '');
    expect(isAuthorized('')).toBe(false);
  });

  it('accepts only the exact configured secret', () => {
    vi.stubEnv('ADMIN_SECRET', 'admin-secret');
    expect(isAuthorized('admin-secret')).toBe(true);
    expect(isAuthorized('admin-secre')).toBe(false);
    expect(isAuthorized('admin-secret ')).toBe(false);
    expect(isAuthorized(42)).toBe(false);
  });
});

describe('POST /api/db/init', () => {
  it('returns 401 and does not touch the database with a blank secret and blank env', async () => {
    vi.stubEnv('ADMIN_SECRET', '');
    const res = await POST(post({ secret: '' }));
    expect(res.status).toBe(401);
    expect(mockedInit).not.toHaveBeenCalled();
  });

  it('initializes when the secret matches', async () => {
    vi.stubEnv('ADMIN_SECRET', 'admin-secret');
    const res = await POST(post({ secret: 'admin-secret' }));
    expect(res.status).toBe(200);
    expect(mockedInit).toHaveBeenCalledOnce();
  });
});
