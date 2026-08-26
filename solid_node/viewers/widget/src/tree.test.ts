/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

import * as THREE from 'three';
import { describe, expect, it, vi } from 'vitest';

const { loadAsync } = vi.hoisted(() => ({
  loadAsync: vi.fn(() => Promise.resolve(new THREE.BoxGeometry())),
}));

vi.mock('three/examples/jsm/loaders/STLLoader.js', () => ({
  STLLoader: class { loadAsync = loadAsync; },
}));

// The real evaluator, watched: what a driver change must NOT do is
// re-evaluate an expression that does not name it, and the only way to
// see that is to count the evaluations.
vi.mock('./evaluator', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./evaluator')>();
  return { ...actual, evalExpr: vi.fn(actual.evalExpr) };
});

import { evalExpr } from './evaluator';
import { assemblyPathKey, materialForColor, WidgetTree } from './tree';
import { ManifestNode } from './types';

const evaluations = () =>
  (evalExpr as unknown as ReturnType<typeof vi.fn>).mock.calls
    .map((call) => call[0] as string);

const leaf = (overrides: Partial<ManifestNode> = {}): ManifestNode => ({
  name: 'leaf', type: 'part', color: '#cc4444', operations: [],
  model: 'leaf.stl', mtime: 1, ...overrides,
});

const root = (children: ManifestNode[]): ManifestNode => ({
  name: 'root', type: 'assembly', color: null, operations: [], children,
});

describe('materialForColor', () => {
  it('uses the development viewer normal material when no color is supplied', () => {
    expect(materialForColor(null)).toBeInstanceOf(THREE.MeshNormalMaterial);
  });

  it('keeps the standard material for an explicit color', () => {
    expect(materialForColor('#cc4444')).toBeInstanceOf(
      THREE.MeshStandardMaterial,
    );
  });
});

describe('WidgetTree targeted updates', () => {
  it('uses model path and mtime together as geometry identity', async () => {
    const tree = new WidgetTree(root([leaf()]), '/build/');
    await tree.loaded;
    loadAsync.mockClear();

    await tree.reconcile(root([leaf()]), '/build/');
    expect(loadAsync).not.toHaveBeenCalled();

    await tree.reconcile(root([leaf({ mtime: 2 })]), '/build/');
    await tree.reconcile(root([leaf({ model: 'other.stl', mtime: 2 })]), '/build/');
    expect(loadAsync.mock.calls.map(([url]) => url)).toEqual([
      '/build/leaf.stl', '/build/other.stl',
    ]);
  });

  it('replaces only the named artifact and leaves an unknown path alone', async () => {
    const tree = new WidgetTree(root([leaf(), leaf({ name: 'other', model: 'other.stl' })]), '/build/');
    await tree.loaded;
    const otherGroup = tree.children[1].group;
    loadAsync.mockClear();

    await tree.artifactChanged('leaf.stl', '/build/');
    await tree.artifactChanged('missing.stl', '/build/');

    expect(loadAsync.mock.calls.map(([url]) => url)).toEqual(['/build/leaf.stl']);
    expect(tree.children[1].group).toBe(otherGroup);
  });

  it('keeps the old tree when fetching a changed document mesh fails', async () => {
    const tree = new WidgetTree(root([leaf()]), '/build/');
    await tree.loaded;
    const previous = tree.children[0].group;
    loadAsync.mockRejectedValueOnce(new Error('network down'));

    await expect(tree.reconcile(root([leaf({ mtime: 2 })]), '/build/'))
      .rejects.toThrow('network down');
    expect(tree.children[0].group).toBe(previous);
  });

  it('does not partially update siblings when one replacement fails', async () => {
    const tree = new WidgetTree(root([
      leaf(), leaf({ name: 'other', model: 'other.stl' }),
    ]), '/build/');
    await tree.loaded;
    const first = tree.children[0].group;
    const second = tree.children[1].group;
    loadAsync.mockResolvedValueOnce(new THREE.BoxGeometry());
    loadAsync.mockRejectedValueOnce(new Error('second failed'));

    await expect(tree.reconcile(root([
      leaf({ mtime: 2 }), leaf({ name: 'other', model: 'other.stl', mtime: 2 }),
    ]), '/build/')).rejects.toThrow('second failed');
    expect(tree.children[0].group).toBe(first);
    expect(tree.children[1].group).toBe(second);
  });

  it('does not refetch a manifest reconcile that follows an artifact update for the same artifact', async () => {
    const tree = new WidgetTree(root([leaf()]), '/build/');
    await tree.loaded;
    loadAsync.mockClear();

    await tree.artifactChanged('leaf.stl', '/build/');
    expect(loadAsync).toHaveBeenCalledTimes(1);
    loadAsync.mockClear();

    await tree.reconcile(root([leaf({ mtime: 2 })]), '/build/');
    expect(loadAsync).not.toHaveBeenCalled();
  });

  it('reconciles structure and operations without refetching unchanged geometry', async () => {
    const tree = new WidgetTree(root([leaf()]), '/build/');
    await tree.loaded;
    const retained = tree.children[0].group;
    loadAsync.mockClear();

    await tree.reconcile(root([
      leaf({ operations: [['t', ['1', '0', '0']] as const] }),
      leaf({ name: 'added', model: 'added.stl' }),
    ]), '/build/');

    expect(tree.children[0].group).toBe(retained);
    expect(tree.children[0].operations).toEqual([['t', ['1', '0', '0']]]);
    expect(loadAsync.mock.calls.map(([url]) => url)).toEqual(['/build/added.stl']);
  });
});

