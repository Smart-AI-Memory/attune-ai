import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock the Resend SDK at the module boundary; the composition logic under
// test is ours, the transport is theirs.
const send = vi.fn();
vi.mock('resend', () => ({
  // `new Resend(key)` — must be constructible, so a class, not an arrow fn.
  Resend: class {
    emails = { send };
  },
}));

import { sendEmail, sendContactFormEmail, sendNewsletterConfirmation } from '@/lib/email';

beforeEach(() => {
  vi.unstubAllEnvs();
  vi.stubEnv('RESEND_API_KEY', 're_test');
  send.mockReset();
  send.mockResolvedValue({ data: { id: 'msg_1' }, error: null });
});

describe('sendEmail (Resend)', () => {
  it('fails closed without RESEND_API_KEY and never calls the SDK', async () => {
    vi.stubEnv('RESEND_API_KEY', '');
    expect(await sendEmail({ to: 'a@example.com', subject: 's', text: 't' })).toBe(false);
    expect(send).not.toHaveBeenCalled();
  });

  it('refuses a body-less message', async () => {
    expect(await sendEmail({ to: 'a@example.com', subject: 's' })).toBe(false);
    expect(send).not.toHaveBeenCalled();
  });

  it('sends with the default from-address and passes replyTo through', async () => {
    const ok = await sendEmail({
      to: 'a@example.com',
      subject: 'Hello',
      text: 'plain',
      html: '<p>rich</p>',
      replyTo: 'visitor@example.com',
    });
    expect(ok).toBe(true);
    expect(send).toHaveBeenCalledOnce();
    const arg = send.mock.calls[0][0];
    expect(arg.from).toBe('Attune AI <noreply@smartaimemory.com>');
    expect(arg.to).toBe('a@example.com');
    expect(arg.subject).toBe('Hello');
    expect(arg.text).toBe('plain');
    expect(arg.html).toBe('<p>rich</p>');
    expect(arg.replyTo).toBe('visitor@example.com');
  });

  it('treats an API-level error as failure (Resend does not throw)', async () => {
    send.mockResolvedValue({ data: null, error: { name: 'validation_error', message: 'bad from' } });
    expect(await sendEmail({ to: 'a@example.com', subject: 's', text: 't' })).toBe(false);
  });

  it('treats a thrown transport error as failure', async () => {
    send.mockRejectedValue(new Error('network'));
    expect(await sendEmail({ to: 'a@example.com', subject: 's', text: 't' })).toBe(false);
  });
});

describe('composed mails', () => {
  it('contact form goes to CONTACT_EMAIL with the visitor as replyTo', async () => {
    vi.stubEnv('CONTACT_EMAIL', 'inbox@example.com');
    const ok = await sendContactFormEmail({
      name: 'Ada',
      email: 'ada@example.com',
      topic: 'Support',
      message: 'line one\nline two',
    });
    expect(ok).toBe(true);
    const arg = send.mock.calls[0][0];
    expect(arg.to).toBe('inbox@example.com');
    expect(arg.replyTo).toBe('ada@example.com');
    expect(arg.subject).toBe('[Smart AI Memory] Contact: Support - Ada');
    expect(arg.html).toContain('line one<br>line two');
    expect(arg.text).toContain('line one\nline two');
  });

  it('newsletter confirmation goes to the subscriber', async () => {
    expect(await sendNewsletterConfirmation('new@example.com')).toBe(true);
    const arg = send.mock.calls[0][0];
    expect(arg.to).toBe('new@example.com');
    expect(arg.subject).toBe('Welcome to Smart AI Memory Newsletter');
    expect(arg.replyTo).toBeUndefined();
  });
});
