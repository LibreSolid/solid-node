/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// A part whose GEOMETRY follows the machine, evaluated the way pose
// already is. Two claims carry the whole design and neither can be read
// off a screenshot, so both are asserted here:
//
//   * a driver move refills the buffers the node already owns -- the
//     Float32Array behind the position attribute is the SAME object and
//     the vertex count is unchanged, because molejo's tessellation is
//     declared by the document and never follows a parameter; and
//   * a driver named by no `params` expression of the node costs it
//     nothing, which is only visible by counting evaluations.
//
// The molejo evaluator is the real one, wrapped in a spy: the numbers
// must be molejo's, and what is watched is how often it is asked.

import * as THREE from 'three';
import { describe, expect, it, vi } from 'vitest';

vi.mock('molejo', async (importOriginal) => {
  const actual = await importOriginal<typeof import('molejo')>();
  return { ...actual, evaluate: vi.fn(actual.evaluate) };
});

import { evaluate } from 'molejo';
import { WidgetTree } from './tree';
import { ManifestFlexible, ManifestNode } from './types';

const evaluations = () =>
  (evaluate as unknown as ReturnType<typeof vi.fn>).mock.calls.length;

// `tests/flexible_project/spring.py` as the producer serializes it.
const SPRING_SPEC = {
  molejo: 1,
  profile: { type: 'circle', radius: 2.0 },
  path: [{ type: 'helix', radius: 14.0, turns: 6.5,
           height: { param: 'height' } }],
  loop: false,
  tessellation: { path: 240, profile: 16 },
};

// 240 segments on the single helix is 241 rings of 16, plus the two cap
// centres: a count the DOCUMENT fixes, which is the whole point.
const SPRING_VERTICES = 241 * 16 + 2;

const spring = (overrides: Partial<ManifestFlexible> = {},
                node: Partial<ManifestNode> = {}): ManifestNode => ({
  name: 'spring', type: 'LeafNode', color: null, operations: [],
  flexible: {
    tech: 'molejo', spec: SPRING_SPEC,
    params: { height: '(46.8 - valvetrain.lift)' },
    ...overrides,
  },
  ...node,
});

const engine = (children: ManifestNode[]): ManifestNode => ({
  name: 'engine', type: 'AssemblyNode', color: null, operations: [], children,
});

const scope = (lift: number, time = 0) => ({
  time, drivers: { valvetrain: { lift } },
});

const meshOf = (tree: WidgetTree): THREE.Mesh => {
  const mesh = tree.group.children.find(
    (child): child is THREE.Mesh => child instanceof THREE.Mesh,
  );
  if (!mesh) throw new Error('the flexible node mounted no mesh');
  return mesh;
};

const positionsOf = (mesh: THREE.Mesh): THREE.BufferAttribute =>
  mesh.geometry.getAttribute('position') as THREE.BufferAttribute;

// The count is cleared before the mount's own update, so `evaluations()`
// on a freshly mounted tree is what THAT tree cost and nothing carried
// over from the test before it.
const mounted = async (data: ManifestNode = engine([spring()]),
                       lift = 0) => {
  const tree = new WidgetTree(data, '/build/');
  await tree.loaded;
  (evaluate as unknown as ReturnType<typeof vi.fn>).mockClear();
  tree.update(scope(lift));
  return tree;
};

describe('a flexible node mounts geometry from its spec', () => {
  it('renders the spring at the driver defaults', async () => {
    const tree = await mounted();
    const mesh = meshOf(tree.children[0]);

    expect(positionsOf(mesh).count).toBe(SPRING_VERTICES);
    expect(mesh.geometry.getIndex()?.count).toBe(3 * 7712);
    // A coil of radius 14 swept by a wire of radius 2 is 32 across, and
    // stands the 46.8 its expression says at lift 0 plus the wire at
    // each end. A 16-sided profile is INSCRIBED in that wire, so both
    // extents land just inside the analytic ones and never outside.
    const box = mesh.geometry.boundingBox!;
    expect(box.max.x - box.min.x).toBeLessThanOrEqual(32);
    expect(box.max.x - box.min.x).toBeGreaterThan(31.9);
    expect(box.max.z - box.min.z).toBeLessThanOrEqual(46.8 + 4);
    expect(box.max.z - box.min.z).toBeGreaterThan(46.8 + 3.9);
  });

  it('inherits the colour its ancestors carry, like any other mesh', async () => {
    const tree = await mounted({ ...engine([spring()]), color: '#336699' });

    const material = meshOf(tree.children[0]).material as THREE.MeshStandardMaterial;
    expect(material).toBeInstanceOf(THREE.MeshStandardMaterial);
    expect(material.color.getHexString()).toBe('336699');
  });

  it('refuses a technology it cannot evaluate, naming node and tech', () => {
    expect(() => new WidgetTree(engine([spring({ tech: 'wibble' })]), '/build/'))
      .toThrow(/spring/);
    expect(() => new WidgetTree(engine([spring({ tech: 'wibble' })]), '/build/'))
      .toThrow(/wibble/);
  });

  it('takes part in the operations matrix like any other node', async () => {
    const tree = await mounted(engine([
      spring({}, { operations: [['t', ['(valvetrain.lift * 2.0)', '0', '0']]] }),
    ]), 3);

    expect(tree.children[0].group.matrix.elements[12]).toBeCloseTo(6);
  });
});

