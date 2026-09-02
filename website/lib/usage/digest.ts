/**
 * Daily usage digest (reporting layer over the Phase 2b opt-in ping).
 *
 * Answers one question for the maintainer: *did anyone run attune-ai
 * yesterday, and what did they run?* It reads only the `usage_events`
 * table, which is anonymous by construction — a rotating, user-resettable
 * `install_id` and a registry-sourced `workflow.<name>` event, with no IP,
 * no headers, and no PII (see `lib/usage/validate.ts` and the frozen
 * payload in docs/specs/usage-signals/phase2-design.md).
 *
 * This module therefore **cannot** tell you who a user is, and must never
 * be extended to try. Identity belongs to a separate, consented channel
 * (newsletter / contact), never to the anonymous ping.
 *
 * `collectUsageDigest` does the reads; `renderUsageDigest` is pure so the
 * email body is testable without a database.
 *
 * Copyright 2026 Smart-AI-Memory
 * Licensed under Apache 2.0
 */

import { query } from '@/lib/db';

/** One `(label, count)` row in a breakdown table. */
export interface DigestBreakdownRow {
  label: string;
  events: number;
  installs: number;
}

/** Everything the email needs. Serializable — no Date objects. */
export interface UsageDigest {
  /** ISO timestamps bounding the reported window. */
  windowStart: string;
  windowEnd: string;
  /** Events received in the window. */
  events: number;
  /** Distinct install_ids seen in the window. */
  activeInstalls: number;
  /** Install_ids whose FIRST-EVER event landed in the window. */
  newInstalls: number;
  /** The same two figures for the preceding 24h, for a delta. */
  prevEvents: number;
  prevActiveInstalls: number;
  /** Top workflows in the window, most-run first. */
  topWorkflows: DigestBreakdownRow[];
  /** Environment mix in the window. */
  osMix: DigestBreakdownRow[];
  pyMix: DigestBreakdownRow[];
  versionMix: DigestBreakdownRow[];
  /** Lifetime totals, for context under the daily numbers. */
  totalEvents: number;
  totalInstalls: number;
}

interface CountRow {
  label: string | null;
  events: string | number;
  installs: string | number;
}

/** pg returns bigint aggregates as strings; normalise to a number. */
function num(v: unknown): number {
  const n = typeof v === 'number' ? v : Number(v ?? 0);
  return Number.isFinite(n) ? n : 0;
}

function toRows(rows: CountRow[], fallback = 'unknown'): DigestBreakdownRow[] {
  return rows.map((r) => ({
    label: r.label ?? fallback,
    events: num(r.events),
    installs: num(r.installs),
  }));
}

/**
 * Read the last 24h of usage (and the 24h before it, for a delta).
 *
 * `now` is injectable so tests and backfills can pin the window.
 */
export async function collectUsageDigest(now: Date = new Date()): Promise<UsageDigest> {
  const windowEnd = now;
  const windowStart = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  const prevStart = new Date(now.getTime() - 48 * 60 * 60 * 1000);

  const startIso = windowStart.toISOString();
  const endIso = windowEnd.toISOString();
  const prevIso = prevStart.toISOString();

  // 1. Window totals + the preceding window, in one pass.
  const totals = await query<{
    events: string;
    installs: string;
    prev_events: string;
    prev_installs: string;
  }>(
    `SELECT
       count(*) FILTER (WHERE received_at >= $1 AND received_at < $2)                    AS events,
       count(DISTINCT install_id) FILTER (WHERE received_at >= $1 AND received_at < $2)  AS installs,
       count(*) FILTER (WHERE received_at >= $3 AND received_at < $1)                    AS prev_events,
       count(DISTINCT install_id) FILTER (WHERE received_at >= $3 AND received_at < $1)  AS prev_installs
     FROM usage_events`,
    [startIso, endIso, prevIso]
  );

  // 2. Installs whose first-ever event landed inside the window.
  const fresh = await query<{ count: string }>(
    `SELECT count(*) AS count FROM (
       SELECT install_id
       FROM usage_events
       GROUP BY install_id
       HAVING min(received_at) >= $1 AND min(received_at) < $2
     ) first_seen`,
    [startIso, endIso]
  );

  // 3. Breakdowns within the window.
  const breakdown = async (column: string, limit: number): Promise<DigestBreakdownRow[]> => {
    // `column` is never caller-supplied — only the literals below.
    const res = await query<CountRow>(
      `SELECT ${column} AS label,
              count(*) AS events,
              count(DISTINCT install_id) AS installs
       FROM usage_events
       WHERE received_at >= $1 AND received_at < $2
       GROUP BY ${column}
       ORDER BY count(*) DESC, label ASC
       LIMIT ${limit}`,
      [startIso, endIso]
    );
    return toRows(res.rows);
  };

  const [topWorkflows, osMix, pyMix, versionMix] = await Promise.all([
    breakdown('event', 10),
    breakdown('os', 6),
    breakdown('py', 6),
    breakdown('version', 6),
  ]);

  // 4. Lifetime context.
  const lifetime = await query<{ events: string; installs: string }>(
    `SELECT count(*) AS events, count(DISTINCT install_id) AS installs FROM usage_events`
  );

  const t = totals.rows[0];
  const l = lifetime.rows[0];

  return {
    windowStart: startIso,
    windowEnd: endIso,
    events: num(t?.events),
    activeInstalls: num(t?.installs),
    newInstalls: num(fresh.rows[0]?.count),
    prevEvents: num(t?.prev_events),
    prevActiveInstalls: num(t?.prev_installs),
    topWorkflows,
    osMix,
    pyMix,
    versionMix,
    totalEvents: num(l?.events),
    totalInstalls: num(l?.installs),
  };
}

