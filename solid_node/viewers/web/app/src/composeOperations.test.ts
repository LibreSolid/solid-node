/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// jsdom has no WebGL and CRA's jest can't parse the ESM sources under
// three/examples/jsm, so STLLoader is replaced with a no-op stand-in.
// (composeOperations is a pure function, but it lives in node.ts, which
// imports STLLoader at module scope.)
jest.mock('three/examples/jsm/loaders/STLLoader', () => ({
  STLLoader: class {
    load(_url: string, _onLoad: (geometry: unknown) => void) {
      // no-op: never invokes onLoad, so no THREE.Mesh/geometry is needed
    }
  },
}));

import * as THREE from 'three';
import { composeOperations } from './node';
import { evaluate } from './evaluator';
import { Operation } from './operations.d';

// Extracts the world position of a mesh's local origin (0,0,0) from a
// composed matrix — the point every leaf model is authored around.
const originOf = (matrix: THREE.Matrix4): THREE.Vector3 =>
  new THREE.Vector3().setFromMatrixPosition(matrix);

describe('composeOperations', () => {
  it('matches the backend for the v8-engine increment-5 piston chain at t=0 (canonical fixture)', () => {
    // Exactly as served by the backend for a piston leaf: level 0 is the
    // piston's own kinematic translation along its axis; level 1 is the
    // CylinderUnit assembly's 45-degree bank rotation about the world X
    // axis, followed by the assembly's placement translation.
    const level0 = evaluate(
      [
        [
          't',
          [
            '0',
            '0',
            '((15.0 * cos((((720.0 * $t) + 45.0) + -45.0))) + sqrt((3600.0 - ((15.0 * sin((((720.0 * $t) + 45.0) + -45.0))) ^ 2))))',
          ],
        ],
      ],
      0,
    );
    const level1 = evaluate(
      [
        ['r', '45.0', [1, 0, 0]],
        ['t', ['-5.2', '0', '0']],
      ],
      0,
    );

    const matrix = composeOperations([level0, level1]);
    const origin = originOf(matrix);

    expect(origin.x).toBeCloseTo(-5.2, 9);
    expect(origin.y).toBeCloseTo(-53.0330085889911, 9);
    expect(origin.z).toBeCloseTo(53.0330085889911, 9);
  });

  it('matches the backend for the same chain at t=0.25 (height drops from 75 to 45)', () => {
    const level0 = evaluate(
      [
        [
          't',
          [
            '0',
            '0',
            '((15.0 * cos((((720.0 * $t) + 45.0) + -45.0))) + sqrt((3600.0 - ((15.0 * sin((((720.0 * $t) + 45.0) + -45.0))) ^ 2))))',
          ],
        ],
      ],
      0.25,
    );
    const level1 = evaluate(
      [
        ['r', '45.0', [1, 0, 0]],
        ['t', ['-5.2', '0', '0']],
      ],
      0.25,
    );

    const matrix = composeOperations([level0, level1]);
    const origin = originOf(matrix);

    expect(origin.x).toBeCloseTo(-5.2, 9);
    expect(origin.y).toBeCloseTo(-31.8198051533946, 9);
    expect(origin.z).toBeCloseTo(31.8198051533946, 9);
  });

  it('is order-sensitive: [t then r] and [r then t] of the same pair produce different results', () => {
    // Same pair of ops, opposite order within a single level.
    const translateThenRotate: Operation[][] = [
      [
        ['t', [1, 0, 0]],
        ['r', 90, [0, 0, 1]],
      ],
    ];
    const rotateThenTranslate: Operation[][] = [
      [
        ['r', 90, [0, 0, 1]],
        ['t', [1, 0, 0]],
      ],
    ];

    const originA = originOf(composeOperations(translateThenRotate));
    const originB = originOf(composeOperations(rotateThenTranslate));

    // [t, r]: translate to (1,0,0), then the later rotation (outermost)
    // carries that translated point around the world Z axis.
    expect(originA.x).toBeCloseTo(0, 9);
    expect(originA.y).toBeCloseTo(1, 9);
    expect(originA.z).toBeCloseTo(0, 9);

    // [r, t]: rotation applies to the origin first (no visible effect,
    // since a rotation about the origin doesn't move the origin), then
    // the later translation (outermost) places it directly.
    expect(originB.x).toBeCloseTo(1, 9);
    expect(originB.y).toBeCloseTo(0, 9);
    expect(originB.z).toBeCloseTo(0, 9);

    expect([originA.x, originA.y, originA.z]).not.toEqual([
      originB.x,
      originB.y,
      originB.z,
    ]);
  });

  it('rotates an already-translated child about the world origin (assembly-level rotate above a placed child)', () => {
    // A lone rotation level sitting above an already-translated child
    // (level 0): the CylinderUnit shape. The rotation must carry the
    // child's position around the world origin, not leave it in place.
    const operations: Operation[][] = [
      [['t', [10, 0, 0]]],
      [['r', 90, [0, 0, 1]]],
    ];

    const origin = originOf(composeOperations(operations));

    expect(origin.x).toBeCloseTo(0, 9);
    expect(origin.y).toBeCloseTo(10, 9);
    expect(origin.z).toBeCloseTo(0, 9);

    // Explicitly not the untouched translated position — that was the bug:
    // the old position.add + applyQuaternion left the position at (10,0,0).
    expect(origin.x).not.toBeCloseTo(10, 6);
  });

  it('preserves existing green behavior: a leaf-only [own-axis rotation, placement translation] chain', () => {
    // The increments-1..4 pattern: every rotation precedes every
    // translation within the single leaf level, so old and new semantics
    // agree here — this must keep matching numerically.
    const operations: Operation[][] = [
      [
        ['r', 30, [0, 1, 0]],
        ['t', [2, 3, 4]],
      ],
    ];

    const origin = originOf(composeOperations(operations));

    // A rotation about the world origin doesn't move the origin itself,
    // so the subsequent translation lands the mesh origin exactly at the
    // translation vector, regardless of the rotation angle.
    expect(origin.x).toBeCloseTo(2, 9);
    expect(origin.y).toBeCloseTo(3, 9);
    expect(origin.z).toBeCloseTo(4, 9);
  });
});
