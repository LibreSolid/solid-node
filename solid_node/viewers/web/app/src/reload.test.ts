/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// Unlike node.test.ts's STLLoader mock (a no-op that never resolves),
// this suite needs to fire STL callbacks at will, at arbitrary points
// in a reload sequence, to reproduce the orphan races in
// improvements.md #24. Every stlLoader.load() call is recorded instead
// of resolved immediately.
type PendingLoad = {
  url: string;
  onLoad: (geometry: unknown) => void;
};

let mockPendingLoads: PendingLoad[] = [];

jest.mock('three/examples/jsm/loaders/STLLoader', () => ({
  STLLoader: class {
    load(url: string, onLoad: (geometry: unknown) => void) {
      mockPendingLoads.push({ url, onLoad });
    }
  },
}));

import * as THREE from 'three';
import { loadNode, Context } from './node';

// A minimal THREE.Scene stand-in with real add/remove/children semantics
// (the code under test calls scene.children.length, scene.remove(), and
// scene.add() directly), so mesh counts can be asserted exactly.
const makeScene = () => {
  const children: THREE.Object3D[] = [];
  return {
    add: (obj: THREE.Object3D) => {
      children.push(obj);
    },
    remove: (obj: THREE.Object3D) => {
      const idx = children.indexOf(obj);
      if (idx >= 0) children.splice(idx, 1);
    },
    children,
  } as unknown as THREE.Scene;
};

const makeContext = (scene: THREE.Scene): Context => ({
  time: 0,
  scene,
  setError: () => {},
});

const mockFetchResponses = (responses: Record<string, unknown>) => {
  (global as any).fetch = jest.fn((input: any) => {
    const url = input.toString();
    const key = Object.keys(responses)
      .filter((k) => url.startsWith(k))
      .sort((a, b) => b.length - a.length)[0];
    if (key === undefined) {
      return Promise.reject(new Error(`Unexpected fetch url: ${url}`));
    }
    return Promise.resolve({
      json: () => Promise.resolve(responses[key]),
    });
  });
};

// Resolves a pending load with a real (empty) BufferGeometry, matching
// what STLLoader would hand to the onLoad callback.
const resolve = (load: PendingLoad) => load.onLoad(new THREE.BufferGeometry());

afterEach(() => {
  jest.resetAllMocks();
  mockPendingLoads = [];
});

describe('Node.reload (orphaned meshes, improvements.md #24)', () => {
  it('does not let a late callback from the replaced tree add a duplicate mesh (case a)', async () => {
    mockFetchResponses({
      '/node/': {
        type: 'AssemblyNode',
        name: 'Root',
        children: ['leaf1'],
        operations: [],
        mtime: 1,
        color: null,
      },
      '/node/leaf1/': {
        type: 'LeafNode',
        name: 'leaf1',
        model: 'leaf1.stl',
        operations: [],
        mtime: 1,
        color: null,
      },
    });

    const scene = makeScene();
    const context = makeContext(scene);
    const tree1 = await loadNode('/', context);
    expect(mockPendingLoads).toHaveLength(1); // tree1's leaf1 load, not yet resolved

    const tree1Load = mockPendingLoads[0];

    // Reload before tree1's leaf1 STL ever arrives.
    const tree2 = await tree1.reload();
    expect(tree2).toBeDefined();
    expect(mockPendingLoads).toHaveLength(2); // tree2's leaf1 load registered

    // The straggler: tree1's leaf1 STL finally arrives, after the swap.
    resolve(tree1Load);
    expect(scene.children).toHaveLength(0); // must NOT have been added

    // The current tree's own load arrives normally.
    resolve(mockPendingLoads[1]);
    expect(scene.children).toHaveLength(1); // exactly one mesh for the one leaf
  });

  it('does not register an extra load from the vestigial this.loadModel() call in reload() (case b)', async () => {
    // reload() is called on the node being replaced; exercise it
    // directly on a LeafNode (has its own model) to isolate the
    // vestigial call from the fresh tree's own construction load.
    mockFetchResponses({
      '/node/': {
        type: 'LeafNode',
        name: 'Root',
        model: 'root.stl',
        operations: [],
        mtime: 1,
        color: null,
      },
    });

    const scene = makeScene();
    const context = makeContext(scene);
    const root = await loadNode('/', context);
    expect(mockPendingLoads).toHaveLength(1); // root's own construction load

    await root.reload();

    // Expected: exactly one more load, from the replacement tree's own
    // LeafNode construction. The vestigial this.loadModel() call at the
    // top of reload() registers a second, extraneous load for `root`
    // itself (a node that is about to be discarded).
    expect(mockPendingLoads).toHaveLength(2);
  });

  it('resolves two overlapping reloads, interleaved out of order, to exactly one mesh (case c)', async () => {
    mockFetchResponses({
      '/node/': {
        type: 'AssemblyNode',
        name: 'Root',
        children: ['leaf1'],
        operations: [],
        mtime: 1,
        color: null,
      },
      '/node/leaf1/': {
        type: 'LeafNode',
        name: 'leaf1',
        model: 'leaf1.stl',
        operations: [],
        mtime: 1,
        color: null,
      },
    });

    const scene = makeScene();
    const context = makeContext(scene);
    const tree1 = await loadNode('/', context);
    // Settle the initial tree so the scene starts from a clean, known
    // baseline of exactly one mesh.
    resolve(mockPendingLoads[0]);
    expect(scene.children).toHaveLength(1);
    mockPendingLoads = [];

    // Two reloads fired back-to-back — exactly the overlap a
    // websocket "reload" message racing a reconnect heal produces.
    const reloadAPromise = tree1.reload();
    const reloadBPromise = tree1.reload();
    const [treeA, treeB] = await Promise.all([reloadAPromise, reloadBPromise]);

    expect(treeA).toBeDefined();
    expect(treeB).toBeDefined();

    // Each reload registered its own leaf1 load.
    expect(mockPendingLoads).toHaveLength(2);

    // Resolve out of order: the load that was registered FIRST resolves
    // LAST, exactly the interleaving that produced the user's doubled
    // con_rods (the heaviest STL's fetch was still in flight when an
    // overlapping reload's clear landed).
    resolve(mockPendingLoads[1]);
    resolve(mockPendingLoads[0]);

    expect(scene.children).toHaveLength(1); // exactly one mesh, not two
  });
});
