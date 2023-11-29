import * as THREE from 'three';
import {
  RawOperation,
  Operation,
} from './operations.d';
import { evaluate } from './evaluator';


interface Context {
  time: number;
}

export abstract class Node {
  // A string matching the subclass name
  type: string;

  // The name identifying this node for its parent
  name: string;
  // The path for the api, is based on name, not sure if necessary
  path: string;

  // Model is the path of the mesh
  model?: string;
  mesh?: THREE.Mesh;

  children: Node[];
  context: Context;

  // Operations matrix.
  // Each layer of the tree has a list of operations
  // rawOperations contains functions (can use $t or any variable)
  // operations contains evaluated function results
  rawOperations: RawOperation[][];
  operations: Operation[][];

  constructor(type: string, name: string, path: string, context: Context) {
    this.type = type;
    this.name = name;
    this.path = path;
    this.context = context;
    this.rawOperations = [];
    this.operations = [];
  }

  setOperations(op: RawOperation[], level: number = 0) {
    this.rawOperations[level] = op;
    this.operations[level] = evaluate(op, this.context.time);
    for (const child of this.children) {
      child.setOperations(op, level + 1);
    }
  }

  setTime(time: number) {
    this.context.time = time;
    this.unapplyOperations();
    this.applyOperations();
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
    for (const operations of this.operations) {
      for (const op of operations) {
        if (op[0] === "r") {
          const quaternion = new THREE.Quaternion();
          const ax = op[2];
          const axis = new THREE.Vector3(ax[0], ax[1], ax[2]);
          quaternion.setFromAxisAngle(axis, op[1] * Math.PI / 180)
          this.mesh.applyQuaternion(quaternion);
        }
        if (op[0] === "t") {
          const v = op[1];
          this.mesh.position.add(new THREE.Vector3(v[0], v[1], v[2]));
        }
      }
    }
  }

  unapplyOperations() {
    if (!this.model) {
      for (const child of this.children) {
        child.unapplyOperations();
      }
    }
    if (!this.mesh) {
      return;  // not loaded yet
    }
    // Iterate through the operations in reverse order,
    // then reverse all rotations and translations
    for (let j = this.operations.length - 1; j >= 0; j--) {
      const operations = this.operations[j];
      for (let i = operations.length - 1; i >= 0; i--) {
        const op = operations[i];

        if (op[0] === "r" && op[2]) {
          const quaternion = new THREE.Quaternion();
          const ax = op[2];
          const axis = new THREE.Vector3(ax[0], ax[1], ax[2]);

          quaternion.setFromAxisAngle(axis, -(op[1] as number) * Math.PI / 180);
          this.mesh.applyQuaternion(quaternion);
        }
        if (op[0] === "t") {
          const v = op[1] as number[];
          this.mesh.position.sub(new THREE.Vector3(v[0], v[1], v[2]));
        }
      }
    }
  }
}

abstract class InternalNode extends Node {
  children: Node[];

  constructor(type: string, name: string, path: string, children: Node[], context: Context) {
    super(type, name, path, context);
    this.children = children;
  }
}


class FusionNode extends InternalNode {
  constructor(name: string, path: string, model: string, children: Node[], context: Context) {
    super("FusionNode", name, path, children, context);
    this.model = model;
  }
}


class AssemblyNode extends InternalNode {
  constructor(name: string, path: string, children: Node[], context: Context) {
    super("AssemblyNode", name, path, children, context);
  }
}


class LeafNode extends Node {

  constructor(name: string, path: string, model: string, context: Context) {
    super("LeafNode", name, path, context);
    this.model = model;
  }

}

// Factory function
export const loadNode = async (path: string, context: Context): Promise<Node> {
  const tstamp = new Date().getTime(); // avoid cache
  const response = await fetch(`/api${path}?t=${tstamp}`);
  const data = await response.json();

  let node: Node;

  if (data.type === "LeafNode") {
    node = new LeafNode(data.name, data.path, data.model, context);
  } else {
    const childrenPromises = data.children.map((childPath: string) => {
      loadNode(childPath, context);
    });
    const children = await Promise.all(childrenPromises);
    if (data.type === "FusionNode") {
      node = new FusionNode(data.name, data.path, data.model, children, context);
    } else if (data.type === "AssemblyNode") {
      node = new AssemblyNode(data.name, data.path, children, context);
    }
  }

  if (!node) {
    throw new Error("Invalid node type");
  }

  node.setOperations(data.operations);
  return node;
}
