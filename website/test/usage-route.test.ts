import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock the DB layer so the route never touches Postgres.
vi.mock('@/lib/db', () => ({
  recordUsageEvents: vi.fn(async (events: unknown[]) => events.length),
}));

import { POST, GET } from '@/app/api/usage/route';
import { recordUsageEvents } from '@/lib/db';
import { _resetRateLimit } from '@/lib/usage/rate-limit';
import { MAX_BODY_BYTES } from '@/lib/usage/validate';
import { NextRequest } from 'next/server';

const mockedRecord = vi.mocked(recordUsageEvents);

function validEvent(over: Record<string, unknown> = {}) {
  return {
    schema: 1,
    package: 'attune-ai',
    version: '8.5.0',
    install_id: '11111111-2222-4333-8444-555555555555',
    event: 'workflow.security_audit',
    os: 'linux',
    py: '3.12',
    ts: '2026-06-16T12:00:00Z',
    ...over,
  };
}

function postReq(body: unknown, headers: Record<string, string> = {}): NextRequest {
  return new NextRequest('https://smartaimemory.com/api/usage', {
    method: 'POST',
    body: typeof body === 'string' ? body : JSON.stringify(body),
    headers: { 'content-type': 'application/json', ...headers },
  });
}

beforeEach(() => {
  _resetRateLimit();
  mockedRecord.mockClear();
});

describe('POST /api/usage', () => {
  it('returns 204 and inserts validated events on a good batch', async () => {
    const res = await POST(postReq({ events: [validEvent()] }));
    expect(res.status).toBe(204);
    expect(mockedRecord).toHaveBeenCalledOnce();
  });

  it('drops the network envelope — no IP/headers reach the DB', async () => {
    await POST(postReq({ events: [validEvent()] }, { 'x-forwarded-for': '203.0.113.7' }));
    const inserted = mockedRecord.mock.calls[0][0];
    expect(inserted).toHaveLength(1);
    // Only frozen-schema columns; nothing carrying the IP or headers.
    expect(Object.keys(inserted[0]).sort()).toEqual(
      ['client_ts', 'event', 'install_id', 'os', 'package', 'py', 'version'].sort()
    );
    expect(JSON.stringify(inserted)).not.toContain('203.0.113.7');
  });

  it('rejects an unknown field with 400 and does not insert', async () => {
    const res = await POST(postReq({ events: [validEvent({ prompt: 'leak' })] }));
    expect(res.status).toBe(400);
    expect(mockedRecord).not.toHaveBeenCalled();
  });

  it('rejects invalid JSON with 400', async () => {
    const res = await POST(postReq('{not json', {}));
    expect(res.status).toBe(400);
  });

  it('rejects an oversized body with 413 before parsing', async () => {
    const huge = 'x'.repeat(MAX_BODY_BYTES + 1);
    const res = await POST(postReq(huge));
    expect(res.status).toBe(413);
    expect(mockedRecord).not.toHaveBeenCalled();
  });

  it('returns 500 (cursor parks) when the DB insert throws', async () => {
    mockedRecord.mockRejectedValueOnce(new Error('db down'));
    const res = await POST(postReq({ events: [validEvent()] }));
    expect(res.status).toBe(500);
  });
});

describe('GET /api/usage', () => {
  it('is not supported (405)', async () => {
    expect((await GET()).status).toBe(405);
  });
});
