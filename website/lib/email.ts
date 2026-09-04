import { Resend, type CreateEmailOptions } from 'resend';

// Lazy initialization
let resend: Resend | null = null;

function getResend(): Resend {
  if (!resend) {
    if (!process.env.RESEND_API_KEY) {
      throw new Error('RESEND_API_KEY is not configured');
    }
    resend = new Resend(process.env.RESEND_API_KEY);
  }
  return resend;
}

const FROM_EMAIL = process.env.FROM_EMAIL || 'Attune AI <noreply@smartaimemory.com>';
const SUPPORT_EMAIL = process.env.SUPPORT_EMAIL || 'admin@smartaimemory.com';

interface EmailResult {
  success: boolean;
  id?: string;
  error?: string;
}

export interface EmailOptions {
  to: string | string[];
  from?: string;
  subject: string;
  text?: string;
  html?: string;
  replyTo?: string;
}

/**
 * Send one email through Resend. Fails closed and never throws: no
 * API key, no body, or an API-level error all return `false` (and log),
 * so callers can treat the boolean as "delivered to Resend".
 *
 * Resend reports API failures through `error` on the result rather than
 * by throwing — check it, or a rejected send reads as success.
 */
export async function sendEmail(options: EmailOptions): Promise<boolean> {
  if (!process.env.RESEND_API_KEY) {
    console.error('RESEND_API_KEY is not set in environment variables');
    return false;
  }
  if (!options.text && !options.html) {
    console.error('Either text or html content must be provided');
    return false;
  }

  const base = {
    from: options.from || FROM_EMAIL,
    to: options.to,
    subject: options.subject,
    ...(options.replyTo ? { replyTo: options.replyTo } : {}),
  };
  // Resend's CreateEmailOptions is a union that needs a definite `html`
  // or `text`; pick the branch explicitly so the type is exact.
  const payload: CreateEmailOptions = options.html
    ? { ...base, html: options.html, ...(options.text ? { text: options.text } : {}) }
    : { ...base, text: options.text as string };

  try {
    const { data, error } = await getResend().emails.send(payload);
    if (error) {
      console.error('Resend error:', error);
      return false;
    }
    console.log('Email sent via Resend:', { to: options.to, subject: options.subject, id: data?.id });
    return true;
  } catch (error) {
    console.error('Resend error:', error);
    return false;
  }
}

export async function sendContactFormEmail(data: {
  name: string;
  email: string;
  company?: string;
  topic: string;
  message: string;
}): Promise<boolean> {
  const { name, email, company, topic, message } = data;

  const html = `
    <h2>New Contact Form Submission</h2>
    <p><strong>Name:</strong> ${name}</p>
    <p><strong>Email:</strong> ${email}</p>
    <p><strong>Company:</strong> ${company || 'Not provided'}</p>
    <p><strong>Topic:</strong> ${topic}</p>
    <p><strong>Message:</strong></p>
    <p>${message.replace(/\n/g, '<br>')}</p>
    <hr>
    <p><small>Sent from smartaimemory.com contact form</small></p>
  `;

  const text = `
New Contact Form Submission

Name: ${name}
Email: ${email}
Company: ${company || 'Not provided'}
Topic: ${topic}

Message:
${message}

---
Sent from smartaimemory.com contact form
  `;

  return sendEmail({
    to: process.env.CONTACT_EMAIL || 'patrick.roebuck@smartaimemory.com',
    subject: `[Smart AI Memory] Contact: ${topic} - ${name}`,
    text,
    html,
    replyTo: email,
  });
}

export async function sendNewsletterConfirmation(email: string): Promise<boolean> {
  const html = `
    <h2>Welcome to Smart AI Memory Newsletter!</h2>
    <p>Thank you for subscribing to our newsletter.</p>
    <p>You'll receive updates about:</p>
    <ul>
      <li>New Attune AI releases and features</li>
      <li>AI development insights and best practices</li>
      <li>Community highlights and use cases</li>
      <li>Exclusive content and early access</li>
    </ul>
    <p>You can unsubscribe at any time by clicking the link at the bottom of our emails.</p>
    <hr>
    <p><small>Smart AI Memory - Building the Future of AI-Human Collaboration</small></p>
  `;

  const text = `
Welcome to Smart AI Memory Newsletter!

Thank you for subscribing to our newsletter.

You'll receive updates about:
- New Attune AI releases and features
- AI development insights and best practices
- Community highlights and use cases
- Exclusive content and early access

You can unsubscribe at any time by clicking the link at the bottom of our emails.

---
Smart AI Memory - Building the Future of AI-Human Collaboration
  `;

  return sendEmail({
    to: email,
    subject: 'Welcome to Smart AI Memory Newsletter',
    text,
    html,
  });
}

