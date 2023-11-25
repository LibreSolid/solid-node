import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader';
import { MeshDictionary,
         RawOperation,
         Operation,
         RawOperationDictionary,
         OperationDictionary,
       } from './loader.d';
import { evaluate } from './evaluator';

export class NodeLoader {

  // Singleton
  private static instance: NodeLoader;

  shapes: MeshDictionary;
  operations: OperationDictionary;
  rawOperations: RawOperationDictionary;
  scene: THREE.Scene | undefined;
  stlLoader: STLLoader;
  reloadTrigger: WebSocket | undefined;
  //compileError: WebSocket | undefined;
  root: string;
  code: string;
  newCode: string;
  location: string;
  time: number;

  constructor(location: string) {
    this.location = location;
    this.stlLoader = new STLLoader();
    this.root = '';
    this.code = '';
    this.newCode = this.code;

    this.shapes = {};
    this.operations = {};
    this.rawOperations = {};

    this.time = 0;

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

    if (this.reloadTrigger) return;

    this.reloadTrigger = new WebSocket(`${protocol}//${domain}/ws/reload`);

    this.reloadTrigger.onmessage = (event) => {
      if (event.data === "reload") {
        this.reload();
      }
    };

    this.reloadTrigger.onclose = () => {
      this.reloadTrigger = undefined;
      this.watch();
    };

  }

  reload() {
    const oldShapes = Object.assign({}, this.shapes);
    this.shapes = {};
    this.loadNode(this.root);

    setTimeout(() => {
      // Garbage collect for deleted children
      for (const path in oldShapes) {
        if (oldShapes.hasOwnProperty(path)) {
          this.scene?.remove(oldShapes[path]);
        }
      }
    }, 200);
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
    const tstamp = new Date().getTime(); // avoid cache
    const response = await fetch(`/api${nodePath}?t=${tstamp}`);
    const result = await response.json();
    if (result.model) {
      this.load(`${nodePath}/${result.model}`,
                result.operations as RawOperation[]);
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

  load(path: string, rawOperations: RawOperation[]) {
    const tstamp = new Date().getTime(); // avoid cache
    const operations = evaluate(rawOperations, this.time);

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
      this.rawOperations[path] = rawOperations;
    });
  }

  setTime(time: number) {
    this.time = time;

    for (const path in this.shapes) {
      const mesh = this.shapes[path];
      const raw = this.rawOperations[path];
      const operations = evaluate(raw, time);
      this.unapplyOperations(mesh, this.operations[path]);
      this.applyOperations(mesh, operations);
      this.operations[path] = operations;
    }
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
    this.rawOperations = {};
  }

  applyOperations(mesh: THREE.Mesh, operations: Operation[]) {
    for (const op of operations) {
      if (op[0] === "r") {
        const quaternion = new THREE.Quaternion();
        const ax = op[2];
        const axis = new THREE.Vector3(ax[0], ax[1], ax[2]);
        quaternion.setFromAxisAngle(axis, op[1] * Math.PI / 180)
        mesh.applyQuaternion(quaternion);
      }
      if (op[0] === "t") {
        const v = op[1];
        mesh.position.add(new THREE.Vector3(v[0], v[1], v[2]));
      }
    }
  }

  unapplyOperations(mesh: THREE.Mesh, operations: Operation[]) {
    // Iterate through the operations in reverse order
    for (let i = operations.length - 1; i >= 0; i--) {
      const op = operations[i];

      if (op[0] === "r" && op[2]) {
        // Reverse the rotation
        const quaternion = new THREE.Quaternion();
        const ax = op[2];
        const axis = new THREE.Vector3(ax[0], ax[1], ax[2]);

        // Invert the angle for reverse rotation
        quaternion.setFromAxisAngle(axis, -(op[1] as number) * Math.PI / 180);
        mesh.applyQuaternion(quaternion);
      }

      if (op[0] === "t") {
        // Reverse the translation
        const v = op[1] as number[];

        // Subtract the translation vector
        mesh.position.sub(new THREE.Vector3(v[0], v[1], v[2]));
      }
    }
  }

}
