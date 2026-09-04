import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock only the DB-touching collector; keep the real renderer so the
// email body under test is the one that actually ships.
vi.mock('@/lib/usage/digest', async () => {
  const actual = await vi.importActual<typeof import('@/lib/usage/digest')>('@/lib/usage/digest');
  return { ...actual, collectUsageDigest: vi.fn() };
});
vi.mock('@/lib/email', () => ({ sendEmail: vi.fn(async () => true) }));

import {
  collectUsageDigest,
  renderUsageDigest,
  formatDelta,
  prettyWorkflow,
  type UsageDigest,
} from '@/lib/usage/digest';
import { sendEmail } from '@/lib/email';
import { GET, POST, isAuthorized } from '@/app/api/cron/usage-digest/route';
import { NextRequest } from 'next/server';

const mockedCollect = vi.mocked(collectUsageDigest);
const mockedSend = vi.mocked(sendEmail);

function digest(over: Partial<UsageDigest> = {}): UsageDigest {
  return {
    windowStart: '2026-08-18T12:00:00.000Z',
    windowEnd: '2026-08-19T12:00:00.000Z',
    events: 12,
    activeInstalls: 4,
    newInstalls: 2,
    prevEvents: 9,
    prevActiveInstalls: 5,
    topWorkflows: [
      { label: 'workflow.security_audit', events: 7, installs: 3 },
      { label: 'workflow.code_review', events: 5, installs: 2 },
    ],
    osMix: [{ label: 'darwin', events: 12, installs: 4 }],
    pyMix: [{ label: '3.12', events: 12, installs: 4 }],
    versionMix: [{ label: '12.0.0', events: 12, installs: 4 }],
    totalEvents: 480,
    totalInstalls: 61,
    ...over,
  };
}

function req(url = 'https://smartaimemory.com/api/cron/usage-digest', headers: Record<string, string> = {}) {
  return new NextRequest(url, { method: 'GET', headers });
}

const AUTH = { authorization: 'Bearer test-secret' };

beforeEach(() => {
  vi.unstubAllEnvs();
  vi.stubEnv('CRON_SECRET', 'test-secret');
  vi.stubEnv('USAGE_DIGEST_TO', 'patrick@example.com');
  mockedCollect.mockReset();
  mockedSend.mockReset();
  mockedSend.mockResolvedValue(true);
});

describe('renderUsageDigest', () => {
  it('leads the subject with new installs when there are any', () => {
    const { subject } = renderUsageDigest(digest());
    expect(subject).toBe('attune-ai: 2 new installs, 12 runs (2026-08-18)');
  });

  it('falls back to active installs when nothing is new', () => {
    const { subject } = renderUsageDigest(digest({ newInstalls: 0 }));
    expect(subject).toBe('attune-ai: 12 runs from 4 installs (2026-08-18)');
  });

  it('singularises a lone install and a lone run', () => {
    const { subject } = renderUsageDigest(digest({ newInstalls: 1, events: 1 }));
    expect(subject).toBe('attune-ai: 1 new install, 1 run (2026-08-18)');
  });

  it('shows workflow names without the registry prefix', () => {
    const { html, text } = renderUsageDigest(digest());
    expect(html).toContain('security_audit');
    expect(html).not.toContain('workflow.security_audit');
    expect(text).toContain('code_review');
  });

  it('renders both deltas against the prior window', () => {
    const { text } = renderUsageDigest(digest());
    expect(text).toContain('Workflow runs   12  (+3 vs prior 24h)');
    expect(text).toContain('Active installs 4  (-1 vs prior 24h)');
  });

  it('carries lifetime totals and the anonymity caveat', () => {
    const { html, text } = renderUsageDigest(digest());
    expect(html).toContain('480');
    expect(html).toContain('61');
    expect(text).toContain('rotating, user-resettable UUID');
  });

  it('never emits an email that could carry identity fields', () => {
    const { html, text } = renderUsageDigest(digest());
    for (const forbidden of ['@', 'ip', 'email', 'address']) {
      // The only '@' allowed is in none of the body; identity words must
      // not appear as data. Guard against a future field being added.
      if (forbidden === '@') continue;
      expect(text.toLowerCase()).not.toContain(`${forbidden}:`);
    }
    expect(html).not.toMatch(/\b\d{1,3}(\.\d{1,3}){3}\b/); // no IPv4
  });

  it('omits a breakdown table entirely when it has no rows', () => {
    const { html } = renderUsageDigest(digest({ osMix: [], pyMix: [], versionMix: [] }));
    expect(html).not.toContain('Operating system');
    expect(html).toContain('Workflows run');
  });
});

