import { MetadataRoute } from 'next';
import { getAllPosts, getAllTags } from '@/lib/blog';
import { wizards } from '@/lib/wizards';

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = 'https://smartaimemory.com';

  // Homepage
  const homepage = [{
    url: baseUrl,
    lastModified: new Date(),
    changeFrequency: 'weekly' as const,
    priority: 1,
  }];

  // High-priority product pages
  const highPriority = [
    '/framework',
    '/pricing',
    '/wizards',
    '/workflows',
  ].map((route) => ({
    url: `${baseUrl}${route}`,
    lastModified: new Date(),
    changeFrequency: 'weekly' as const,
    priority: 0.9,
  }));

  // Standard content pages
  const standardPages = [
    '/docs',
    '/plugins',
    '/faq',
    '/contact',
    '/book',
    '/blog',
    '/chapter-23',
    '/tools/debug-wizard',
    '/tools/workflows',
    '/demo/distributed-memory',
  ].map((route) => ({
    url: `${baseUrl}${route}`,
    lastModified: new Date(),
    changeFrequency: 'weekly' as const,
    priority: 0.7,
  }));

  // Utility pages
  const utilityPages = [
    '/privacy',
    '/terms',
    '/success',
  ].map((route) => ({
    url: `${baseUrl}${route}`,
    lastModified: new Date(),
    changeFrequency: 'monthly' as const,
    priority: 0.3,
  }));

  // Blog posts
  const posts = getAllPosts();
  const blogPages = posts.map((post) => ({
    url: `${baseUrl}/blog/${post.slug}`,
    lastModified: new Date(post.date),
    changeFrequency: 'monthly' as const,
    priority: 0.6,
  }));

  // Individual wizard pages
  const wizardPages = wizards.map((w) => ({
    url: `${baseUrl}/wizards/${w.name}`,
    lastModified: new Date(),
    changeFrequency: 'weekly' as const,
    priority: 0.8,
  }));

  // Blog tag archive pages
  const tags = getAllTags();
  const tagPages = tags.map((tag) => ({
    url: `${baseUrl}/blog/tag/${tag}`,
    lastModified: new Date(),
    changeFrequency: 'weekly' as const,
    priority: 0.5,
  }));

  // Changelog
  const changelogPages = [
    {
      url: `${baseUrl}/changelog`,
      lastModified: new Date(),
      changeFrequency: 'monthly' as const,
      priority: 0.5,
    },
  ];

  // Comparison pages
  const comparePages = [
    '/compare',
    '/compare/crewai-vs-attune',
    '/compare/langgraph-vs-attune',
    '/compare/best-ai-agent-frameworks-2026',
  ].map((route) => ({
    url: `${baseUrl}${route}`,
    lastModified: new Date(),
    changeFrequency: 'weekly' as const,
    priority: 0.8,
  }));

  return [
    ...homepage,
    ...highPriority,
    ...standardPages,
    ...utilityPages,
    ...blogPages,
    ...wizardPages,
    ...tagPages,
    ...changelogPages,
    ...comparePages,
  ];
}
