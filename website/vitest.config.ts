import { defineConfig } from 'vitest/config';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));

// Mirror Next's `@/*` -> `./*` tsconfig path so API-route tests can
// import `@/lib/...` the same way the routes do. Scoped to a leading
// `@/` via regex so it never rewrites `@scope/pkg` package imports.
export default defineConfig({
  resolve: {
    alias: [{ find: /^@\//, replacement: `${root}/` }],
  },
});
