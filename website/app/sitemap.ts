import { MetadataRoute } from 'next';
import { getAllPosts } from '@/lib/blog';

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
    '/contribute',
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

  return [...homepage, ...highPriority, ...standardPages, ...utilityPages, ...blogPages];
}
