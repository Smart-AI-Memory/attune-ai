'use client';

import { useEffect, useRef, type ReactNode } from 'react';
import { mountGuide, type GuideData } from '@/lib/harness-help/guide-interactions';

/** Add local interactions to server-rendered, source-controlled help content. */
export default function GuideControls({ data, children }: { data: GuideData; children: ReactNode }) {
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (root.current) return mountGuide(root.current, data);
  }, [data]);
  return <div ref={root}>{children}</div>;
}