describe('WidgetTree assembly navigation', () => {
  it('exposes stable paths and effective inherited colours', async () => {
    const tree = new WidgetTree({
      name: 'root', type: 'assembly', color: '#336699', operations: [],
      children: [
        {
          name: 'arm', type: 'assembly', color: null, operations: [],
          children: [leaf({ name: 'pin', color: null })],
        },
      ],
    }, '/build/');
    await tree.loaded;

    expect(tree.assembly()).toEqual({
      name: 'root', path: [], color: '#336699', model: false,
      children: [{
        name: 'arm', path: ['arm'], color: '#336699', model: false,
        children: [{
          name: 'pin', path: ['arm', 'pin'], color: '#336699', model: true,
          children: [],
        }],
      }],
    });
  });

  it('validates node paths and filters the rendered tree by focus and visibility', async () => {
    const tree = new WidgetTree(root([
      leaf({ name: 'left', model: 'left.stl' }),
      leaf({ name: 'right', model: 'right.stl' }),
    ]), '/build/');
    await tree.loaded;

    expect(tree.hasPath(['left'])).toBe(true);
    expect(tree.hasPath(['missing'])).toBe(false);
    expect(() => tree.requirePath(['missing'])).toThrow('Unknown assembly path: missing');

    tree.applyVisibility(['left'], new Set());
    expect(tree.group.visible).toBe(true);
    expect(tree.children[0].group.visible).toBe(true);
    expect(tree.children[1].group.visible).toBe(false);

    tree.applyVisibility(null, new Set([assemblyPathKey(['left'])]));
    expect(tree.children[0].group.visible).toBe(false);
    expect(tree.children[1].group.visible).toBe(true);
  });

  it('hides geometry owned by focus ancestors while retaining their transforms', async () => {
    const tree = new WidgetTree({
      ...root([
        leaf({ name: 'left', model: 'left.stl' }),
        leaf({ name: 'right', model: 'right.stl' }),
      ]),
      model: 'root.stl',
      mtime: 1,
    }, '/build/');
    await tree.loaded;

    tree.applyVisibility(['left'], new Set());

    const rootMesh = tree.group.children.find(
      (child): child is THREE.Mesh => child instanceof THREE.Mesh,
    );
    const leftMesh = tree.children[0].group.children.find(
      (child): child is THREE.Mesh => child instanceof THREE.Mesh,
    );
    expect(tree.group.visible).toBe(true);
    expect(rootMesh?.visible).toBe(false);
    expect(leftMesh?.visible).toBe(true);
    expect(tree.children[1].group.visible).toBe(false);
  });

  it('keeps a shown child occluded while its ancestor remains hidden', async () => {
    const tree = new WidgetTree(root([{
      name: 'arm', type: 'assembly', color: null, operations: [],
      children: [leaf({ name: 'pin' })],
    }]), '/build/');
    await tree.loaded;

    tree.applyVisibility(null, new Set([assemblyPathKey(['arm'])]));
    expect(tree.children[0].group.visible).toBe(false);
    expect(tree.children[0].children[0].group.visible).toBe(true);
  });
});