/** A workflow event is stored as `workflow.<name>`; show the name. */
export function prettyWorkflow(event: string): string {
  return event.startsWith('workflow.') ? event.slice('workflow.'.length) : event;
}

/** `+3` / `-2` / `±0` against the previous window. */
export function formatDelta(current: number, previous: number): string {
  const d = current - previous;
  if (d === 0) return '±0';
  return d > 0 ? `+${d}` : `${d}`;
}

function utcDay(iso: string): string {
  return iso.slice(0, 10);
}

function esc(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** The rendered email: subject plus both bodies. */
export interface RenderedDigest {
  subject: string;
  html: string;
  text: string;
}

const INK = '#0b0b0b';
const INK2 = '#52514e';
const MUTED = '#898781';
const RULE = '#e1e0d9';
const ACCENT = '#2a78d6';

function htmlTable(title: string, rows: DigestBreakdownRow[], pretty = (s: string) => s): string {
  if (rows.length === 0) return '';
  const body = rows
    .map(
      (r) => `
        <tr>
          <td style="padding:6px 10px;border-bottom:1px solid ${RULE};color:${INK};font-size:14px;">${esc(pretty(r.label))}</td>
          <td style="padding:6px 10px;border-bottom:1px solid ${RULE};color:${INK};font-size:14px;text-align:right;">${r.events}</td>
          <td style="padding:6px 10px;border-bottom:1px solid ${RULE};color:${INK2};font-size:14px;text-align:right;">${r.installs}</td>
        </tr>`
    )
    .join('');
  return `
    <h3 style="font:600 14px system-ui,-apple-system,'Segoe UI',sans-serif;color:${INK};margin:26px 0 8px;">${esc(title)}</h3>
    <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;">
      <tr>
        <th align="left" style="padding:0 10px 6px;color:${MUTED};font:600 11px system-ui;text-transform:uppercase;letter-spacing:.05em;">Name</th>
        <th align="right" style="padding:0 10px 6px;color:${MUTED};font:600 11px system-ui;text-transform:uppercase;letter-spacing:.05em;">Runs</th>
        <th align="right" style="padding:0 10px 6px;color:${MUTED};font:600 11px system-ui;text-transform:uppercase;letter-spacing:.05em;">Installs</th>
      </tr>
      ${body}
    </table>`;
}

function textTable(title: string, rows: DigestBreakdownRow[], pretty = (s: string) => s): string {
  if (rows.length === 0) return '';
  const width = Math.max(...rows.map((r) => pretty(r.label).length), 4);
  const lines = rows.map(
    (r) => `  ${pretty(r.label).padEnd(width)}  ${String(r.events).padStart(5)} runs  ${String(r.installs).padStart(4)} installs`
  );
  return `\n${title}\n${lines.join('\n')}\n`;
}

function statCell(value: number | string, label: string, note: string): string {
  return `
    <td style="padding:14px 16px;border:1px solid ${RULE};border-radius:10px;vertical-align:top;">
      <div style="color:${MUTED};font:600 11px system-ui;text-transform:uppercase;letter-spacing:.06em;">${esc(label)}</div>
      <div style="color:${INK};font:650 26px system-ui;letter-spacing:-0.02em;padding-top:4px;">${esc(String(value))}</div>
      <div style="color:${INK2};font:400 12px system-ui;padding-top:3px;">${esc(note)}</div>
    </td>`;
}

/**
 * Render the digest. Pure — no I/O, no clock, no environment reads — so
 * the email body can be asserted in tests.
 */
export function renderUsageDigest(d: UsageDigest): RenderedDigest {
  const day = utcDay(d.windowStart);
  const subject =
    d.newInstalls > 0
      ? `attune-ai: ${d.newInstalls} new install${d.newInstalls === 1 ? '' : 's'}, ${d.events} run${d.events === 1 ? '' : 's'} (${day})`
      : `attune-ai: ${d.events} run${d.events === 1 ? '' : 's'} from ${d.activeInstalls} install${d.activeInstalls === 1 ? '' : 's'} (${day})`;

  const html = `<!DOCTYPE html>
<html><body style="margin:0;background:#f9f9f7;padding:24px;">
  <div style="max-width:620px;margin:0 auto;background:#fcfcfb;border:1px solid ${RULE};border-radius:12px;padding:26px;">
    <h1 style="font:650 20px system-ui,-apple-system,'Segoe UI',sans-serif;color:${INK};margin:0 0 4px;letter-spacing:-0.01em;">
      attune-ai usage — last 24 hours
    </h1>
    <p style="font:400 13px system-ui;color:${MUTED};margin:0 0 20px;">
      ${esc(d.windowStart.replace('T', ' ').slice(0, 16))} → ${esc(d.windowEnd.replace('T', ' ').slice(0, 16))} UTC
    </p>

    <table role="presentation" cellpadding="0" cellspacing="6" style="width:100%;border-collapse:separate;font-family:system-ui;">
      <tr>
        ${statCell(d.newInstalls, 'New installs', 'first seen in this window')}
        ${statCell(d.activeInstalls, 'Active installs', `${formatDelta(d.activeInstalls, d.prevActiveInstalls)} vs prior 24h`)}
        ${statCell(d.events, 'Workflow runs', `${formatDelta(d.events, d.prevEvents)} vs prior 24h`)}
      </tr>
    </table>

    ${htmlTable('Workflows run', d.topWorkflows, prettyWorkflow)}
    ${htmlTable('Operating system', d.osMix)}
    ${htmlTable('Python version', d.pyMix)}
    ${htmlTable('Package version', d.versionMix)}

    <p style="font:400 13px system-ui;color:${INK2};margin:26px 0 0;padding-top:16px;border-top:1px solid ${RULE};">
      Lifetime: <strong style="color:${INK};">${d.totalEvents}</strong> runs from
      <strong style="color:${INK};">${d.totalInstalls}</strong> distinct install IDs.
    </p>
    <p style="font:400 12px system-ui;color:${MUTED};margin:12px 0 0;">
      Counts come from the opt-in anonymous usage ping, which is OFF by default. An
      <code style="color:${ACCENT};">install_id</code> is a rotating UUID the user can reset — treat it as
      a lower bound on machines, not a user identity. Nothing here identifies anyone, by design.
    </p>
  </div>
</body></html>`;

  const text = [
    `attune-ai usage — last 24 hours`,
    `${d.windowStart.slice(0, 16).replace('T', ' ')} → ${d.windowEnd.slice(0, 16).replace('T', ' ')} UTC`,
    ``,
    `  New installs    ${d.newInstalls}  (first seen in this window)`,
    `  Active installs ${d.activeInstalls}  (${formatDelta(d.activeInstalls, d.prevActiveInstalls)} vs prior 24h)`,
    `  Workflow runs   ${d.events}  (${formatDelta(d.events, d.prevEvents)} vs prior 24h)`,
    textTable('Workflows run', d.topWorkflows, prettyWorkflow),
    textTable('Operating system', d.osMix),
    textTable('Python version', d.pyMix),
    textTable('Package version', d.versionMix),
    ``,
    `Lifetime: ${d.totalEvents} runs from ${d.totalInstalls} distinct install IDs.`,
    ``,
    `Counts come from the opt-in anonymous usage ping (OFF by default). install_id is a`,
    `rotating, user-resettable UUID — a lower bound on machines, not a user identity.`,
  ].join('\n');

  return { subject, html, text };
}
