import { ImageResponse } from 'next/og';
import { NextRequest } from 'next/server';

export const runtime = 'edge';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);

    // Get parameters from query string
    const title = searchParams.get('title') || 'Smart AI Memory';
    const subtitle = searchParams.get('subtitle') || 'Delegate with clear scope. Keep the evidence.';

    return new ImageResponse(
      (
        <div
          style={{
            fontSize: 60,
            background: 'linear-gradient(135deg, #285e42 0%, #263c30 100%)',
            width: '100%',
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontFamily: 'sans-serif',
            padding: '80px',
          }}
        >
          <div style={{ fontSize: 80, fontWeight: 'bold', marginBottom: 20, textAlign: 'center' }}>
            {title}
          </div>
          <div style={{ fontSize: 36, textAlign: 'center', opacity: 0.9 }}>
            {subtitle}
          </div>
        </div>
      ),
      {
        width: 1200,
        height: 630,
      }
    );
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : 'Unknown error';
    console.log(message);
    return new Response(`Failed to generate the image`, {
      status: 500,
    });
  }
}
