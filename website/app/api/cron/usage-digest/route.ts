/**
 * `GET /api/cron/usage-digest` — daily usage digest email.
 *
 * Invoked by Vercel Cron (see `crons` in vercel.json), which sends
 * `Authorization: Bearer $CRON_SECRET`. Also callable by hand with
 * `x-admin-secret: $ADMIN_SECRET` (each header is checked against its
 * own secret), so the digest can be previewed or re-sent without
 * waiting for the schedule.
 *
 * Behaviour:
 *   - No secret configured  → 500. Fails closed; never runs unauthenticated.
 *   - Zero events in window → 200 `{ skipped: "no activity" }`, no email.
 *     A silent day sends nothing, so the digest never becomes noise.
 *   - `?dry=1`              → renders and returns the email, sends nothing.
 *
 * Reads only anonymous aggregate counts (see lib/usage/digest.ts).
 *
 * Copyright 2026 Smart-AI-Memory
 * Licensed under Apache 2.0
 */

import { timingSafeEqual } from 'node:crypto';
import { NextRequest, NextResponse } from 'next/server';
import { collectUsageDigest, renderUsageDigest } from '@/lib/usage/digest';
import { sendEmail } from '@/lib/email/sendgrid';

// pg requires the Node.js runtime; a cron result must never be cached.
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

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

/** Where the digest goes. Explicit override, else the contact inbox. */
function recipient(): string | null {
  return process.env.USAGE_DIGEST_TO || process.env.CONTACT_EMAIL || null;
}

export async function GET(req: NextRequest): Promise<NextResponse> {
  if (!isAuthorized(req)) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const to = recipient();
  if (!to) {
    return NextResponse.json(
      { error: 'USAGE_DIGEST_TO (or CONTACT_EMAIL) is not configured' },
      { status: 500 }
    );
  }

  let digest;
  try {
    digest = await collectUsageDigest(new Date());
  } catch (error) {
    console.error('usage digest query failed:', error);
    return NextResponse.json({ error: 'digest query failed' }, { status: 500 });
  }

  const rendered = renderUsageDigest(digest);
  const dry = req.nextUrl.searchParams.get('dry') === '1';

  if (dry) {
    return NextResponse.json({
      dryRun: true,
      to,
      subject: rendered.subject,
      digest,
      html: rendered.html,
    });
  }

  // A day with no activity sends nothing — silence keeps the digest useful.
  if (digest.events === 0) {
    return NextResponse.json({
      skipped: 'no activity',
      window: { start: digest.windowStart, end: digest.windowEnd },
    });
  }

  const sent = await sendEmail({
    to,
    subject: rendered.subject,
    html: rendered.html,
    text: rendered.text,
  });

  if (!sent) {
    // 5xx so a delivery failure is visible in the Vercel cron run log.
    return NextResponse.json({ error: 'email send failed' }, { status: 500 });
  }

  return NextResponse.json({
    sent: true,
    to,
    subject: rendered.subject,
    events: digest.events,
    newInstalls: digest.newInstalls,
    activeInstalls: digest.activeInstalls,
  });
}

/** Vercel Cron issues GET; nothing else is supported. */
export async function POST(): Promise<NextResponse> {
  return new NextResponse(null, { status: 405 });
}
