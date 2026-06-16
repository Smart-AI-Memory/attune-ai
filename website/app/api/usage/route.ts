/**
 * Usage Ingest API Route (Phase 2b).
 *
 * `POST /api/usage` — public, unauthenticated collection endpoint for the
 * opt-in anonymous usage ping (a CLI can't hold a secret). Validates
 * against frozen schema v1, rejects unknown fields, size-caps the body,
 * best-effort rate-limits per IP, **drops the network envelope (IP +
 * headers)**, inserts, and returns 204.
 *
 * Privacy: nothing here stores IP, headers, or any field outside the
 * frozen schema. The client ships OFF by default and only an opted-in
 * user transmits. See docs/specs/usage-signals/phase2-design.md.
 *
 * Copyright 2026 Smart-AI-Memory
 * Licensed under Apache 2.0
 */

import { NextRequest, NextResponse } from 'next/server';
import { recordUsageEvents } from '@/lib/db';
import { validateBatch, MAX_BODY_BYTES } from '@/lib/usage/validate';
import { rateLimit } from '@/lib/usage/rate-limit';

// pg requires the Node.js runtime; never cache an ingest endpoint.
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

/**
 * Read the client IP for rate-limiting ONLY. It is never stored,
 * logged, or inserted — it leaves this function as a Map key and
 * nothing more.
 */
function clientIp(req: NextRequest): string {
  const xff = req.headers.get('x-forwarded-for');
  if (xff) return xff.split(',')[0].trim();
  return req.headers.get('x-real-ip') ?? 'unknown';
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  // Best-effort per-IP rate limit (IP read transiently, never persisted).
  if (!rateLimit(clientIp(req))) {
    return new NextResponse(null, { status: 429 });
  }

  // Size-cap the body BEFORE parsing.
  let rawText: string;
  try {
    rawText = await req.text();
  } catch {
    return NextResponse.json({ error: 'unreadable body' }, { status: 400 });
  }
  if (Buffer.byteLength(rawText, 'utf8') > MAX_BODY_BYTES) {
    return NextResponse.json({ error: 'payload too large' }, { status: 413 });
  }

  let body: unknown;
  try {
    body = JSON.parse(rawText);
  } catch {
    return NextResponse.json({ error: 'invalid JSON' }, { status: 400 });
  }

  const result = validateBatch(body);
  if (!result.ok) {
    return NextResponse.json({ error: result.error }, { status: result.status });
  }

  try {
    await recordUsageEvents(result.events);
  } catch (error) {
    console.error('usage ingest failed:', error);
    // 5xx → the client leaves its cursor parked and retries next run.
    return NextResponse.json({ error: 'ingest failed' }, { status: 500 });
  }

  // 204: accepted, no body. The client advances its cursor on any 2xx.
  return new NextResponse(null, { status: 204 });
}

/** Only POST is supported. */
export async function GET(): Promise<NextResponse> {
  return new NextResponse(null, { status: 405 });
}