describe('formatDelta', () => {
  it('signs increases, decreases, and no change', () => {
    expect(formatDelta(5, 2)).toBe('+3');
    expect(formatDelta(2, 5)).toBe('-3');
    expect(formatDelta(4, 4)).toBe('±0');
  });
});

describe('prettyWorkflow', () => {
  it('strips the prefix and leaves anything else alone', () => {
    expect(prettyWorkflow('workflow.doc_gen')).toBe('doc_gen');
    expect(prettyWorkflow('doc_gen')).toBe('doc_gen');
  });
});

describe('GET /api/cron/usage-digest', () => {
  it('rejects an unauthenticated call', async () => {
    const res = await GET(req());
    expect(res.status).toBe(401);
    expect(mockedCollect).not.toHaveBeenCalled();
  });

  it('rejects a wrong bearer token', async () => {
    const res = await GET(req(undefined, { authorization: 'Bearer nope' }));
    expect(res.status).toBe(401);
  });

  it('fails closed when no secret is configured at all', () => {
    vi.stubEnv('CRON_SECRET', '');
    vi.stubEnv('ADMIN_SECRET', '');
    expect(isAuthorized(req(undefined, AUTH))).toBe(false);
  });

  it('accepts the ADMIN_SECRET header as a manual fallback', () => {
    vi.stubEnv('CRON_SECRET', '');
    vi.stubEnv('ADMIN_SECRET', 'admin-secret');
    expect(isAuthorized(req(undefined, { 'x-admin-secret': 'admin-secret' }))).toBe(true);
  });

  it('checks each header against its own secret when BOTH are configured', () => {
    // The production shape: CRON_SECRET for Vercel, ADMIN_SECRET for a human.
    // A single `CRON_SECRET || ADMIN_SECRET` pick compared the admin header
    // against the cron secret and locked the manual path out (found live
    // 2026-09-04 with a real ADMIN_SECRET returning 401).
    vi.stubEnv('CRON_SECRET', 'cron-secret');
    vi.stubEnv('ADMIN_SECRET', 'admin-secret');
    expect(isAuthorized(req(undefined, { 'x-admin-secret': 'admin-secret' }))).toBe(true);
    expect(isAuthorized(req(undefined, { authorization: 'Bearer cron-secret' }))).toBe(true);
    // Cross-use is not accepted: the admin value is not a bearer, and vice versa.
    expect(isAuthorized(req(undefined, { 'x-admin-secret': 'cron-secret' }))).toBe(false);
    expect(isAuthorized(req(undefined, { authorization: 'Bearer admin-secret' }))).toBe(false);
  });

  it('sends the digest when there was activity', async () => {
    mockedCollect.mockResolvedValue(digest());
    const res = await GET(req(undefined, AUTH));
    expect(res.status).toBe(200);
    expect(mockedSend).toHaveBeenCalledOnce();
    const msg = mockedSend.mock.calls[0][0];
    expect(msg.to).toBe('patrick@example.com');
    expect(msg.subject).toContain('2 new installs');
    expect(msg.html).toBeTruthy();
    expect(msg.text).toBeTruthy();
  });

  it('sends nothing on a zero-activity day', async () => {
    mockedCollect.mockResolvedValue(digest({ events: 0, activeInstalls: 0, newInstalls: 0 }));
    const res = await GET(req(undefined, AUTH));
    expect(res.status).toBe(200);
    expect(await res.json()).toMatchObject({ skipped: 'no activity' });
    expect(mockedSend).not.toHaveBeenCalled();
  });

  it('renders but does not send on a dry run', async () => {
    mockedCollect.mockResolvedValue(digest());
    const res = await GET(
      req('https://smartaimemory.com/api/cron/usage-digest?dry=1', AUTH)
    );
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.dryRun).toBe(true);
    expect(body.html).toContain('attune-ai usage');
    expect(mockedSend).not.toHaveBeenCalled();
  });

  it('reports a 500 when the query fails, so the cron run shows red', async () => {
    mockedCollect.mockRejectedValue(new Error('pg down'));
    const res = await GET(req(undefined, AUTH));
    expect(res.status).toBe(500);
    expect(mockedSend).not.toHaveBeenCalled();
  });

  it('reports a 500 when delivery fails', async () => {
    mockedCollect.mockResolvedValue(digest());
    mockedSend.mockResolvedValue(false);
    const res = await GET(req(undefined, AUTH));
    expect(res.status).toBe(500);
  });

  it('errors clearly when no recipient is configured', async () => {
    vi.stubEnv('USAGE_DIGEST_TO', '');
    vi.stubEnv('CONTACT_EMAIL', '');
    const res = await GET(req(undefined, AUTH));
    expect(res.status).toBe(500);
    expect((await res.json()).error).toContain('USAGE_DIGEST_TO');
  });

  it('does not support POST', async () => {
    expect((await POST()).status).toBe(405);
  });
});
