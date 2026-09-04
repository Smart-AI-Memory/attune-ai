import { NextRequest, NextResponse } from 'next/server';
import { sendContactFormEmail } from '@/lib/email';
import { createContact } from '@/lib/db';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { name, email, company, topic, message } = body;

    // Validate required fields
    if (!name || !email || !topic || !message) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      );
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return NextResponse.json(
        { error: 'Invalid email format' },
        { status: 400 }
      );
    }

    // Log submission
    console.log('Contact form submission:', {
      name,
      email,
      company,
      topic,
      message,
      timestamp: new Date().toISOString(),
    });

    // Store in database
    let dbSuccess = false;
    let contactId: number | null = null;
    try {
      const contact = await createContact({
        name,
        email,
        company,
        topic,
        message,
        metadata: {
          userAgent: request.headers.get('user-agent'),
          ip: request.headers.get('x-forwarded-for') || request.headers.get('x-real-ip'),
        },
      });
      dbSuccess = true;
      contactId = contact.id;
      console.log('Contact saved to database:', contact.id);
    } catch (dbError) {
      console.error('Database error (continuing anyway):', dbError);
    }

    // Send email via Resend
    const emailSent = await sendContactFormEmail({
      name,
      email,
      company,
      topic,
      message,
    });

    if (!emailSent) {
      // The visitor still gets a 200 (their submission is stored); the
      // maintainer must be able to see the miss — at error level, and
      // in the body so a production probe can read it.
      console.error('contact form email NOT sent', { contactId, resendKeyPresent: Boolean(process.env.RESEND_API_KEY) });
    }

    // Log summary
    console.log('Contact form complete:', {
      contactId,
      database: dbSuccess,
      emailNotification: emailSent,
    });

    return NextResponse.json(
      {
        success: true,
        message: 'Thank you! We will get back to you within 24-48 hours.',
        emailSent,
      },
      { status: 200 }
    );
  } catch (error) {
    console.error('Contact form error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

// Handle OPTIONS for CORS — restrict to same-origin
export async function OPTIONS(request: NextRequest) {
  const origin = request.headers.get('origin') || '';
  const allowedOrigins = [
    'https://smartaimemory.com',
    'https://www.smartaimemory.com',
    ...(process.env.NODE_ENV === 'development' ? ['http://localhost:3000'] : []),
  ];
  const corsOrigin = allowedOrigins.includes(origin) ? origin : allowedOrigins[0];

  return new NextResponse(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': corsOrigin,
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}
