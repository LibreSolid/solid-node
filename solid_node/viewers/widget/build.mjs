/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

import { build } from 'esbuild';

// The banner satisfies the MIT notice-retention requirement for the
// bundled dependencies in every downstream copy of the bundle (git,
// PyPI, and each `solid export` output directory users publish).
const banner = `/*!
 * solid-widget.js - embeddable viewer for solid-node exports
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 *
 * Bundles three.js - Copyright 2010-2023 three.js authors
 *   MIT License - https://github.com/mrdoob/three.js/blob/dev/LICENSE
 * Bundles jokenizer - Copyright (c) 2018 Umut Özel
 *   MIT License - https://github.com/umutozel/jokenizer/blob/master/LICENSE
 */`;

await build({
  entryPoints: ['src/widget.ts'],
  bundle: true,
  minify: true,
  format: 'iife',
  globalName: 'SolidNodeWidget',
  outfile: 'dist/solid-widget.js',
  banner: { js: banner },
  logLevel: 'info',
});
