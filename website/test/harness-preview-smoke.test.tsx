import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { execFile } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { createServer } from 'node:http';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import { renderToStaticMarkup } from 'react-dom/server';
import Home from '../app/page';
import Docs from '../app/docs/page';
import { HARNESS_CURRENT_INSTALL_URL, HARNESS_CURRENT_VERSION } from '../lib/harness-release';
import nextConfig from '../next.config';

// Exercise the real entry links; leave unrelated client providers and CSS
// compilation to the normal website build, as in the publication tests.
vi.mock('@/components/Navigation', () => ({ default: () => null }));
vi.mock('@/components/Footer', () => ({ default: () => null }));
vi.mock('../app/page.module.css', () => ({ default: {} }));

const run = promisify(execFile);
const checker = fileURLToPath(new URL('../scripts/harness-preview-smoke.py', import.meta.url));
const publicRoot = new URL('../public/', import.meta.url);
const readPublic = (name: string) => readFileSync(new URL(name, publicRoot));
const trainingReceipt = JSON.parse(readPublic('harness-training-static/import.json').toString('utf8'));
const setupRoute = '/harness/help/get-started/';
const practiceRoute = '/harness/learn/reporting/assets/reporting-practice.zip';

// Next injects this option in builds; match it when rendering Link outside Next.
beforeEach(() => vi.stubEnv('__NEXT_TRAILING_SLASH', nextConfig.trailingSlash ? 'true' : ''));
afterEach(() => vi.unstubAllEnvs());

/** Serve the rendered entry and committed payload through the checker's real curl boundary. */
async function checkJourney({ destination, removeAnchor = false, corruptZip = false }: {
  destination?: string; removeAnchor?: boolean; corruptZip?: boolean;
} = {}) {
  let homepage = renderToStaticMarkup(<Home />);
  if (destination !== undefined) {
    const original = `href="${HARNESS_CURRENT_INSTALL_URL}"`;
    expect(homepage).toContain(original);
    homepage = homepage.replace(original, `href="${destination}"`);
  }
  const routes = new Map<string, Buffer>([
    ['/', Buffer.from(homepage)],
    ['/docs/', Buffer.from(renderToStaticMarkup(<Docs />))],
    [setupRoute, readPublic('harness-help-static/get-started/index.html')],
    ['/harness/help/', readPublic('harness-help-static/index.html')],
    ['/harness/help/build.json', readPublic('harness-help-static/build.json')],
    ['/harness-help-static/import.json', readPublic('harness-help-static/import.json')],
    ['/harness/learn/import.json', readPublic('harness-training-static/import.json')],
  ]);
  for (const name of Object.keys(trainingReceipt.files)) {
    const route = `/harness/learn/${name.replace(/index\.html$/, '')}`;
    routes.set(route, readPublic(`harness-training-static/${name}`));
  }
  if (removeAnchor) {
    const setup = routes.get(setupRoute)!.toString('utf8');
    expect(setup).toContain('id="install-harness"');
    routes.set(setupRoute, Buffer.from(setup.replace('id="install-harness"', 'id="removed-installation"')));
  }
  if (corruptZip) routes.set(practiceRoute, Buffer.from('damaged download'));

  const requests: string[] = [];
  const server = createServer((request, response) => {
    const route = new URL(request.url!, 'http://fixture.invalid').pathname;
    requests.push(route);
    if (route === '/harness/learn/') {
      response.writeHead(307, { Location: `${setupRoute}#set-up-the-practice-folder` }).end();
      return;
    }
    const body = routes.get(route);
    response.writeHead(body === undefined ? 404 : 200).end(body);
  });
  await new Promise<void>((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('Expected a loopback HTTP port');
  try {
    const { stdout } = await run(process.env.ATTUNE_PYTHON || 'python3', [
      '-B', '-c',
      'import json, pathlib, runpy, sys; root = pathlib.Path(sys.argv[1]).parents[1] / "public"; runpy.run_path(sys.argv[1])["check_journey"](sys.argv[2], json.loads((root / "harness-help-static/import.json").read_text(encoding="utf-8")), json.loads((root / "harness-training-static/import.json").read_text(encoding="utf-8")), sys.argv[3])',
      checker, `http://127.0.0.1:${address.port}`, HARNESS_CURRENT_VERSION,
    ], { timeout: 20_000 });
    return { stdout, requests };
  } finally {
    await new Promise<void>((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
  }
}

describe('maintained Harness installation journey', () => {
  it('follows the actual homepage through the committed course and historical files', async () => {
    const { stdout, requests } = await checkJourney();
    expect(stdout).toContain('Passed: homepage');
    expect(requests).toContain(setupRoute);
    expect(requests).toContain(practiceRoute);
    expect(requests).toContain('/harness/learn/1.7.0-preparation/assets/reporting-example.zip');
  }, 25_000);

  it.each(['/harness/help/', setupRoute])('refuses installation destination %s', async destination => {
    await expect(checkJourney({ destination })).rejects.toThrow(
      `expected 'Install Harness ${HARNESS_CURRENT_VERSION}' to link to ${setupRoute}#install-harness`,
    );
  }, 25_000);

  it('refuses a valid installation URL when its anchor is missing', async () => {
    await expect(checkJourney({ removeAnchor: true })).rejects.toThrow('missing installation anchor');
  }, 25_000);

  it('still refuses a corrupted practice ZIP after entering through installation', async () => {
    await expect(checkJourney({ corruptZip: true })).rejects.toThrow('bytes differ from the committed training export');
  }, 25_000);
});
