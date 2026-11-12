import { MetadataRoute } from 'next';
import { getAllPosts, getAllTags } from '@/lib/blog';

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = 'https://smartaimemory.com';
  const canonicalUrl = (route: string) => `${baseUrl}${route}${route.endsWith('/') ? '' : '/'}`;

  // Homepage
  const homepage = [{
    url: canonicalUrl('/'),
    lastModified: new Date(),
    changeFrequency: 'weekly' as const,
    priority: 1,
  }];

  // High-priority product pages
  const highPriority = [
    '/how-it-works',
    '/fix-workspace',
    '/docs',
    '/harness/help/',
    '/harness/help/get-started/',
    '/harness/help/ai-tools-and-integrations/',
    '/pricing',
  ].map((route) => ({
    url: canonicalUrl(route),
    lastModified: new Date(),
    changeFrequency: 'weekly' as const,
    priority: 0.9,
  }));

  // Standard content pages
  const standardPages = [
    '/blog',
    '/benchmarks',
    '/changelog',
    '/contact',
    '/faq/',
    '/migrate',
  ].map((route) => ({
    url: canonicalUrl(route),
    lastModified: new Date(),
    changeFrequency: 'weekly' as const,
    priority: 0.7,
  }));

  // Utility pages
  const utilityPages = [
    '/privacy',
    '/terms',
  ].map((route) => ({
    url: canonicalUrl(route),
    lastModified: new Date(),
    changeFrequency: 'monthly' as const,
    priority: 0.3,
  }));

  // Blog posts
  const posts = getAllPosts();
  const blogPages = posts.map((post) => ({
    url: canonicalUrl(`/blog/${post.slug}`),
    lastModified: new Date(post.date),
    changeFrequency: 'monthly' as const,
    priority: 0.6,
  }));

  // Blog tag archive pages
  const tags = getAllTags();
  const tagPages = tags.map((tag) => ({
    url: canonicalUrl(`/blog/tag/${encodeURIComponent(tag)}`),
    lastModified: new Date(),
    changeFrequency: 'weekly' as const,
    priority: 0.5,
  }));

  return [
    ...homepage,
    ...highPriority,
    ...standardPages,
    ...utilityPages,
    ...blogPages,
    ...tagPages,
  ];
}
