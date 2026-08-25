import { notFound } from 'next/navigation';
import Link from 'next/link';
import type { Metadata } from 'next';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
import { generateMetadata as generateSEOMetadata } from '@/lib/metadata';
import { getAllTags, getPostsByTag } from '@/lib/blog';

interface PageProps {
  params: Promise<{ tag: string }>;
}

export async function generateStaticParams() {
  const tags = getAllTags();
  return tags.map((tag) => ({ tag }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { tag: rawTag } = await params;
  const tag = decodeURIComponent(rawTag);
  const posts = getPostsByTag(tag);

  if (posts.length === 0) {
    return { title: 'Tag Not Found' };
  }

  return generateSEOMetadata({
    title: `Posts tagged '${tag}' — Attune AI Blog`,
    description: `${posts.length} article${posts.length === 1 ? '' : 's'} tagged with '${tag}' on the Attune AI blog. Claude Code tutorials, agent patterns, and AI workflow guides.`,
    url: `https://smartaimemory.com/blog/tag/${encodeURIComponent(tag)}`,
    keywords: [tag, 'Claude Code', 'Attune AI', 'AI developer blog'],
  });
}

export default async function TagPage({ params }: PageProps) {
  const { tag: rawTag } = await params;
  const tag = decodeURIComponent(rawTag);
  const posts = getPostsByTag(tag);

  if (posts.length === 0) {
    notFound();
  }

  const allTags = getAllTags();

  return (
    <>
      <Navigation />
      <main id="main-content" className="min-h-screen pt-16">
        {/* Hero */}
        <section className="py-16 bg-gradient-to-b from-[var(--border)] to-transparent">
          <div className="container">
            <div className="max-w-3xl mx-auto">
              <nav className="mb-6 text-sm text-[var(--muted)]">
                <Link href="/blog" className="hover:text-[var(--primary)] transition-colors">
                  ← All Posts
                </Link>
              </nav>
              <p className="text-sm text-[var(--muted)] uppercase tracking-wider mb-3">Tag</p>
              <h1 className="text-4xl sm:text-5xl font-bold mb-4">{tag}</h1>
              <p className="text-xl text-[var(--text-secondary)]">
                {posts.length} article{posts.length === 1 ? '' : 's'}
              </p>
            </div>
          </div>
        </section>

        <section className="py-16">
          <div className="container">
            <div className="max-w-6xl mx-auto grid lg:grid-cols-4 gap-12">
              {/* Posts */}
              <div className="lg:col-span-3 space-y-8">
                {posts.map((post) => (
                  <article
                    key={post.slug}
                    className="p-6 rounded-xl border border-[var(--border)] hover:border-[var(--primary)] transition-colors"
                  >
                    <div className="flex flex-wrap gap-2 mb-3">
                      {post.tags.map((t) => (
                        <Link
                          key={t}
                          href={`/blog/tag/${encodeURIComponent(t)}`}
                          className={`px-2 py-0.5 rounded text-xs font-semibold transition-colors ${
                            t === tag
                              ? 'bg-[var(--primary)] text-white'
                              : 'bg-[var(--border)] hover:bg-[var(--primary)] hover:text-white'
                          }`}
                        >
                          {t}
                        </Link>
                      ))}
                    </div>
                    <Link href={`/blog/${post.slug}`}>
                      <h2 className="text-2xl font-bold mb-2 hover:text-[var(--primary)] transition-colors">
                        {post.title}
                      </h2>
                    </Link>
                    <p className="text-[var(--text-secondary)] mb-4">{post.excerpt}</p>
                    <div className="flex items-center gap-4 text-sm text-[var(--muted)]">
                      <span>{post.author}</span>
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
                  </article>
                ))}
              </div>

              {/* Sidebar: all tags */}
              <aside className="lg:col-span-1">
                <h2 className="text-lg font-bold mb-4">All Tags</h2>
                <div className="flex flex-wrap gap-2">
                  {allTags.map((t) => (
                    <Link
                      key={t}
                      href={`/blog/tag/${encodeURIComponent(t)}`}
                      className={`px-3 py-1 rounded-full text-sm font-semibold transition-colors ${
                        t === tag
                          ? 'bg-[var(--primary)] text-white'
                          : 'bg-[var(--border)] hover:bg-[var(--primary)] hover:text-white'
                      }`}
                    >
                      {t}
                    </Link>
                  ))}
                </div>
              </aside>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
