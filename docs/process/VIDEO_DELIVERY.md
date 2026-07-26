# Video delivery playbook

**Created:** 2026-07-23. Consolidates the capture/export/hosting
rulings from the demo-script work (dry-run + Patrick, 2026-07-23)
into one durable, cross-video reference. Per-video scripts (e.g.
[DEMO_DYNAMIC_FORMS_script.md](DEMO_DYNAMIC_FORMS_script.md),
[DEMO_10_6_0_script.md](DEMO_10_6_0_script.md)) own the content;
this page owns the pipeline. If a script and this page disagree
on mechanics, fix the drift in the same PR.

## Capture (ruled)

- Full display, screen 1 (LG HDR 4K) at native 4K. Identify the
  stage by a 5-second test take + thumbnail check — never by
  display name (names disagree across tools).
- Recorder config verified fresh every session: mic = G733,
  system audio OFF, camera off. Config drifts between sessions.
- Do Not Disturb on; screen 1 is a clean set. Terminal font
  16–18pt minimum (binding harder for the 4:5 crop).
- After EVERY take: `cp -R` the `.screenstudio` bundle out of
  `~/Screen Studio Projects/` before touching the app again.

## Exports (ruled)

| Cut | Resolution | Why |
|-----|------------|-----|
| Main (~4 min) | mp4, 1920×1080 (16:9), H.264 + AAC, 10–60 fps, ≤5 GB | Full stage, forms readable; YouTube-native for the article-embed path |
| Social (~60s) | mp4, 1080×1350 (4:5 portrait) | Best current LinkedIn mobile-feed engagement |

Shooting is unchanged by the split: record the full 16:9 stage,
no record-time portrait framing. Build the 4:5 cut in the editor
(one-click vertical + auto-zoom reframes) and eyeball every form
beat in the portrait crop.

## Captions and transcript

- Generate captions from the mic track (auto-captions off the
  G733), then QC pass per segment — narrated claims must read
  exactly as spoken.
- Export an SRT sidecar from the corrected captions. Upload the
  SAME SRT to both YouTube and the LinkedIn native video —
  LinkedIn feed video autoplays muted, so the 4:5 cut without
  captions loses its first three seconds.
- Publish the corrected transcript as a per-video receipts page
  at `docs/process/<DEMO_NAME>_transcript.md` (see
  [DEMO_DYNAMIC_FORMS_transcript.md](DEMO_DYNAMIC_FORMS_transcript.md)
  for the template: verbatim narration + claim→receipt table).
  The `docs/` tree auto-projects to attune-ai.dev, so the page
  is linkable the moment it lands on `main`.

## Hosting and placement

| Surface | What goes there |
|---------|-----------------|
| YouTube | Main 16:9 cut — the canonical hosted copy |
| LinkedIn feed post | Native upload of the 4:5 social cut + SRT |
| LinkedIn article | YouTube EMBED only — articles cannot host native video |
| attune-ai.dev blog | `videoId: <youtube-id>` in the post's frontmatter renders the `VideoEmbed` facade above the content |

## YouTube conventions

- Upload unlisted first; flip to public only after the chair's
  honesty-gate pass (cut + transcript page reviewed together).
- Chapters: paste the script's journey table as timestamped
  lines in the description — segment names, final-export times.
- Description, first lines: one-sentence value claim, link to
  attune-ai.dev, link to the transcript/receipts page ("every
  claim in this video has a receipt").
- End screen: link card back to attune-ai.dev.

## Publish checklist

- [ ] Honesty-gate pass on the final cut (chair)
- [ ] Transcript page filled — no unresolved receipt rows
- [ ] SRT uploaded on YouTube AND LinkedIn native video
- [ ] YouTube chapters + description links in place
- [ ] Blog post frontmatter carries `videoId`; embed verified
      on the deployed page
- [ ] `.screenstudio` bundles archived for every kept take
