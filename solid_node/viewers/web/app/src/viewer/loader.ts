import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader';

export class MeshLoader {
  meshes: THREE.Mesh[];
  scene: THREE.Scene;
  loader: STLLoader;

  constructor(scene: THREE.Scene) {
    this.scene = scene;
    this.loader = new STLLoader();
    this.meshes = [];

  }

  loadRoot(nodePath: string) {
    this.clear();
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



  }

  load(stlPath: string) {
    this.loader.load(`api${stlPath}`, (geometry) => {
      const material = new THREE.MeshNormalMaterial();
      const mesh = new THREE.Mesh(geometry, material);
      this.scene.add(mesh);
      this.meshes.push(mesh);
    });
  }

  clear() {
    for (const mesh of this.meshes) {
      this.scene.remove(mesh);
    }
    this.meshes = [];
  }
}
