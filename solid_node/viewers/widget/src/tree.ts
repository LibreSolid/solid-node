/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// Mirrors the manifest tree as a three.js Group hierarchy. Each node's
// local matrix is recomputed from scratch from its evaluated operations
// on every time change (stateless per frame), and three.js composes
// ancestors naturally: world = ancestors' matrices * own matrix, the
// same composition as AbstractBaseNode.mesh (own operations first,
// then each ancestor's, up the tree).

import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import { ManifestNode, RawOperation } from './types';
import { evalExpr, isAnimated } from './evaluator';

const DEFAULT_COLOR = '#8899aa';

const stlLoader = new STLLoader();

export class WidgetTree {
  group: THREE.Group;
  operations: RawOperation[];
  children: WidgetTree[];

  // Resolves when this node's mesh (if any) and all descendants
  // finished loading, so the camera can be fit to the actual bounds.
  loaded: Promise<void>;

  constructor(data: ManifestNode, baseUrl: string,
              inheritedColor: string | null = null) {
    this.group = new THREE.Group();
    this.group.matrixAutoUpdate = false;
    this.operations = data.operations;
    this.children = [];

    const color = data.color ?? inheritedColor;
    const pending: Promise<void>[] = [];

    if (data.model) {
      pending.push(this.loadModel(baseUrl + data.model, color));
    }

    for (const childData of data.children ?? []) {
      const child = new WidgetTree(childData, baseUrl, color);
      this.children.push(child);
      this.group.add(child.group);
      pending.push(child.loaded);
    }

    this.loaded = Promise.all(pending).then(() => undefined);
  }

  private async loadModel(url: string, color: string | null): Promise<void> {
    const geometry = await stlLoader.loadAsync(url);
    geometry.computeVertexNormals();
    const material = new THREE.MeshStandardMaterial({
      color: new THREE.Color(color ?? DEFAULT_COLOR),
      metalness: 0.1,
      roughness: 0.6,
    });
    this.group.add(new THREE.Mesh(geometry, material));
  }

  get animated(): boolean {
    return (
      this.operations.some(operationIsAnimated) ||
      this.children.some((child) => child.animated)
    );
  }

  // Recompute every local matrix for animation time t (0..1)
  update(t: number): void {
    this.group.matrix.copy(operationsMatrix(this.operations, t));
    for (const child of this.children) {
      child.update(t);
    }
  }
}

function operationIsAnimated(op: RawOperation): boolean {
  if (op[0] === 'r') {
    return isAnimated(op[1]);
  }
  return op[1].some(isAnimated);
}

// Operations listed [op1, op2, ...] apply to the solid in order:
// v' = opN(...(op1(v))), i.e. matrix = M_opN * ... * M_op1
function operationsMatrix(ops: RawOperation[], t: number): THREE.Matrix4 {
  const matrix = new THREE.Matrix4();
  const step = new THREE.Matrix4();
  const axis = new THREE.Vector3();

  for (const op of ops) {
    if (op[0] === 'r') {
      const angle = evalExpr(op[1], t) * (Math.PI / 180);
      axis.set(op[2][0], op[2][1], op[2][2]).normalize();
      step.makeRotationAxis(axis, angle);
    } else {
      step.makeTranslation(
        evalExpr(op[1][0], t),
        evalExpr(op[1][1], t),
        evalExpr(op[1][2], t),
      );
    }
    matrix.premultiply(step);
  }
  return matrix;
}
