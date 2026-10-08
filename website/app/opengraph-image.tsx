import { ImageResponse } from 'next/og';

// Image metadata
export const alt = 'Smart AI Memory - Delegate with clear scope. Keep the evidence.';
export const size = {
  width: 1200,
  height: 630,
};

export const contentType = 'image/png';

// Image generation
export default async function Image() {
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
        <div style={{ fontSize: 80, fontWeight: 'bold', marginBottom: 20 }}>
          Smart AI Memory
        </div>
        <div style={{ fontSize: 36, textAlign: 'center', opacity: 0.9 }}>
          Delegate with clear scope. Keep the evidence.
        </div>
      </div>
    ),
    {
      ...size,
    }
  );
}
