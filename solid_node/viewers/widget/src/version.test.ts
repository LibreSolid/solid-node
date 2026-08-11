/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// A host that ships against a different viewer needs to say so in a
// sentence rather than render an empty pane, which only works while
// there is exactly one place the number is written. package.json is that
// place, because the next cycle reads it from Python without building or
// running the bundle.

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { API_VERSION } from './version';

const pkg = JSON.parse(
  readFileSync(new URL('../package.json', import.meta.url), 'utf8'),
);

describe('API_VERSION', () => {
  it('is declared in package.json, where a Python caller can read it', () => {
    expect(typeof pkg.solidNodeViewerApi).toBe('number');
    expect(Number.isInteger(pkg.solidNodeViewerApi)).toBe(true);
    expect(pkg.solidNodeViewerApi).toBeGreaterThan(0);
  });

  it('is the number the package declares, not a second copy', () => {
    expect(API_VERSION).toBe(pkg.solidNodeViewerApi);
  });

  it('declares the camera-orientation API as version 3', () => {
    expect(API_VERSION).toBe(4);
  });
});
