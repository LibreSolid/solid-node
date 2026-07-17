/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// jsdom has no WebGL and CRA's jest can't parse the ESM sources under
// three/examples/jsm, so STLLoader is replaced with a no-op stand-in.
jest.mock('three/examples/jsm/loaders/STLLoader', () => ({
  STLLoader: class {
    load(_url: string, _onLoad: (geometry: unknown) => void) {
      // no-op: never invokes onLoad, so no THREE.Mesh/geometry is needed
    }
  },
}));

import * as THREE from 'three';
import { loadNode, Context, FusionNode, AssemblyNode, LeafNode } from './node';
import { evaluate } from './evaluator';

const makeContext = (): Context => ({
  time: 0,
  scene: { add() {}, remove() {}, children: [] } as any,
  setError: () => {},
});

// Maps a path prefix (as it appears in the fetched URL, e.g. "/node/child1/")
// to the JSON payload the backend would respond with for that node.
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

afterEach(() => {
  jest.resetAllMocks();
});

describe('loadNode', () => {
  it('loads a rigid FusionNode payload with no children key (B10)', async () => {
    // This is exactly the shape NodeAPI.state() returns for any rigid node
    // (viewer.py): no "children" key at all, only "model".
    mockFetchResponses({
      '/node/': {
        type: 'FusionNode',
        name: 'Frame',
        model: 'Frame.stl',
        operations: [],
        mtime: 1,
        color: null,
      },
    });

    const node = await loadNode('/', makeContext());

    expect(node).toBeInstanceOf(FusionNode);
    expect(node.model).toBe('Frame.stl');
    expect(node.children).toEqual([]);
  });

  it('loads a LeafNode payload (regression)', async () => {
    mockFetchResponses({
      '/node/': {
        type: 'LeafNode',
        name: 'Leaf',
        model: 'Leaf.stl',
        operations: [],
        mtime: 1,
        color: null,
      },
    });

    const node = await loadNode('/', makeContext());

    expect(node).toBeInstanceOf(LeafNode);
    expect(node.model).toBe('Leaf.stl');
    expect(node.children).toEqual([]);
  });

  it('loads an AssemblyNode with children (regression)', async () => {
    mockFetchResponses({
      '/node/': {
        type: 'AssemblyNode',
        name: 'Root',
        children: ['child1'],
        operations: [],
        mtime: 1,
        color: null,
      },
      '/node/child1/': {
        type: 'LeafNode',
        name: 'child1',
        model: 'child1.stl',
        operations: [],
        mtime: 1,
        color: null,
      },
    });

    const node = await loadNode('/', makeContext());

    expect(node).toBeInstanceOf(AssemblyNode);
    expect(node.children).toHaveLength(1);
    expect(node.children[0]).toBeInstanceOf(LeafNode);
    expect(node.children[0].model).toBe('child1.stl');
  });
});

// Reads the world position of a mesh's local origin however the current
// application strategy exposes it: the new absolute-matrix strategy sets
// mesh.matrix directly (matrixAutoUpdate = false) and never touches
// mesh.position; the old incremental strategy never touched mesh.matrix
// and only ever mutated mesh.position (rotation, applied via
// applyQuaternion, does not move position). This lets the same
// assertion serve as the red demonstration against the old code and the
// regression pin against the new code.
const meshOrigin = (mesh: THREE.Mesh): THREE.Vector3 => {
  if (mesh.matrixAutoUpdate === false) {
    return new THREE.Vector3().setFromMatrixPosition(mesh.matrix);
  }
  return mesh.position.clone();
};

describe('applyOperations (order-faithful matrix composition, improvements.md #23)', () => {
  it('places the v8-engine increment-5 piston chain at the correct world position, not the pre-rotation translation', async () => {
    // The CylinderUnit shape: a leaf (piston) with its own kinematic
    // translation (level 0), sitting under an assembly that rotates 45
    // degrees about the world X axis and then translates into place
    // (level 1). This is the exact chain that broke the old browser
    // renderer: it rose the piston vertically then rotated it in place
    // instead of carrying it onto the 45-degree bank.
    mockFetchResponses({
      '/node/': {
        type: 'LeafNode',
        name: 'Piston',
        model: 'Piston.stl',
        mtime: 1,
        color: null,
        operations: [
          [
            't',
            [
              '0',
              '0',
              '((15.0 * cos((((720.0 * $t) + 45.0) + -45.0))) + sqrt((3600.0 - ((15.0 * sin((((720.0 * $t) + 45.0) + -45.0))) ^ 2))))',
            ],
          ],
        ],
      },
    });

    const node = await loadNode('/', makeContext());
    // STLLoader is mocked as a no-op, so no mesh was ever loaded via
    // loadModel(); attach one directly and cascade the ancestor's
    // (level 1) operations the way the real assembly tree would.
    node.mesh = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1));
    node.setOperations(
      [
        ['r', '45.0', [1, 0, 0]],
        ['t', ['-5.2', '0', '0']],
      ],
      1,
    );

    node.applyOperations();

    const origin = meshOrigin(node.mesh);
    expect(origin.x).toBeCloseTo(-5.2, 9);
    expect(origin.y).toBeCloseTo(-53.0330085889911, 9);
    expect(origin.z).toBeCloseTo(53.0330085889911, 9);
  });
});
