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
import {
  Manifest, ManifestFlexible, ManifestNode, RawOperation,
} from './types';

const node = (name: string, operations: RawOperation[],
              children?: ManifestNode[]): ManifestNode => ({
  name, type: 'AssemblyNode', color: null, operations, children,
});

// The valve spring of `tests/flexible_project/spring.py`, as the
// producer publishes it: the spec verbatim and one expression per
// parameter.
const SPRING_SPEC = {
  molejo: 1,
  profile: { type: 'circle', radius: 2.0 },
  path: [{ type: 'helix', radius: 14.0, turns: 6.5,
           height: { param: 'height' } }],
  loop: false,
  tessellation: { path: 240, profile: 16 },
};

const spring = (overrides: Partial<ManifestFlexible> = {}): ManifestNode => ({
  name: 'spring', type: 'LeafNode', color: null, operations: [],
  flexible: {
    tech: 'molejo', spec: SPRING_SPEC,
    params: { height: '(46.8 - valvetrain.lift)' },
    ...overrides,
  },
});

const lift = {
  default: 0.0, range: [0.0, 12.0], unit: 'mm',
  dtype: 'float', scale: null,
};

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

// Schema v3 (the flexible node shape). The producer emits the LOWEST
// version its content needs, so this viewer accepts the whole range it
// can render and refuses anything outside it -- the same posture it
// takes toward a `tech` it cannot evaluate, and for the same reason:
// a schema this build cannot read is not a document to guess at.
describe('assertRenderable on a flexible document', () => {
  it('accepts a version 3 document carrying a flexible node', () => {
    const manifest = document({
      version: 3,
      drivers: { 'valvetrain.lift': lift },
      root: node('engine', [], [node('valvetrain', [], [spring()])]),
    });

    expect(() => assertRenderable(manifest, '/m.json')).not.toThrow();
  });

  it('refuses a technology it cannot evaluate, naming node and tech', () => {
    const manifest = document({
      version: 3,
      drivers: { 'valvetrain.lift': lift },
      root: node('engine', [], [spring({ tech: 'wibble' })]),
    });

    expect(() => assertRenderable(manifest, '/m.json')).toThrow(/spring/);
    expect(() => assertRenderable(manifest, '/m.json')).toThrow(/wibble/);
    expect(() => assertRenderable(manifest, '/m.json')).toThrow(/molejo/);
    expect(() => assertRenderable(manifest, '/m.json')).toThrow(/m\.json/);
  });

  it('refuses a version it does not render, naming it and the ones it does', () => {
    const manifest = document({
      version: 4 as unknown as Manifest['version'],
      root: node('root', []),
    });

    expect(() => assertRenderable(manifest, '/m.json')).toThrow(/\b4\b/);
    expect(() => assertRenderable(manifest, '/m.json')).toThrow(/1, 2, 3/);
    expect(() => assertRenderable(manifest, '/m.json')).toThrow(/m\.json/);
  });

  it('holds a `params` expression to the same drivers table', () => {
    // `params` is an expression like any other, so an id its own table
    // does not declare is the same malformed document as an operation's
    // -- there is no value to bind, and evaluating it anyway would show
    // a wrong SHAPE instead of a wrong pose.
    const manifest = document({
      version: 3,
      drivers: {},
      root: node('engine', [], [spring()]),
    });

    expect(() => assertRenderable(manifest, '/m.json'))
      .toThrow(/valvetrain\.lift/);
  });

  it('leaves a `$t` parameter alone: animation time is not a driver', () => {
    const manifest = document({
      version: 3,
      drivers: {},
      root: node('engine', [], [
        spring({ params: { height: '(46.8 - (12.0 * $t))' } }),
      ]),
    });

    expect(() => assertRenderable(manifest, '/m.json')).not.toThrow();
  });
});