// Send purchase confirmation with license key
export async function sendLicenseEmail(data: {
  to: string;
  customerName?: string;
  licenseKey: string;
  productName: string;
  expiresAt: Date;
  amountPaid: number;
}): Promise<EmailResult> {
  try {
    const result = await getResend().emails.send({
      from: FROM_EMAIL,
      to: data.to,
      subject: `Your Attune AI License - ${data.productName}`,
      html: `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }
    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
    .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }
    .content { background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; border-top: none; }
    .license-box { background: white; border: 2px dashed #667eea; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px; }
    .license-key { font-family: monospace; font-size: 18px; font-weight: bold; color: #667eea; letter-spacing: 1px; }
    .button { display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 10px 0; }
    .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 14px; }
    .details { background: white; padding: 15px; border-radius: 6px; margin: 15px 0; }
    .details-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f3f4f6; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Thank You for Your Purchase!</h1>
      <p>Your Attune AI license is ready</p>
    </div>
    <div class="content">
      <p>Hi${data.customerName ? ` ${data.customerName}` : ''},</p>
      <p>Thank you for purchasing <strong>${data.productName}</strong>. Your license key is below:</p>

      <div class="license-box">
        <p style="margin: 0 0 10px 0; color: #6b7280;">Your License Key</p>
        <div class="license-key">${data.licenseKey}</div>
      </div>

      <div class="details">
        <div class="details-row">
          <span>Product:</span>
          <strong>${data.productName}</strong>
        </div>
        <div class="details-row">
          <span>Amount Paid:</span>
          <strong>$${(data.amountPaid / 100).toFixed(2)}</strong>
        </div>
        <div class="details-row">
          <span>Valid Until:</span>
          <strong>${data.expiresAt.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</strong>
        </div>
      </div>

      <h3>Getting Started</h3>
      <ol>
        <li>Install Attune: <code>pip install attune-ai</code></li>
        <li>Set your license key as an environment variable: <code>ATTUNE_LICENSE_KEY=${data.licenseKey}</code></li>
        <li>Check out our <a href="https://smartaimemory.com/docs">documentation</a> to get started</li>
      </ol>

      <p style="text-align: center; margin-top: 30px;">
        <a href="https://smartaimemory.com/docs" class="button">View Documentation</a>
      </p>

      <p>If you have any questions, reply to this email or contact us at <a href="mailto:${SUPPORT_EMAIL}">${SUPPORT_EMAIL}</a>.</p>
    </div>
    <div class="footer">
      <p>&copy; ${new Date().getFullYear()} Smart AI Memory. All rights reserved.</p>
      <p><a href="https://smartaimemory.com">smartaimemory.com</a></p>
    </div>
  </div>
</body>
</html>
      `,
    });

    if (result.error) {
      console.error('Failed to send license email:', result.error);
      return { success: false, error: result.error.message };
    }
    return { success: true, id: result.data?.id };
  } catch (error) {
    console.error('Failed to send license email:', error);
    return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
  }
}