describe('flexible geometry is gated the way pose is', () => {
  it('refills the buffers it already owns when its driver moves', async () => {
    const tree = await mounted();
    const mesh = meshOf(tree.children[0]);
    const attribute = positionsOf(mesh);
    const array = attribute.array;
    const geometry = mesh.geometry;
    const before = Array.from(array.slice(0, 3 * 32));
    // `needsUpdate` is write-only on a BufferAttribute; the version it
    // bumps is what the renderer reads, so that is what is asserted.
    const version = attribute.version;

    tree.update(scope(12), { time: false, drivers: new Set(['valvetrain.lift']) });

    // Same geometry, same attribute, same backing array: nothing was
    // reallocated, and the index was never touched.
    expect(mesh.geometry).toBe(geometry);
    expect(positionsOf(mesh)).toBe(attribute);
    expect(positionsOf(mesh).array).toBe(array);
    expect(positionsOf(mesh).count).toBe(SPRING_VERTICES);
    expect(Array.from(array.slice(0, 3 * 32))).not.toEqual(before);
    expect(attribute.version).toBeGreaterThan(version);
  });

  it('leaves the spring alone when an unrelated driver moves', async () => {
    const tree = await mounted();
    expect(evaluations()).toBe(1);

    tree.update(scope(0), { time: false, drivers: new Set(['spindle.speed']) });

    expect(evaluations()).toBe(1);
  });

  it('leaves the spring alone when only time advanced', async () => {
    const tree = await mounted();
    expect(evaluations()).toBe(1);

    tree.update(scope(0, 0.25), { time: true, drivers: new Set() });

    expect(evaluations()).toBe(1);
  });

  it('animates a `$t` parameter under the time loop', async () => {
    const tree = await mounted(engine([
      spring({ params: { height: '(46.8 - (12.0 * $t))' } }),
    ]));
    const mesh = meshOf(tree.children[0]);
    const array = positionsOf(mesh).array;
    const before = Array.from(array.slice(0, 3 * 32));

    tree.update({ time: 0.5, drivers: {} }, { time: true, drivers: new Set() });

    expect(positionsOf(mesh).array).toBe(array);
    expect(Array.from(array.slice(0, 3 * 32))).not.toEqual(before);
  });

  it('reads `animated` off a `$t` parameter, and not off a driver one', async () => {
    const driven = new WidgetTree(engine([spring()]), '/build/');
    const timed = new WidgetTree(engine([
      spring({ params: { height: '(46.8 - (12.0 * $t))' } }),
    ]), '/build/');
    await Promise.all([driven.loaded, timed.loaded]);

    expect(timed.animated).toBe(true);
    expect(driven.animated).toBe(false);
  });

  it('re-evaluates a spring whose expressions a reconcile replaced', async () => {
    const tree = await mounted();
    const mesh = meshOf(tree.children[0]);
    const array = positionsOf(mesh).array;

    await tree.reconcile(engine([
      spring({ params: { height: '(46.8 - (2.0 * cam.angle))' } }),
    ]), '/build/');
    (evaluate as unknown as ReturnType<typeof vi.fn>).mockClear();
    tree.update({ time: 0, drivers: { cam: { angle: 3 } } },
                { time: false, drivers: new Set(['cam.angle']) });

    // The spec did not change, so the buffers did not either -- only
    // which inputs the node now watches.
    expect(evaluations()).toBe(1);
    expect(positionsOf(meshOf(tree.children[0])).array).toBe(array);
  });
});
