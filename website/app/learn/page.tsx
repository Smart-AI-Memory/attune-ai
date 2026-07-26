import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import Navigation from "@/components/Navigation";
import Footer from "@/components/Footer";
import { HELP_VIDEOS, TOPIC_LABELS, type VideoTopic } from "@/lib/videos";

export const metadata: Metadata = {
  title: "Learn Attune AI - Video Walkthroughs",
  description:
    "Short videos for getting started with Attune AI and working with " +
    "individual features.",
};

const TOPIC_ORDER: VideoTopic[] = ["getting-started", "feature"];

export default function LearnPage() {
  // Rails ship dark: no videos yet means no page (and no nav link).
  if (HELP_VIDEOS.length === 0) {
    notFound();
  }

  return (
    <>
      <Navigation />
      <main id="main-content" className="container min-h-screen pt-28 pb-16">
        <h1 className="text-4xl font-bold mb-3">Learn Attune AI</h1>
        <p className="text-lg mb-10 opacity-80">
          Short videos: getting started, then one feature at a time.
        </p>

        {TOPIC_ORDER.map((topic) => {
        const videos = HELP_VIDEOS.filter((v) => v.topic === topic);
        if (videos.length === 0) return null;
        return (
          <section key={topic} className="mb-12">
            <h2 className="text-2xl font-semibold mb-6">
              {TOPIC_LABELS[topic]}
            </h2>
            <div className="grid gap-8 md:grid-cols-2">
              {videos.map((video) => (
                <article
                  key={video.id}
                  className="rounded-xl border border-[var(--border)] overflow-hidden"
                >
                  <div className="aspect-video">
                    <iframe
                      src={`https://www.youtube-nocookie.com/embed/${video.youtubeId}`}
                      title={video.title}
                      allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                      allowFullScreen
                      loading="lazy"
                      className="w-full h-full"
                    />
                  </div>
                  <div className="p-5">
                    <h3 className="text-lg font-semibold mb-2">
                      {video.title}
                    </h3>
                    <p className="text-sm opacity-80">{video.description}</p>
                    {video.featureId && (
                      <p className="text-sm mt-3">
                        <Link
                          href="/docs"
                          className="text-[var(--primary)] hover:underline"
                        >
                          Read the {video.featureId.replace(/-/g, " ")} docs
                        </Link>
                      </p>
                    )}
                  </div>
                </article>
              ))}
            </div>
          </section>
        );
        })}
      </main>
      <Footer />
    </>
  );
}
