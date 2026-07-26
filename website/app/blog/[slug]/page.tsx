import { notFound } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import type { Metadata } from 'next';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import Breadcrumbs from '@/components/Breadcrumbs';
import VideoEmbed from '@/components/VideoEmbed';
import { getPostBySlug, getAllPosts, getRelatedPosts } from '@/lib/blog';
import { generateMetadata as generateSEOMetadata, generateStructuredData } from '@/lib/metadata';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface PageProps {
  params: Promise<{
    slug: string;
  }>;
}

export async function generateStaticParams() {
  const posts = getAllPosts();
  return posts.map((post) => ({
    slug: post.slug,
  }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const post = getPostBySlug(slug);

  if (!post) {
    return {
      title: 'Post Not Found',
    };
  }

  return generateSEOMetadata({
    title: post.title,
    description: post.excerpt,
    type: 'article',
    url: `https://smartaimemory.com/blog/${post.slug}`,
    image: post.coverImage,
    publishedTime: post.date,
    author: post.author,
  });
}

export default async function BlogPostPage({ params }: PageProps) {
  const { slug } = await params;
  const post = getPostBySlug(slug);

  if (!post) {
    notFound();
  }

  const articleSchema = generateStructuredData('article', {
    title: post.title,
    description: post.excerpt,
    image: post.coverImage,
    author: post.author,
    publishedTime: post.date,
  });

  const breadcrumbSchema = generateStructuredData('breadcrumb', {
    items: [
      { name: 'Home', url: 'https://smartaimemory.com' },
      { name: 'Blog', url: 'https://smartaimemory.com/blog' },
      { name: post.title, url: `https://smartaimemory.com/blog/${post.slug}` },
    ],
  });

  const isTutorial = post.tags.includes('tutorial');

  const relatedPosts = getRelatedPosts(post.slug, post.tags);

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(articleSchema) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbSchema) }}
      />
      {isTutorial && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              '@context': 'https://schema.org',
              '@type': 'HowTo',
              name: post.title,
              description: post.excerpt,
              author: {
                '@type': 'Person',
                name: post.author,
              },
            }),
          }}
        />
      )}
      <Navigation />
      <main id="main-content" className="min-h-screen pt-16">
        <article className="py-20">
          <div className="container">
            <div className="max-w-4xl mx-auto">
              <Breadcrumbs
                items={[
                  { name: 'Blog', href: '/blog' },
                  { name: post.title, href: `/blog/${post.slug}` },
                ]}
              />

              {/* Header */}
              <header className="mb-12">
                <h1 className="text-5xl font-bold mb-6">{post.title}</h1>

                <div className="flex flex-wrap items-center gap-4 text-[var(--muted)] mb-6">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-[var(--text-primary)]">
                      {post.author}
                    </span>
                  </div>
                  <span>•</span>
                  <time dateTime={post.date}>
                    {new Date(post.date).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                    })}
                  </time>
                  <span>•</span>
                  <span>{post.readingTime}</span>
                </div>

                <div className="flex flex-wrap gap-2">
                  {post.tags.map((tag) => (
                    <Link
                      key={tag}
                      href={`/blog/tag/${encodeURIComponent(tag)}`}
                      className="px-3 py-1 bg-[var(--surface-container-high)] text-[var(--foreground)] rounded-full text-sm font-semibold hover:bg-[var(--primary)] hover:text-white transition-colors"
                    >
                      {tag}
                    </Link>
                  ))}
                </div>
              </header>

              {/* Demo Video (takes precedence over the cover image) */}
              {post.videoId && (
                <div className="mb-12">
                  <VideoEmbed videoId={post.videoId} title={post.title} />
                </div>
              )}

              {/* Cover Image */}
              {!post.videoId && post.coverImage && (
                <div className="mb-12 relative aspect-video">
                  <Image
                    src={post.coverImage}
                    alt={post.title}
                    fill
                    className="object-cover rounded-lg"
                    priority
                  />
                </div>
              )}

              {/* Content */}
              <div className="prose prose-lg max-w-none prose-headings:font-bold prose-a:text-[var(--primary)] prose-a:no-underline hover:prose-a:underline prose-code:bg-[var(--border)] prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-[var(--border)] prose-pre:border prose-pre:border-[var(--border)]">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {post.content}
                </ReactMarkdown>
              </div>

              {/* Related Posts */}
              {relatedPosts.length > 0 && (
                <section className="mt-12 pt-12 border-t border-[var(--border)]">
                  <h2 className="text-2xl font-bold mb-6">Related Articles</h2>
                  <div className="grid md:grid-cols-3 gap-6">
                    {relatedPosts.map((related) => (
                      <Link
                        key={related.slug}
                        href={`/blog/${related.slug}`}
                        className="group block p-4 rounded-lg border border-[var(--border)] hover:border-[var(--primary)] transition-colors"
                      >
                        <h3 className="font-bold mb-2 group-hover:text-[var(--primary)] transition-colors">
                          {related.title}
                        </h3>
                        <p className="text-sm text-[var(--muted)] line-clamp-2">
                          {related.excerpt}
                        </p>
                        <div className="flex flex-wrap gap-1 mt-3">
                          {related.tags.slice(0, 3).map((tag) => (
                            <span
                              key={tag}
                              className="px-2 py-0.5 bg-[var(--surface-container-high)] text-[var(--foreground)] rounded text-xs"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      </Link>
                    ))}
                  </div>
                </section>
              )}

              {/* Footer */}
              <footer className="mt-12 pt-12 border-t border-[var(--border)]">
                <div className="flex justify-between items-center">
                  <Link
                    href="/blog"
                    className="btn btn-outline"
                  >
                    &larr; Back to Blog
                  </Link>
                  <Link
                    href="/contact"
                    className="btn btn-primary"
                  >
                    Get in Touch
                  </Link>
                </div>
              </footer>
            </div>
          </div>
        </article>
      </main>
      <Footer />
    </>
  );
}
