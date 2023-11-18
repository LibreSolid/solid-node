import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader';

export class NodeLoader {
  meshes: THREE.Mesh[];
  scene: THREE.Scene | undefined;
  stlLoader: STLLoader;
  root: string;
  code: string;
  newCode: string;

  constructor() {
    this.stlLoader = new STLLoader();
    this.meshes = [];
    this.root = '';
    this.code = '';
    this.newCode = this.code;
  }

  setScene(scene: THREE.Scene) {
    this.scene = scene;
    for (const mesh of this.meshes) {
      this.scene.add(mesh);
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
    console.log(result);
    if (result.model) {
      this.load(`${nodePath}/${result.model}`);
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

  load(stlPath: string) {
    this.stlLoader.load(`api${stlPath}`, (geometry) => {
      const material = new THREE.MeshNormalMaterial();
      const mesh = new THREE.Mesh(geometry, material);
      if (this.scene) {
        this.scene.add(mesh);
      }
      this.meshes.push(mesh);
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
      console.log('File saved!');
    }
  }

  clear() {
    for (const mesh of this.meshes) {
      if (this.scene) {
        this.scene.remove(mesh);
      }
    }
    this.code = '';
    this.meshes = [];
  }
}
