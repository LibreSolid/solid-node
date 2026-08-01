/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// The viewer's API version is declared once, in package.json, and
// injected at build time by build.mjs. The suite must be given the same
// value from the same place, so a test can never agree with a bundle
// that was built from a different number.

import { readFileSync } from 'node:fs';
import { defineConfig } from 'vitest/config';

const pkg = JSON.parse(
  readFileSync(new URL('./package.json', import.meta.url), 'utf8'),
);

export default defineConfig({
  define: {
    __VIEWER_API_VERSION__: JSON.stringify(pkg.solidNodeViewerApi ?? null),
  },
});
