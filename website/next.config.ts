import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // standalone is for self-hosted deploys (Railway). On Vercel it must
  // be off: Next 16's Turbopack build routes trace output into the
  // standalone bundle, and Vercel's onBuildComplete then fails with
  // ENOENT on .next/next-server.js.nft.json.
  ...(process.env.VERCEL ? {} : { output: 'standalone' as const }),
  outputFileTracingRoot: path.join(__dirname, './'),
  trailingSlash: true,  // Force trailing slashes for MkDocs compatibility
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-XSS-Protection', value: '1; mode=block' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(self), geolocation=()' },
          { key: 'Content-Security-Policy', value: "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https:; frame-ancestors 'none'" },
        ],
      },
    ];
  },
  async rewrites() {
    return [
      // Serve index.html for framework-docs directory paths
      {
        source: '/framework-docs/:path*/',
        destination: '/framework-docs/:path*/index.html',
      },
    ];
  },
  async redirects() {
    return [
      { source: '/workflows/', destination: '/docs/#workflows', permanent: true },
      { source: '/wizards/', destination: '/docs/#workflows', permanent: true },
      { source: '/wizards/:name/', destination: '/docs/#workflows', permanent: true },
      { source: '/attune-lite/', destination: '/docs/#plugin', permanent: true },
      { source: '/attune-plugin/', destination: '/docs/#plugin', permanent: true },
      { source: '/compare/', destination: '/', permanent: true },
      { source: '/compare/:slug/', destination: '/', permanent: true },
      { source: '/tools/', destination: '/docs/', permanent: true },
      { source: '/tools/:path*/', destination: '/docs/', permanent: true },
      { source: '/demo/', destination: '/docs/', permanent: true },
      { source: '/demo/:path*/', destination: '/docs/', permanent: true },
      { source: '/framework/', destination: '/docs/#quickstart', permanent: true },
      { source: '/book/', destination: '/docs/', permanent: true },
      { source: '/chapter-23/', destination: '/docs/', permanent: true },
      { source: '/plugins/', destination: '/docs/#plugin', permanent: true },
      // The Discipline of Agent Collaboration — canonical home is
      // attune-ai.dev/discipline (built from the same master file in
      // attune-ai-dev/). Served natively here too since v5 — see
      // app/discipline/page.tsx (rel=canonical points at attune-ai.dev).
    ];
  },
};

export default nextConfig;
