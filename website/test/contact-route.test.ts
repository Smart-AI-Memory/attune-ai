import { NextRequest } from 'next/server';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { POST } from '@/app/api/contact/route';
import { createContact } from '@/lib/db';
import { sendContactFormEmail } from '@/lib/email';

vi.mock('@/lib/db', () => ({ createContact: vi.fn() }));
vi.mock('@/lib/email', () => ({ sendContactFormEmail: vi.fn() }));

const submission = {
  name: 'Example Visitor',
  email: 'visitor@example.com',
  company: 'Example Company',
  topic: 'general',
  message: 'Can you help me get started?',
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(console, 'log').mockImplementation(() => {});
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('POST /api/contact', () => {
  it.each([
    { stored: true, emailSent: true, status: 200 },
    { stored: true, emailSent: false, status: 200 },
    { stored: false, emailSent: true, status: 200 },
    { stored: false, emailSent: false, status: 503 },
  ])('returns $status when stored=$stored and emailSent=$emailSent', async ({
    stored,
    emailSent,
    status,
  }) => {
    if (stored) {
      vi.mocked(createContact).mockResolvedValueOnce({
        ...submission,
        id: 1,
        status: 'new',
        submitted_at: new Date(),
        replied_at: null,
        notes: null,
        metadata: null,
      });
    } else {
      vi.mocked(createContact).mockRejectedValueOnce(new Error('Storage unavailable'));
    }
    vi.mocked(sendContactFormEmail).mockResolvedValueOnce(emailSent);

    const response = await POST(new NextRequest('http://localhost/api/contact', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(submission),
    }));

    expect(createContact).toHaveBeenCalledExactlyOnceWith(expect.objectContaining(submission));
    expect(sendContactFormEmail).toHaveBeenCalledExactlyOnceWith(submission);
    expect(response.status).toBe(status);
    expect(await response.json()).toMatchObject({ success: status === 200, emailSent });
  });
});
