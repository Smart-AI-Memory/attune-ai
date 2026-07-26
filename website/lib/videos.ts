/**
 * Help Videos - Single Source of Truth
 *
 * Registry for the /learn page and the conditional "Learn" nav link.
 * Both render from this array: while it is empty the /learn route
 * 404s and the nav link is hidden, so the rails ship dark and light
 * up when the first video lands.
 *
 * `youtubeId` is the 11-char YouTube video id (the site embeds via
 * youtube-nocookie.com). `featureId` optionally ties a walkthrough to
 * a feature master in content/features/ — keep it matching the
 * feature slug used there so help surfaces and the site agree.
 */

export type VideoTopic = "getting-started" | "feature";

export interface HelpVideo {
  id: string;
  title: string;
  description: string;
  youtubeId: string;
  topic: VideoTopic;
  /** Feature slug from content/features/<slug>.md, when topic is "feature". */
  featureId?: string;
  /** ISO date the video was published. */
  published?: string;
}

export const HELP_VIDEOS: HelpVideo[] = [
  // Seed these as demos clear the release gate, e.g.:
  // {
  //   id: "dynamic-forms-demo",
  //   title: "Dynamic forms in 4 minutes",
  //   description:
  //     "Socratic discovery that respects your time: one form for the " +
  //     "independent dimensions of a decision, and pushback you can click.",
  //   youtubeId: "<11-char-id>",
  //   topic: "feature",
  //   featureId: "elicitation-forms",
  // },
];

export const TOPIC_LABELS: Record<VideoTopic, string> = {
  "getting-started": "Getting started",
  feature: "Feature walkthroughs",
};
