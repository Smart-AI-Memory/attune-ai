'use client';

import { useState } from 'react';

interface VideoEmbedProps {
  /** YouTube video ID (the 11-char ID, not the full URL). */
  videoId: string;
  /** Accessible title for the video (also the iframe title). */
  title: string;
  /** Optional poster image; defaults to the YouTube thumbnail. */
  poster?: string;
}

/**
 * Privacy-friendly YouTube facade: renders only a poster image and
 * play button until clicked, then swaps in a youtube-nocookie iframe.
 * No third-party JS or cookies load before the user opts in, and the
 * fixed aspect ratio means no layout shift when the player mounts.
 */
export default function VideoEmbed({ videoId, title, poster }: VideoEmbedProps) {
  const [playing, setPlaying] = useState(false);
  const posterSrc = poster || `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;

  return (
    <div className="relative aspect-video overflow-hidden rounded-lg border border-[var(--border)] bg-black">
      {playing ? (
        <iframe
          src={`https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1&rel=0`}
          title={title}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          className="absolute inset-0 h-full w-full"
        />
      ) : (
        <button
          type="button"
          onClick={() => setPlaying(true)}
          aria-label={`Play video: ${title}`}
          className="group absolute inset-0 h-full w-full cursor-pointer"
        >
          {/* eslint-disable-next-line @next/next/no-img-element -- remote YouTube thumbnail; avoids adding i.ytimg.com to next/image remotePatterns */}
          <img
            src={posterSrc}
            alt={title}
            loading="lazy"
            className="absolute inset-0 h-full w-full object-cover"
          />
          <span className="absolute inset-0 flex items-center justify-center">
            <span className="flex h-16 w-16 items-center justify-center rounded-full bg-black/70 transition-colors group-hover:bg-[var(--primary)]">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="white"
                aria-hidden="true"
              >
                <path d="M8 5v14l11-7z" />
              </svg>
            </span>
          </span>
        </button>
      )}
    </div>
  );
}
