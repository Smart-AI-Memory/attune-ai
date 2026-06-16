import { describe, it, expect } from 'vitest';
import {
  validateEvent,
  validateBatch,
  ALLOWED_KEYS,
  MAX_EVENTS_PER_REQUEST,
} from '../lib/usage/validate';

// A minimal valid schema-v1 client payload.
function validEvent(over: Record<string, unknown> = {}) {
  return {
    schema: 1,
    package: 'attune-ai',
    version: '8.5.0',
    install_id: '11111111-2222-4333-8444-555555555555',
    event: 'workflow.security_audit',
    os: 'darwin',
    py: '3.12',
    ts: '2026-06-16T12:00:00Z',
    ...over,
  };
}

describe('validateEvent — happy path', () => {
  it('accepts a well-formed event and maps ts -> client_ts', () => {
    const res = validateEvent(validEvent());
    expect(res.ok).toBe(true);
    if (res.ok) {
      expect(res.value).toEqual({
        package: 'attune-ai',
        version: '8.5.0',
        install_id: '11111111-2222-4333-8444-555555555555',
        event: 'workflow.security_audit',
        os: 'darwin',
        py: '3.12',
        client_ts: '2026-06-16T12:00:00.000Z',
      });
      // schema is a version gate, never stored.
      expect('schema' in res.value).toBe(false);
      expect('ts' in res.value).toBe(false);
    }
  });

  it('allows os/py to be null', () => {
    const res = validateEvent(validEvent({ os: null, py: null }));
    expect(res.ok).toBe(true);
    if (res.ok) {
      expect(res.value.os).toBeNull();
      expect(res.value.py).toBeNull();
    }
  });

  it('null/empty ts becomes null client_ts', () => {
    expect((validateEvent(validEvent({ ts: '' })) as { value: { client_ts: unknown } }).value.client_ts).toBeNull();
  });
});

describe('validateEvent — frozen-payload defense', () => {
  it('rejects an unknown field (free-text creep)', () => {
    const res = validateEvent(validEvent({ prompt: 'rm -rf /' }));
    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.error).toMatch(/unknown field: prompt/);
  });

  it('rejects forbidden telemetry fields that must never leave the client', () => {
    for (const field of ['cost', 'tokens', 'model', 'user_id', 'path']) {
      const res = validateEvent(validEvent({ [field]: 'x' }));
      expect(res.ok).toBe(false);
    }
  });

  it('ALLOWED_KEYS is exactly the schema-v1 set', () => {
    expect([...ALLOWED_KEYS].sort()).toEqual(
      ['event', 'install_id', 'os', 'package', 'py', 'schema', 'ts', 'version'].sort()
    );
  });
});

describe('validateEvent — field validation', () => {
  it('rejects a wrong schema version', () => {
    expect(validateEvent(validEvent({ schema: 2 })).ok).toBe(false);
    expect(validateEvent(validEvent({ schema: undefined })).ok).toBe(false);
  });

  it('rejects a non-UUID install_id', () => {
    expect(validateEvent(validEvent({ install_id: 'not-a-uuid' })).ok).toBe(false);
    expect(validateEvent(validEvent({ install_id: 123 })).ok).toBe(false);
  });

  it('rejects an event outside the workflow.<name> grammar', () => {
    expect(validateEvent(validEvent({ event: 'security_audit' })).ok).toBe(false); // no prefix
    expect(validateEvent(validEvent({ event: 'workflow.has space' })).ok).toBe(false);
    expect(validateEvent(validEvent({ event: 'skill.foo' })).ok).toBe(false); // reserved, not v1
  });

  it('rejects empty/oversized package and version', () => {
    expect(validateEvent(validEvent({ package: '' })).ok).toBe(false);
    expect(validateEvent(validEvent({ version: 'v'.repeat(64) })).ok).toBe(false);
  });

  it('rejects a non-object', () => {
    expect(validateEvent(null).ok).toBe(false);
    expect(validateEvent('nope').ok).toBe(false);
    expect(validateEvent([validEvent()]).ok).toBe(false);
  });
});

describe('validateBatch', () => {
  it('accepts a {events:[...]} batch', () => {
    const res = validateBatch({ events: [validEvent(), validEvent({ event: 'workflow.bug_predict' })] });
    expect(res.ok).toBe(true);
    if (res.ok) expect(res.events).toHaveLength(2);
  });

  it('rejects a non-batch body with 400', () => {
    expect(validateBatch({}).ok).toBe(false);
    expect((validateBatch({ events: 'x' } as unknown) as { status: number }).status).toBe(400);
  });

  it('rejects an empty events array with 400', () => {
    const res = validateBatch({ events: [] });
    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.status).toBe(400);
  });

  it('rejects too many events with 413', () => {
    const events = Array.from({ length: MAX_EVENTS_PER_REQUEST + 1 }, () => validEvent());
    const res = validateBatch({ events });
    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.status).toBe(413);
  });

  it('reports the index of the first bad event', () => {
    const res = validateBatch({ events: [validEvent(), validEvent({ install_id: 'bad' })] });
    expect(res.ok).toBe(false);
    if (!res.ok) {
      expect(res.status).toBe(400);
      expect(res.error).toMatch(/event\[1\]/);
    }
  });
});