// ADR-056 stage 3b: which operations recompute is decided by the FREE
// VARIABLES of their parsed expressions (design D2), not by whether the
// raw string contains `$t`. A driver change must re-evaluate exactly the
// operations that name that driver, and nothing else -- that bound is
// what makes per-driver interactivity cheap on a large tree.
describe('WidgetTree driver-aware updates', () => {
  const STATIC = '90';
  const X_TERM = '(x_axis.motor * 0.0125)';
  const Y_TERM = '(y_axis.motor * 0.0125)';
  const SPIN = '(360.0 * $t)';
  const MIXED = '((5.0 * cos((360.0 * $t))) + ((x_axis.motor * 0.0125) * 0.1))';

  const machine = (): ManifestNode => root([
    leaf({ name: 'frame', operations: [['r', STATIC, [0, 0, 1]] as const] }),
    leaf({ name: 'x', operations: [['t', [X_TERM, '0', '0']] as const] }),
    leaf({ name: 'y', operations: [['t', [Y_TERM, '0', '0']] as const] }),
    leaf({ name: 'spin', operations: [['r', SPIN, [0, 0, 1]] as const] }),
    leaf({ name: 'cover', operations: [['t', [MIXED, '0', '0']] as const] }),
  ]);

  const scope = (time: number, x: number, y: number) => ({
    time, drivers: { x_axis: { motor: x }, y_axis: { motor: y } },
  });

  const mounted = async () => {
    const tree = new WidgetTree(machine(), '/build/');
    await tree.loaded;
    tree.update(scope(0, 8000, 2000));
    (evalExpr as unknown as ReturnType<typeof vi.fn>).mockClear();
    return tree;
  };

  it('re-evaluates only the operations naming a changed driver', async () => {
    const tree = await mounted();

    tree.update(scope(0, 1600, 2000),
                { time: false, drivers: new Set(['x_axis.motor']) });

    expect(evaluations()).toContain(X_TERM);
    expect(evaluations()).toContain(MIXED);
    expect(evaluations()).not.toContain(Y_TERM);
    expect(evaluations()).not.toContain(SPIN);
    expect(evaluations()).not.toContain(STATIC);
  });

  it('moves the carriage to the pose the new driver value implies', async () => {
    const tree = await mounted();

    tree.update(scope(0, 1600, 2000),
                { time: false, drivers: new Set(['x_axis.motor']) });

    expect(tree.children[1].group.matrix.elements[12]).toBeCloseTo(20);
    expect(tree.children[2].group.matrix.elements[12]).toBeCloseTo(25);
  });

  it('keeps animating $t operations from the time transport', async () => {
    const tree = await mounted();

    tree.update(scope(0.25, 8000, 2000),
                { time: true, drivers: new Set() });

    expect(evaluations()).toContain(SPIN);
    expect(evaluations()).toContain(MIXED);
    expect(evaluations()).not.toContain(X_TERM);
    expect(evaluations()).not.toContain(STATIC);
  });

  it('recomputes everything when nothing is named as changed', async () => {
    const tree = await mounted();

    tree.update(scope(0.25, 1600, 2000));

    expect(evaluations()).toContain(STATIC);
    expect(evaluations()).toContain(X_TERM);
    expect(evaluations()).toContain(Y_TERM);
  });

  it('reads `animated` off the parsed tree, not a substring', async () => {
    const timeDriven = new WidgetTree(machine(), '/build/');
    const driverOnly = new WidgetTree(root([
      leaf({ name: 'x', operations: [['t', [X_TERM, '0', '0']] as const] }),
    ]), '/build/');
    await Promise.all([timeDriven.loaded, driverOnly.loaded]);

    // A driver-driven document has no timeline to scrub: `animated` is
    // about the `$t` transport, and `x_axis.motor` is not it.
    expect(timeDriven.animated).toBe(true);
    expect(driverOnly.animated).toBe(false);
  });

  it('forgets a node\'s free variables when its operations are replaced', async () => {
    const tree = await mounted();

    await tree.reconcile(root([
      leaf({ name: 'frame', operations: [['t', [X_TERM, '0', '0']] as const] }),
    ]), '/build/');
    (evalExpr as unknown as ReturnType<typeof vi.fn>).mockClear();

    tree.update(scope(0, 1600, 2000),
                { time: false, drivers: new Set(['x_axis.motor']) });

    expect(evaluations()).toContain(X_TERM);
  });
});
