import type { Metadata } from 'next';

export interface SEOConfig {
  title?: string;
  description?: string;
  keywords?: string[];
  image?: string;
  url?: string;
  type?: 'website' | 'article';
  publishedTime?: string;
  modifiedTime?: string;
  author?: string;
  section?: string;
}

const defaultMetadata = {
  siteName: 'Attune AI',
  title: 'Persistent memory and receipt-verified workflows for Claude Code — Attune AI',
  description:
    'Persistent memory and receipt-verified workflows for Claude Code: cross-session memory, acceptance probes re-run independently, RAG grounding, and spec-driven development — open source.',
  url: 'https://smartaimemory.com',
  image: '/og-image.png',
  twitterHandle: '@smartaimemory',
  keywords: [
    'help content generation',
    'developer documentation automation',
    'code-generated documentation',
    'progressive help templates',
    'living documentation',
    'attune-help',
    'attune-ai',
    'Claude Code plugin',
    'Claude Code memory',
    'persistent memory for Claude Code',
    'agent memory',
    'spec driven development Claude Code',
    'MCP server',
    'Claude Code /coach',
    'self-maintaining docs',
    'knowledge base from code',
    'open source documentation tool',
  ],
};

export function generateMetadata(config?: SEOConfig): Metadata {
  const title = config?.title
    ? `${config.title} | ${defaultMetadata.siteName}`
    : defaultMetadata.title;


  const description = config?.description || defaultMetadata.description;
  const image = config?.image || defaultMetadata.image;
  const url = config?.url || defaultMetadata.url;
  const keywords = config?.keywords || defaultMetadata.keywords;

  return {
    metadataBase: new URL(defaultMetadata.url),
    title,
    description,
    keywords,
    authors: [
      { name: 'Attune AI' },
      ...(config?.author ? [{ name: config.author }] : []),
    ],
    creator: 'Attune AI',
    publisher: 'Attune AI',
    formatDetection: {
      email: false,
      address: false,
      telephone: false,
    },
    openGraph: {
      type: config?.type || 'website',
      locale: 'en_US',
      url,
      title,
      description,
      siteName: 'Attune AI',
      images: [
        {
          url: image,
          width: 1200,
          height: 630,
          alt: title,
        },
      ],
      ...(config?.publishedTime && { publishedTime: config.publishedTime }),
      ...(config?.modifiedTime && { modifiedTime: config.modifiedTime }),
      ...(config?.author && { authors: [config.author] }),
      ...(config?.section && { section: config.section }),
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
      images: [image],
      creator: defaultMetadata.twitterHandle,
      site: defaultMetadata.twitterHandle,
    },
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
        'max-video-preview': -1,
        'max-image-preview': 'large',
        'max-snippet': -1,
      },
    },
    alternates: {
      canonical: url,
    },
    icons: {
      icon: '/favicon.ico',
      apple: '/apple-touch-icon.png',
    },
    manifest: '/site.webmanifest',
    // Search-engine ownership is verified out-of-band: Google via a DNS
    // TXT record, Bing via /BingSiteAuth.xml — no meta tags needed.
  };
}

export interface BreadcrumbItem {
  name: string;
  url: string;
}

interface BreadcrumbData {
  items: BreadcrumbItem[];
}

interface ProductData {
  name?: string;
  description?: string;
  url?: string;
  price?: string;
  rating?: string;
  ratingCount?: string;
}

interface ArticleData {
  title?: string;
  description?: string;
  image?: string;
  author?: string;
  publishedTime?: string;
  modifiedTime?: string;
}

interface FAQData {
  questions?: Array<{ question: string; answer: string }>;
}

type StructuredData = ProductData | ArticleData | FAQData | BreadcrumbData | undefined;
type StructuredDataType = 'organization' | 'product' | 'article' | 'faq' | 'website' | 'breadcrumb';

export function generateStructuredData(type: StructuredDataType, data?: StructuredData) {
  switch (type) {
    case 'organization':
      return {
        '@context': 'https://schema.org',
        '@type': 'Organization',
        name: 'Attune AI',
        alternateName: 'Smart AI Memory',
        url: defaultMetadata.url,
        logo: `${defaultMetadata.url}/logo.png`,
        description: defaultMetadata.description,
        sameAs: [
          'https://github.com/Smart-AI-Memory',
          'https://github.com/Smart-AI-Memory/attune-ai',
        ],
        contactPoint: {
          '@type': 'ContactPoint',
          email: 'patrick.roebuck@pm.me',
          contactType: 'Customer Service',
        },
      };

    case 'product': {
      const productData = data as ProductData | undefined;
      return {
        '@context': 'https://schema.org',
        '@type': 'SoftwareApplication',
        name: productData?.name || 'Attune AI',
        applicationCategory: 'DeveloperApplication',
        operatingSystem: 'Cross-platform',
        description: productData?.description || 'Help content generated from your codebase that stays fresh automatically',
        url: productData?.url || `${defaultMetadata.url}/docs`,
        author: {
          '@type': 'Organization',
          name: 'Smart AI Memory',
        },
        offers: {
          '@type': 'Offer',
          price: productData?.price || '0',
          priceCurrency: 'USD',
          availability: 'https://schema.org/InStock',
        },
        aggregateRating: {
          '@type': 'AggregateRating',
          ratingValue: productData?.rating || '5',
          ratingCount: productData?.ratingCount || '1',
        },
      };
    }

    case 'article': {
      const articleData = data as ArticleData | undefined;
      const authorName = articleData?.author || 'Attune AI';
      const isOrg =
        authorName === 'Smart AI Memory' ||
        authorName === 'Smart AI Memory Team' ||
        authorName === 'Attune AI';
      const imageUrl = articleData?.image
        ? (articleData.image.startsWith('http') ? articleData.image : `${defaultMetadata.url}${articleData.image}`)
        : `${defaultMetadata.url}${defaultMetadata.image}`;
      return {
        '@context': 'https://schema.org',
        '@type': 'Article',
        headline: articleData?.title,
        description: articleData?.description,
        image: imageUrl,
        author: {
          '@type': isOrg ? 'Organization' : 'Person',
          name: authorName,
        },
        publisher: {
          '@type': 'Organization',
          name: 'Attune AI',
          logo: {
            '@type': 'ImageObject',
            url: `${defaultMetadata.url}/logo.png`,
          },
        },
        datePublished: articleData?.publishedTime,
        dateModified: articleData?.modifiedTime || articleData?.publishedTime,
      };
    }

    case 'website':
      return {
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        name: defaultMetadata.siteName,
        url: defaultMetadata.url,
        potentialAction: {
          '@type': 'SearchAction',
          target: {
            '@type': 'EntryPoint',
            urlTemplate: `${defaultMetadata.url}/docs?q={search_term_string}`,
          },
          'query-input': 'required name=search_term_string',
        },
      };

    case 'breadcrumb': {
      const breadcrumbData = data as BreadcrumbData | undefined;
      return {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: (breadcrumbData?.items || []).map((item, index) => ({
          '@type': 'ListItem',
          position: index + 1,
          name: item.name,
          item: item.url,
        })),
      };
    }

    case 'faq': {
      const faqData = data as FAQData | undefined;
      return {
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        mainEntity: (faqData?.questions || []).map((q) => ({
          '@type': 'Question',
          name: q.question,
          acceptedAnswer: {
            '@type': 'Answer',
            text: q.answer,
          },
        })),
      };
    }

    default:
      return null;
  }
}
