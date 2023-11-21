import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader';
import { MeshDictionary, RawOperation, Operation, OperationDictionary } from './loader.d';
import { evaluate } from './evaluator';

export class NodeLoader {

  // Singleton
  private static instance: NodeLoader;

  shapes: MeshDictionary;
  operations: OperationDictionary;
  scene: THREE.Scene | undefined;
  stlLoader: STLLoader;
  ws: WebSocket | undefined;
  root: string;
  code: string;
  newCode: string;
  location: string;

  constructor(location: string) {
    this.location = location;
    this.stlLoader = new STLLoader();
    this.shapes = {};
    this.root = '';
    this.code = '';
    this.newCode = this.code;

    this.operations = {};

    this.watch();
  }

  // Static method that controls access to the singleton instance
  public static getInstance(location: string): NodeLoader {
    if (!NodeLoader.instance) {
      NodeLoader.instance = new NodeLoader(location);
    }
    return NodeLoader.instance;
  }

  watch() {
    const parts = this.location.split('/');
    const protocol = parts[0].replace('http', 'ws');
    const domain = parts[2];

    if (this.ws) return;

    this.ws = new WebSocket(`${protocol}//${domain}/ws`);

    this.ws.onmessage = (event) => {
      if (event.data == "reload") {
        this.reload();
      }
    };

    this.ws.onclose = () => {
      this.ws = undefined;
      this.watch();
    };

  }

  reload() {
    console.log('Reload!');
    for (const path in this.shapes) {
      if (this.shapes.hasOwnProperty(path)) {
        this.load(path, this.operations[path]);
      }
    }
  }

  setScene(scene: THREE.Scene) {
    this.scene = scene;
    for (const path in this.shapes) {
      if (this.shapes.hasOwnProperty(path)) {
        this.scene.add(this.shapes[path]);
      }
    }
  }

  setCode(code: string) {
    this.newCode = code;
  }

  loadRoot(nodePath: string) {
    this.clear();
    this.root = nodePath;
    this.loadNode(nodePath);
  }

  async loadNode(nodePath: string) {
    const response = await fetch(`/api${nodePath}/`);
    const result = await response.json();
    const operations = evaluate(result.operations as RawOperation[], 0);
    if (result.model) {
      this.load(`${nodePath}/${result.model}`, operations);
    }
    if (result.children) {
      const children = result.children as string[];
      children.forEach((child) => {
        this.loadNode(`${nodePath}/${child}`);
      });
    }
    if (result.code && !this.code) {
      this.code = result.code;
    }
  }

  load(path: string, operations: Operation[]) {
    const tstamp = new Date().getTime(); // avoid cache
    this.stlLoader.load(`api${path}?t=${tstamp}`, (geometry) => {
      const material = new THREE.MeshNormalMaterial();
      const mesh = new THREE.Mesh(geometry, material);
      this.applyOperations(mesh, operations);
      if (this.scene) {
        if (this.shapes[path]) {
          this.scene.remove(this.shapes[path]);
        }
        this.scene.add(mesh);
      }
      this.shapes[path] = mesh;
      this.operations[path] = operations;
    });
  }

  async saveCode() {
    const response = await fetch(
      `/api${this.root}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'text/plain',
        },
        body: this.newCode,
      }
    );
    if (response.ok) {
      this.code = this.newCode;
    }
  }

  clear() {
    for (const path in this.shapes) {
      if (this.shapes.hasOwnProperty(path)) {
        if (this.scene) {
          this.scene.remove(this.shapes[path]);
        }
      }
    }
    this.code = '';
    this.shapes = {};
    this.operations = {};
  }

  applyOperations(mesh: THREE.Mesh, operations: Operation[]) {
    for (const op of operations) {
      if (op[0] == "r") {
        const quaternion = new THREE.Quaternion();
        const ax = op[2];
        const axis = new THREE.Vector3(ax[0], ax[1], ax[2]);
        quaternion.setFromAxisAngle(axis, op[1] * Math.PI / 180)
        mesh.applyQuaternion(quaternion);
      }
      if (op[0] == "t") {
        const v = op[1];
        mesh.position.add(new THREE.Vector3(v[0], v[1], v[2]));
      }
    }
  }
}