// Send book purchase confirmation with download links
export async function sendBookEmail(data: {
  to: string;
  customerName?: string;
  licenseKey: string;
  downloadToken: string;
  expiresAt: Date;
  amountPaid: number;
}): Promise<EmailResult> {
  const downloadBaseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://smartaimemory.com';

  try {
    const result = await getResend().emails.send({
      from: FROM_EMAIL,
      to: data.to,
      subject: 'Your Attune AI Book - Download Ready!',
      html: `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }
    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
    .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }
    .content { background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; border-top: none; }
    .download-box { background: white; border: 1px solid #e5e7eb; padding: 20px; margin: 20px 0; border-radius: 8px; }
    .download-button { display: inline-block; background: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; margin: 5px; }
    .license-box { background: #f0f9ff; border: 1px solid #bae6fd; padding: 15px; border-radius: 6px; margin: 15px 0; }
    .license-key { font-family: monospace; font-size: 14px; color: #0369a1; }
    .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 14px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Your Book is Ready!</h1>
      <p>Multi-Agent Coordination with Persistent and Short-Term Memory</p>
    </div>
    <div class="content">
      <p>Hi${data.customerName ? ` ${data.customerName}` : ''},</p>
      <p>Thank you for purchasing <strong>Attune AI</strong>! Your download links are ready.</p>

      <div class="download-box">
        <h3 style="margin-top: 0;">Download Your Book</h3>
        <p>Click any format below to download:</p>
        <p>
          <a href="${downloadBaseUrl}/api/download?token=${data.downloadToken}&format=pdf" class="download-button">PDF</a>
          <a href="${downloadBaseUrl}/api/download?token=${data.downloadToken}&format=epub" class="download-button">ePub</a>
          <a href="${downloadBaseUrl}/api/download?token=${data.downloadToken}&format=mobi" class="download-button">Mobi</a>
        </p>
        <p style="font-size: 12px; color: #6b7280;">Download links expire in 30 days. You can download up to 10 times.</p>
      </div>

      <div class="license-box">
        <h4 style="margin: 0 0 10px 0;">Your Developer License (1 Year Included)</h4>
        <p style="margin: 0;">License Key: <span class="license-key">${data.licenseKey}</span></p>
        <p style="margin: 10px 0 0 0; font-size: 12px;">Valid until: ${data.expiresAt.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</p>
      </div>

      <h3>What's Included</h3>
      <ul>
        <li>Complete book in PDF, ePub, and Mobi formats</li>
        <li>Access to Software Development Plugin</li>
        <li>Access to Healthcare Plugin</li>
        <li>All future updates to this edition</li>
      </ul>

      <p>If you have any questions, contact us at <a href="mailto:${SUPPORT_EMAIL}">${SUPPORT_EMAIL}</a>.</p>
    </div>
    <div class="footer">
      <p>&copy; ${new Date().getFullYear()} Smart AI Memory. All rights reserved.</p>
      <p><a href="https://smartaimemory.com">smartaimemory.com</a></p>
    </div>
  </div>
</body>
</html>
      `,
    });

    if (result.error) {
      console.error('Failed to send book email:', result.error);
      return { success: false, error: result.error.message };
    }
    return { success: true, id: result.data?.id };
  } catch (error) {
    console.error('Failed to send book email:', error);
    return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
  }
}

// Send contribution thank you email
export async function sendContributionEmail(data: {
  to: string;
  customerName?: string;
  amountPaid: number;
}): Promise<EmailResult> {
  try {
    const result = await getResend().emails.send({
      from: FROM_EMAIL,
      to: data.to,
      subject: 'Thank You for Supporting Attune AI!',
      html: `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }
    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
    .header { background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }
    .content { background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; border-top: none; }
    .amount { font-size: 36px; font-weight: bold; color: #10b981; }
    .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 14px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Thank You!</h1>
      <p>Your contribution helps us build the future of AI development</p>
    </div>
    <div class="content">
      <p>Hi${data.customerName ? ` ${data.customerName}` : ''},</p>

      <p style="text-align: center;">
        <span class="amount">$${(data.amountPaid / 100).toFixed(2)}</span>
        <br>
        <span style="color: #6b7280;">Contribution received</span>
      </p>

      <p>Your generous contribution directly supports:</p>
      <ul>
        <li>Continued development of Attune AI</li>
        <li>Free access for students and educators</li>
        <li>Open-source community resources</li>
        <li>New wizard development and features</li>
      </ul>

      <p>As a contributor, you're helping make anticipatory AI accessible to developers everywhere. We truly appreciate your support!</p>

      <p>Follow our progress:</p>
      <ul>
        <li><a href="https://github.com/Smart-AI-Memory/attune-ai">GitHub Repository</a></li>
        <li><a href="https://smartaimemory.com/docs">Documentation</a></li>
      </ul>

      <p>Questions? Contact us at <a href="mailto:${SUPPORT_EMAIL}">${SUPPORT_EMAIL}</a>.</p>
    </div>
    <div class="footer">
      <p>&copy; ${new Date().getFullYear()} Smart AI Memory. All rights reserved.</p>
      <p><a href="https://smartaimemory.com">smartaimemory.com</a></p>
    </div>
  </div>
</body>
</html>
      `,
    });

    if (result.error) {
      console.error('Failed to send contribution email:', result.error);
      return { success: false, error: result.error.message };
    }
    return { success: true, id: result.data?.id };
  } catch (error) {
    console.error('Failed to send contribution email:', error);
    return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
  }
}
