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

const stlLoader = new STLLoader();

export function materialForColor(color: string | null): THREE.Material {
  if (color === null) {
    return new THREE.MeshNormalMaterial();
  }
  return new THREE.MeshStandardMaterial({
    color: new THREE.Color(color),
    metalness: 0.1,
    roughness: 0.6,
  });
}

export class WidgetTree {
  group: THREE.Group;
  operations: RawOperation[];
  children: WidgetTree[];
  name: string;
  private model: string | undefined;
  private mtime: number | undefined;
  private color: string | null;

  // Resolves when this node's mesh (if any) and all descendants
  // finished loading, so the camera can be fit to the actual bounds.
  loaded: Promise<void>;

  constructor(data: ManifestNode, baseUrl: string,
              inheritedColor: string | null = null) {
    this.group = new THREE.Group();
    this.group.matrixAutoUpdate = false;
    this.name = data.name;
    this.operations = data.operations;
    this.children = [];

    const color = data.color ?? inheritedColor;
    this.color = color;
    this.model = data.model;
    this.mtime = data.mtime;
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
    this.group.add(await loadMesh(url, color));
  }

  /** Replace every mesh that names this artifact.  Unknown artifacts are
   * deliberately harmless: a manifest update is authoritative for removals. */
  async artifactChanged(path: string, baseUrl: string): Promise<void> {
    const replacements: Array<{ tree: WidgetTree; mesh: THREE.Mesh }> = [];
    const collect = (node: WidgetTree) => {
      if (node.model === path) {
        replacements.push({ tree: node, mesh: undefined as unknown as THREE.Mesh });
      }
      node.children.forEach(collect);
    };
    collect(this);
    await Promise.all(replacements.map(async (replacement) => {
      replacement.mesh = await loadMesh(baseUrl + path, replacement.tree.color);
    }));
    replacements.forEach(({ tree, mesh }) => tree.replaceMesh(mesh));
  }

  /** Fetch every stale mesh before changing the live tree.  This makes a
   * rejected document update leave the previously rendered scene intact. */
  async reconcile(data: ManifestNode, baseUrl: string,
                  inheritedColor: string | null = null): Promise<void> {
    const apply = await this.prepareReconcile(data, baseUrl, inheritedColor);
    apply();
  }

  private async prepareReconcile(data: ManifestNode, baseUrl: string,
                                 inheritedColor: string | null): Promise<() => void> {
    const nextColor = data.color ?? inheritedColor;
    const modelChanged = this.model !== data.model || this.mtime !== data.mtime;
    const replacement = data.model && modelChanged
      ? await loadMesh(baseUrl + data.model, nextColor) : undefined;

    const existing = uniqueByName(this.children);
    const incoming = uniqueDataByName(data.children ?? []);
    const nextChildren = await Promise.all((data.children ?? []).map(async (childData) => {
      const child = existing.get(childData.name);
      if (!child || !incoming.has(childData.name)) {
        const created = new WidgetTree(childData, baseUrl, nextColor);
        await created.loaded;
        return { tree: created, apply: () => undefined };
      }
      return {
        tree: child,
        apply: await child.prepareReconcile(childData, baseUrl, nextColor),
      };
    }));

    return () => {
      // All nested fetches succeeded.  Only now is it safe to mutate the
      // live tree, including its children.
      nextChildren.forEach((child) => child.apply());
      if (replacement) {
        this.replaceMesh(replacement);
      } else if (!data.model && this.model) {
        this.removeMesh();
      }
      this.name = data.name;
      this.model = data.model;
      this.mtime = data.mtime;
      this.operations = data.operations;
      this.setColor(nextColor);

      const retained = new Set(nextChildren.map((child) => child.tree));
      this.children.filter((child) => !retained.has(child)).forEach((child) => {
        this.group.remove(child.group);
        child.dispose();
      });
      this.children = nextChildren.map((child) => child.tree);
      this.children.forEach((child) => {
        this.group.remove(child.group);
        this.group.add(child.group);
      });
    };
  }

  private replaceMesh(mesh: THREE.Mesh): void {
    this.removeMesh();
    this.group.add(mesh);
  }

  private removeMesh(): void {
    this.group.children.filter((child): child is THREE.Mesh => child instanceof THREE.Mesh)
      .forEach((mesh) => {
        this.group.remove(mesh);
        mesh.geometry.dispose();
        const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
        materials.forEach((material) => material.dispose());
      });
  }

  private setColor(color: string | null): void {
    if (this.color === color) return;
    this.color = color;
    this.group.children.filter((child): child is THREE.Mesh => child instanceof THREE.Mesh)
      .forEach((mesh) => {
        const previous = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
        mesh.material = materialForColor(color);
        previous.forEach((material) => material.dispose());
      });
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

  dispose(): void {
    this.group.traverse((object) => {
      if (!(object instanceof THREE.Mesh)) {
        return;
      }
      object.geometry.dispose();
      const materials = Array.isArray(object.material)
        ? object.material : [object.material];
      materials.forEach((material) => material.dispose());
    });
  }
}

async function loadMesh(url: string, color: string | null): Promise<THREE.Mesh> {
  const geometry = await stlLoader.loadAsync(url);
  geometry.computeVertexNormals();
  return new THREE.Mesh(geometry, materialForColor(color));
}

function uniqueByName(children: WidgetTree[]): Map<string, WidgetTree> {
  const names = new Map<string, WidgetTree>();
  const duplicate = new Set<string>();
  children.forEach((child) => names.has(child.name)
    ? duplicate.add(child.name) : names.set(child.name, child));
  duplicate.forEach((name) => names.delete(name));
  return names;
}

function uniqueDataByName(children: ManifestNode[]): Set<string> {
  const seen = new Set<string>();
  const duplicate = new Set<string>();
  children.forEach((child) => seen.has(child.name)
    ? duplicate.add(child.name) : seen.add(child.name));
  duplicate.forEach((name) => seen.delete(name));
  return seen;
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
