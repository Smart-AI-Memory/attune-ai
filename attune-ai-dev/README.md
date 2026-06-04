# attune-ai-dev

Source for [attune-ai.dev](https://attune-ai.dev) — the canonical
home for the `attune-ai` package: a landing page, the public **Help**
site (`/help`, generated from the `.help/` corpus), and the article
*The Discipline of Agent Collaboration* (`/discipline`).

Sibling site to `website/` (smartaimemory.com). The two have
different jobs:

| Site | Job |
|---|---|
| `website/` (smartaimemory.com) | Full product marketing — six packages, blog, pricing. |
| `attune-ai-dev/` (attune-ai.dev) | Package home: landing + user Help + the Discipline article. |

## Files

- `index.html` — bare-domain landing page. Single file, hand-edited.
  Links to Help, the Discipline article, smartaimemory.com, and
  GitHub. Matches the smartaimemory.com brand tokens (`#004ac6`
  primary, Manrope headline, system body).
- `brand.css` — shared brand tokens + base styles. Single-sourced;
  both build scripts read it.
- `discipline/` — the article *The Discipline of Agent Collaboration*,
  served at `attune-ai.dev/discipline`. Built by `build_discipline.py`
  (markdown-it-py) from `COLLABORATION_DISCIPLINE.md`.
- `help/` — the generated public help site, served at
  `attune-ai.dev/help`. Built by `build_help.py` from the `.help/`
  corpus (reuses `attune.ops.help_data` + markdown-it-py). Committed
  static HTML; rebuilt by `.github/workflows/build-help-site.yml`
  when `.help/` changes.
- `build_discipline.py` / `build_help.py` — build scripts. Run
  locally / in CI; Vercel never runs them (it serves the committed
  HTML).
- `og.png` — *(planned)* 1200×630 social card image.

## Deploying

Static site. Deployed on **Vercel** (same account as
`website/` / smartaimemory.com).

### One-time setup in Vercel

1. New Project → Import this repo (`Smart-AI-Memory/attune-ai`).
2. **Root Directory:** `attune-ai-dev`
3. **Framework Preset:** Other (or none — static site).
4. **Build Command:** *(leave empty)*
5. **Output Directory:** *(leave empty — serves repo root)*
6. **Install Command:** *(leave empty)*
7. Deploy.

`vercel.json` in this directory carries the runtime config
(clean URLs, security headers, OG-image cache policy).

### Custom domain

1. Vercel project → Settings → Domains → Add `attune-ai.dev`.
2. Vercel will show DNS records to add (typically an A record
   for the apex pointing at `76.76.21.21`, and a CNAME for
   `www` pointing at `cname.vercel-dns.com`).
3. Add those records in Cloudflare DNS for `attune-ai.dev`.
   Set Cloudflare proxy status to **DNS only** (gray cloud)
   for the Vercel records — Vercel handles its own CDN/SSL.

## DNS

Domain registered at Cloudflare Registrar. DNS managed
through Cloudflare. Vercel handles SSL termination
automatically once the DNS records resolve.

## Updating the version chip

The eyebrow chip in `index.html` shows the current package
version (currently `v7.4.0`). Update by hand on each release,
or wire it to `pyproject.toml` later via a build step.

## Why a separate site

`attune-ai.dev` exists primarily to serve the article and reinforce
the `pip install attune-ai` brand surface. Duplicating the
smartaimemory.com marketing here would be redundant; pointing
back to it from the landing keeps both sites doing one job each.
