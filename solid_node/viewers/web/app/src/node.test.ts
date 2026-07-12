/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
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

import { loadNode, Context, FusionNode, AssemblyNode, LeafNode } from './node';

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
