/**
 * Usage-event validation (Phase 2b).
 *
 * The collection endpoint is public and unauthenticated (a CLI can't
 * hold a secret), so validation is the primary defense. Two jobs:
 *
 *  1. Reject anything that isn't exactly the frozen schema-v1 payload —
 *     **including unknown fields** — so the payload can never quietly
 *     grow free-text columns release-over-release (the spec's R2 frozen
 *     payload). This mirrors the Python client's PAYLOAD_KEYS freeze.
 *  2. Bound every field length so a spoofer can't bloat the table.
 *
 * The data is treated as best-effort, not adversarially trusted (an
 * unauthenticated endpoint is spoofable by design — see phase2-design.md).
 *
 * Copyright 2026 Smart-AI-Memory
 * Licensed under Apache 2.0
 */

import type { UsageEventInsert } from '@/lib/db';

/** Frozen schema version. Bump in lockstep with the Python client. */
export const SCHEMA_VERSION = 1;

/**
 * The EXACT set of keys a client payload may carry (schema v1). Mirrors
 * the Python client's PAYLOAD_KEYS. Any other key rejects the event.
 */
export const ALLOWED_KEYS = new Set([
  'schema',
  'package',
  'version',
  'install_id',
  'event',
  'os',
  'py',
  'ts',
]);

/** Per-request caps (defense against a spoofer bloating the table). */
export const MAX_EVENTS_PER_REQUEST = 200;
export const MAX_BODY_BYTES = 256 * 1024; // 256 KB

/** Field length caps. */
const LIMITS = {
  package: 64,
  version: 32,
  event: 96,
  os: 32,
  py: 16,
} as const;

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
// event is registry-sourced on the client: "workflow.<name>". Keep the
// grammar tight so it can never carry free-text.
const EVENT_RE = /^workflow\.[a-z0-9._-]{1,80}$/i;

export type ValidationResult =
  | { ok: true; value: UsageEventInsert }
  | { ok: false; error: string };

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

function cappedString(v: unknown, max: number): string | null {
  if (typeof v !== 'string') return null;
  const s = v.trim();
  if (s.length === 0 || s.length > max) return null;
  return s;
}

/** Normalize a client `ts` to an ISO string for `client_ts`, or null. */
function normalizeTs(v: unknown): string | null {
  if (typeof v !== 'string' || v.trim() === '') return null;
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

/**
 * Validate one raw client event against schema v1.
 *
 * Strict: unknown keys reject; every field is type- and length-checked.
 * Maps the client's `ts` to `client_ts` and drops `schema` (it's a
 * version gate, not stored).
 */
export function validateEvent(raw: unknown): ValidationResult {
  if (!isPlainObject(raw)) {
    return { ok: false, error: 'event is not an object' };
  }

  // Reject unknown fields outright — frozen-payload defense.
  for (const key of Object.keys(raw)) {
    if (!ALLOWED_KEYS.has(key)) {
      return { ok: false, error: `unknown field: ${key}` };
    }
  }

  if (raw.schema !== SCHEMA_VERSION) {
    return { ok: false, error: `unsupported schema: ${String(raw.schema)}` };
  }

  const pkg = cappedString(raw.package, LIMITS.package);
  if (!pkg) return { ok: false, error: 'invalid package' };

  const version = cappedString(raw.version, LIMITS.version);
  if (!version) return { ok: false, error: 'invalid version' };

  const install_id = typeof raw.install_id === 'string' ? raw.install_id.trim() : '';
  if (!UUID_RE.test(install_id)) {
    return { ok: false, error: 'invalid install_id' };
  }

  const event = cappedString(raw.event, LIMITS.event);
  if (!event || !EVENT_RE.test(event)) {
    return { ok: false, error: 'invalid event' };
  }

  // os / py are optional but, when present, must be sane short strings.
  const os = raw.os === undefined || raw.os === null ? null : cappedString(raw.os, LIMITS.os);
  if (raw.os !== undefined && raw.os !== null && os === null) {
    return { ok: false, error: 'invalid os' };
  }
  const py = raw.py === undefined || raw.py === null ? null : cappedString(raw.py, LIMITS.py);
  if (raw.py !== undefined && raw.py !== null && py === null) {
    return { ok: false, error: 'invalid py' };
  }

  return {
    ok: true,
    value: {
      package: pkg,
      version,
      install_id,
      event,
      os,
      py,
      client_ts: normalizeTs(raw.ts),
    },
  };
}

export type BatchResult =
  | { ok: true; events: UsageEventInsert[] }
  | { ok: false; status: number; error: string };

/**
 * Validate a parsed request body of shape `{ events: [...] }`.
 *
 * Returns the HTTP status to use on failure so the route stays thin:
 * 413 for too many events, 400 for anything malformed.
 */
export function validateBatch(body: unknown): BatchResult {
  if (!isPlainObject(body) || !Array.isArray(body.events)) {
    return { ok: false, status: 400, error: 'body must be { events: [...] }' };
  }
  const events = body.events;
  if (events.length === 0) {
    return { ok: false, status: 400, error: 'events is empty' };
  }
  if (events.length > MAX_EVENTS_PER_REQUEST) {
    return { ok: false, status: 413, error: 'too many events' };
  }

  const out: UsageEventInsert[] = [];
  for (let i = 0; i < events.length; i++) {
    const res = validateEvent(events[i]);
    if (!res.ok) {
      return { ok: false, status: 400, error: `event[${i}]: ${res.error}` };
    }
    out.push(res.value);
  }
  return { ok: true, events: out };
}
