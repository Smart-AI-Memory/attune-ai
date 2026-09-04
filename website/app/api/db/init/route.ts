import { timingSafeEqual } from 'node:crypto';
import { NextRequest, NextResponse } from 'next/server';
import { initializeDatabase } from '@/lib/db';

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

// This endpoint initializes the database schema
// Should only be called once during setup, protected by a secret
export async function POST(req: NextRequest) {
  try {
    // Check for admin secret
    const { secret } = await req.json();

    if (!isAuthorized(secret)) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    if (!process.env.DATABASE_URL) {
      return NextResponse.json(
        { error: 'DATABASE_URL is not configured' },
        { status: 500 }
      );
    }

    await initializeDatabase();

    return NextResponse.json({
      success: true,
      message: 'Database schema initialized successfully',
    });
  } catch (error) {
    console.error('Database initialization error:', error);
    return NextResponse.json({ error: 'Database initialization failed' }, { status: 500 });
  }
}
