import type { Metadata } from "next";
import "./globals.css";
import "../public/portfolio-theme.css";
import { ThemeProvider } from "@/lib/theme-provider";
import { generateMetadata, generateStructuredData } from "@/lib/metadata";
import PlausibleAnalytics from "@/components/PlausibleAnalytics";
import WebVitals from "@/components/WebVitals";
import { SpeedInsights } from "@vercel/speed-insights/next";
import { Analytics } from "@vercel/analytics/next";

export const metadata: Metadata = generateMetadata();

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const organizationSchema = generateStructuredData('organization');
  const websiteSchema = generateStructuredData('website');

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Structured Data */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify([organizationSchema, websiteSchema]),
          }}
        />
        <PlausibleAnalytics />
      </head>
      <body
        className="antialiased"
      >
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[100] focus:bg-[var(--primary)] focus:text-white focus:px-4 focus:py-2 focus:rounded-lg focus:outline-none"
        >
          Skip to main content
        </a>
        <ThemeProvider>
          <WebVitals />
          <SpeedInsights />
          <Analytics />
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
