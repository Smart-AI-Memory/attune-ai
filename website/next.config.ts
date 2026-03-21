import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  output: 'standalone',
  outputFileTracingRoot: path.join(__dirname, './'),
  trailingSlash: true,  // Force trailing slashes for MkDocs compatibility
  eslint: {
    // Only run ESLint on these directories during production builds
    dirs: ['app'],
    // Ignore ESLint errors during production builds
    ignoreDuringBuilds: true,
  },
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
};

export default nextConfig;
