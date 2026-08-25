/**
 * IndexNow deploy ping — submits the freshly built sitemap's URLs to
 * https://www.indexnow.org/ (Bing, Yandex, Seznam, Naver) after a
 * production build.
 *
 * Runs via `npm run build:vercel` (see vercel.json buildCommand).
 * Fail-open by design: this script NEVER fails the build — any error
 * logs and exits 0. Ping only happens when VERCEL_ENV=production;
 * pass --dry-run to print the payload locally without sending.
 *
 * The key is intentionally public: IndexNow verifies ownership by
 * serving public/<key>.txt from the site root.
 */
import { existsSync, readFileSync, readdirSync } from 'node:fs';

const HOST = 'smartaimemory.com';
const ENDPOINT = 'https://api.indexnow.org/indexnow';
const SITEMAP_BODY = '.next/server/app/sitemap.xml.body';

const dryRun = process.argv.includes('--dry-run');

function log(msg) {
  console.log(`indexnow: ${msg}`);
}

async function main() {
  if (process.env.VERCEL_ENV !== 'production' && !dryRun) {
    log(`skipped (VERCEL_ENV=${process.env.VERCEL_ENV ?? 'unset'}, not production)`);
    return;
  }

  const keyFile = readdirSync('public').find((f) => /^[0-9a-f]{8,128}\.txt$/.test(f));
  if (!keyFile) {
    log('skipped (no key file matching public/<hex>.txt)');
    return;
  }
  const key = keyFile.replace(/\.txt$/, '');

  if (!existsSync(SITEMAP_BODY)) {
    log(`skipped (${SITEMAP_BODY} not found — did the build layout change?)`);
    return;
  }
  const xml = readFileSync(SITEMAP_BODY, 'utf8');
  const urlList = [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
  if (urlList.length === 0) {
    log('skipped (no <loc> entries parsed from sitemap)');
    return;
  }

  const payload = { host: HOST, key, urlList };
  if (dryRun) {
    log(`dry-run: would submit ${urlList.length} URLs with key ${key.slice(0, 8)}…`);
    console.log(JSON.stringify(payload, null, 2));
    return;
  }

  const res = await fetch(ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
    body: JSON.stringify(payload),
  });
  // 200 = submitted, 202 = accepted (key validation pending)
  log(`submitted ${urlList.length} URLs — HTTP ${res.status}`);
}

main().catch((err) => {
  log(`error (non-fatal): ${err?.message ?? err}`);
});
