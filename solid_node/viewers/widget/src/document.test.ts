/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// The schema v2 gate. This viewer evaluates `$t` and nothing else, so a
// document whose expressions name drivers describes a pose it cannot
// compute -- and rendering it anyway would show a wrong machine rather
// than an error. An empty driver table names nothing, so it is exactly
// the version 1 document and renders unchanged.

import { describe, expect, it } from 'vitest';
import { assertRenderable } from './viewer';
import { Manifest } from './types';

const document = (overrides: Partial<Manifest>): Manifest => ({
  format: 'solid-node-export',
  version: 2,
  animation: { fps: 30, frames: 360 },
  root: { name: 'root', type: 'AssemblyNode', color: null, operations: [] },
  ...overrides,
});

describe('assertRenderable', () => {
  it('accepts a version 1 document, which carries no table at all', () => {
    expect(() =>
      assertRenderable(document({ version: 1, drivers: undefined }), '/m.json'),
    ).not.toThrow();
  });

  it('accepts a version 2 document with an empty driver table', () => {
    expect(() =>
      assertRenderable(document({ drivers: {} }), '/m.json'),
    ).not.toThrow();
  });

  it('refuses a non-empty driver table, naming the drivers', () => {
    const manifest = document({
      drivers: {
        'x_axis.motor': {
          default: 8000, range: [0, 8000], unit: 'ustep',
          dtype: 'int', scale: 0.0125,
        },
      },
    });

    expect(() => assertRenderable(manifest, '/m.json')).toThrow(
      /x_axis\.motor/,
    );
  });
});
