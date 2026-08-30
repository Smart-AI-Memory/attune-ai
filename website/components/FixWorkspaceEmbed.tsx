'use client';

import { useEffect, useRef, useState } from 'react';

const MIN_HEIGHT = 760;
const MAX_HEIGHT = 2400;

export default function FixWorkspaceEmbed() {
  const frame = useRef<HTMLIFrameElement>(null);
  const [height, setHeight] = useState(1180);

  useEffect(() => {
    const receiveHeight = (event: MessageEvent) => {
      if (
        event.origin !== window.location.origin ||
        event.source !== frame.current?.contentWindow ||
        event.data?.type !== 'attune-fix-demo-height' ||
        typeof event.data.height !== 'number'
      ) {
        return;
      }
      setHeight(Math.min(MAX_HEIGHT, Math.max(MIN_HEIGHT, Math.ceil(event.data.height))));
    };
    window.addEventListener('message', receiveHeight);
    return () => window.removeEventListener('message', receiveHeight);
  }, []);

  return (
    <iframe
      ref={frame}
      src="/fix-workspace-demo/index.html"
      title="Interactive, non-executing attune-ai Fix approval workspace"
      className="w-full border-0 bg-[var(--background)]"
      style={{ height }}
      sandbox="allow-scripts allow-same-origin allow-modals"
    />
  );
}
