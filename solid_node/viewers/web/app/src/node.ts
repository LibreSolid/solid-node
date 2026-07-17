/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

import * as THREE from 'three';
import {
  RawOperation,
  Operation,
} from './operations.d';
import { evaluate } from './evaluator';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader';

type SetErrorType = React.Dispatch<React.SetStateAction<string>>;

export interface Context {
  time: number;
  scene: THREE.Scene;
  setError: SetErrorType;
}

interface NodeData {
  type: string;
  name: string;
  model?: string;
  children?: string[];
  mtime: number;
  operations: RawOperation[];
  color: string;
}

const stlLoader = new STLLoader();

// Composes a node's flattened operation chain into a single absolute
// world matrix. `operations` is indexed level 0 first (the node's own
// ops), then each ancestor's ops at deeper levels — exactly the shape
// Node.operations holds after setOperations cascades down the tree.
// Every rotation is about the world axis through the origin; every
// translation is a world translation; later operations are outermost:
// world = M_opk · … · M_op1 (each op premultiplied, in encounter order).
export const composeOperations = (operations: Operation[][]): THREE.Matrix4 => {
  const matrix = new THREE.Matrix4();
  const opMatrix = new THREE.Matrix4();

  for (const level of operations) {
    for (const op of level) {
      if (op[0] === "r") {
        const ax = op[2];
        const axis = new THREE.Vector3(ax[0], ax[1], ax[2]).normalize();
        opMatrix.makeRotationAxis(axis, op[1] * Math.PI / 180);
      } else {
        const v = op[1];
        opMatrix.makeTranslation(v[0], v[1], v[2]);
      }
      matrix.premultiply(opMatrix);
    }
  }

  return matrix;
}

export abstract class Node {
  // A string matching the subclass name
  type: string;

  // The name identifying this node for its parent
  name: string;

  // The name of all parents joined by /
  path: string;

  // Model is the path of the mesh
  model?: string;
  mesh?: THREE.Mesh;

  children: Node[];
  context: Context;

  mtime: number;

  color: string;

  // Operations matrix.
  // Each layer of the tree has a list of operations
  // rawOperations contains functions (can use $t or any variable)
  // operations contains evaluated function results
  rawOperations: RawOperation[][];
  operations: Operation[][];

  constructor(type: string, path: string, data: NodeData, context: Context) {
    this.type = type;
    this.path = path;
    this.name = data.name;
    this.mtime = data.mtime;
    this.context = context;
    this.children = [];
    this.rawOperations = [];
    this.operations = [];
    this.color = data.color;
  }

  setOperations(op: RawOperation[], level: number = 0) {
    this.rawOperations[level] = op;
    this.operations[level] = evaluate(op, this.context.time);
    for (const child of this.children) {
      child.setOperations(op, level + 1);
    }
  }

  setContext(context: Context) {
    this.context = context;

    for (const child of this.children) {
      child.setContext(context);
    }

    this.setOperations(this.rawOperations[0]);
    this.applyOperations();
  }

  async reload(): Promise<Node | undefined> {
    this.loadModel();
    try {
      const nodeData = await loadNodeData(this.path);
      const scene = this.context.scene;
      while(scene.children.length > 0) {
	scene.remove(scene.children[0]);
      }
      return await loadNode(this.path, this.context);
    } catch (e) {
      return undefined;
    }
  }

  loadModel() {
    if (!this.model)
      return;
    const tstamp = new Date().getTime(); // avoid cache

    stlLoader.load(`/node${this.path}${this.model}?t=${tstamp}`, (geometry) => {
      // TODO use this.color to colorize node
      const material = new THREE.MeshNormalMaterial();
      const mesh = new THREE.Mesh(geometry, material);
      if (this.context.scene) {
        if (this.mesh) {
          this.context.scene.remove(this.mesh);
        }
        this.context.scene.add(mesh);
      }
      this.mesh = mesh;
      this.applyOperations();
    });

  }

  applyOperations() {
    if (!this.model) {
      for (const child of this.children) {
        child.applyOperations();
      }
    }
    if (!this.mesh) {
      return;  // not loaded yet
    }
    // Absolute composition: recomputed from scratch from this.operations
    // every time, so redundant calls (setContext recurses into every
    // node, which then also re-triggers its subtree) are idempotent —
    // no undo/reapply bookkeeping needed.
    this.mesh.matrixAutoUpdate = false;
    this.mesh.matrix.copy(composeOperations(this.operations));
    this.mesh.matrixWorldNeedsUpdate = true;
  }
}

abstract class InternalNode extends Node {
  children: Node[];

  constructor(type: string, path: string, data: NodeData, children: Node[], context: Context) {
    super(type, path, data, context);
    this.children = children;
  }
}


export class FusionNode extends InternalNode {
  constructor(path: string, data: NodeData, children: Node[], context: Context) {
    super("FusionNode", path, data, children, context);
    this.model = data.model;
    this.loadModel();
  }
}


export class AssemblyNode extends InternalNode {
  constructor(path: string, data: NodeData, children: Node[], context: Context) {
    super("AssemblyNode", path, data, children, context);
  }
}


export class LeafNode extends Node {

  constructor(path: string, data: NodeData, context: Context) {
    super("LeafNode", path, data, context);
    this.model = data.model;
    this.loadModel();
  }

}

export const loadRoot = async (context: Context): Promise<Node> => {
  return loadNode('/', context);
}

const loadNodeData = async (path: string): Promise<NodeData> => {
  const tstamp = new Date().getTime(); // avoid cache
  const response = await fetch(`/node${path}?t=${tstamp}`);
  return await response.json() as NodeData;
}

// Factory function
export const loadNode = async (path: string, context: Context): Promise<Node> => {
  const data = await loadNodeData(path);
  let node: Node | undefined;

  if (data.type === "LeafNode") {
    node = new LeafNode(path, data, context);
  } else {
    // NodeAPI.state() (viewer.py) omits "children" entirely for any rigid
    // node (not just LeafNode), so it must not be assumed present here.
    const childrenPromises = (data.children ?? []).map((child: string) => {
      const childPath = `${path}${child}/`;
      return loadNode(childPath, context);
    });
    const children = await Promise.all(childrenPromises);
    if (data.type === "FusionNode") {
      node = new FusionNode(path, data, children, context);
    } else if (data.type === "AssemblyNode") {
      node = new AssemblyNode(path, data, children, context);
    }
  }

  if (!node) {
    throw new Error("Invalid node type");
  }

  node.setOperations(data.operations);
  return node;
}
