/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// The schema v2 consumer gate, INVERTED (ADR-056 stage 3b, design D8).
//
// The export delta's manifest contract says a consumer SHALL either
// evaluate driver-referencing expressions or fail loudly on a non-empty
// `drivers` table rather than render a wrong pose. Stage 3a took the
// second branch: this viewer evaluated `$t` and nothing else, so it
// refused every non-empty table. It now takes the first -- a document
// with drivers loads and renders at the pose its table's defaults
// imply, so these tests changed meaning with the capability.
//
// What stays refused is a MALFORMED document: one whose expressions
// name a qualified id its own table does not declare. There is no value
// to bind for it, and rendering it anyway would show a wrong machine
// rather than an error. The producer guarantees this cannot happen
// (every referenced id appears in the table); the gate is what makes a
// broken producer loud instead of silent.

import { describe, expect, it } from 'vitest';
import { assertRenderable } from './viewer';
import { Manifest, ManifestNode, RawOperation } from './types';

const node = (name: string, operations: RawOperation[],
              children?: ManifestNode[]): ManifestNode => ({
  name, type: 'AssemblyNode', color: null, operations, children,
});

const document = (overrides: Partial<Manifest>): Manifest => ({
  format: 'solid-node-export',
  version: 2,
  animation: { fps: 30, frames: 360 },
  root: node('root', []),
  ...overrides,
});

const motor = {
  default: 8000, range: [0, 8000], unit: 'ustep',
  dtype: 'int', scale: 0.0125,
};

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

  it('leaves a $t document alone: animation time is not a driver', () => {
    const manifest = document({
      drivers: {},
      root: node('root', [['r', '(360.0 * $t)', [0, 0, 1]]]),
    });

    expect(() => assertRenderable(manifest, '/m.json')).not.toThrow();
  });

  it('accepts a non-empty table whose ids its expressions declare', () => {
    // Stage 3a refused exactly this document. It now renders.
    const manifest = document({
      drivers: { 'x_axis.motor': motor },
      root: node('root', [], [
        node('x_axis', [], [
          node('carriage', [['t', ['(x_axis.motor * 0.0125)', '0', '0']]]),
        ]),
      ]),
    });

    expect(() => assertRenderable(manifest, '/m.json')).not.toThrow();
  });

  it('refuses an expression naming an id the table does not declare', () => {
    const manifest = document({
      drivers: { 'x_axis.motor': motor },
      root: node('root', [], [
        node('z_axis', [['r', '(z_axis.motor * 0.1125)', [0, 0, 1]]]),
      ]),
    });

    expect(() => assertRenderable(manifest, '/m.json'))
      .toThrow(/z_axis\.motor/);
    expect(() => assertRenderable(manifest, '/m.json')).toThrow(/m\.json/);
  });

  it('refuses a driver expression under an empty table too', () => {
    const manifest = document({
      drivers: {},
      root: node('root', [['t', ['(x_axis.motor * 0.0125)', '0', '0']]]),
    });

    expect(() => assertRenderable(manifest, '/m.json'))
      .toThrow(/x_axis\.motor/);
  });

  it('names the undeclared id even beside a legal one', () => {
    const manifest = document({
      drivers: { 'x_axis.motor': motor },
      root: node('root', [['t', [
        '((x_axis.motor * 0.0125) + (y_axis.motor * 0.0125))', '0', '0',
      ]]]),
    });

    expect(() => assertRenderable(manifest, '/m.json'))
      .toThrow(/y_axis\.motor/);
  });
});
