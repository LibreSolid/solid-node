import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader';

interface Shape {
  mesh: THREE.Mesh;
  path: string;
}

export class NodeLoader {

  // Singleton
  private static instance: NodeLoader;

  shapes: Shape[];
  ws: WebSocket;
  scene: THREE.Scene | undefined;
  stlLoader: STLLoader;
  root: string;
  code: string;
  newCode: string;
  location: string;

  constructor(location: string) {
    this.location = location;
    this.stlLoader = new STLLoader();
    this.shapes = [];
    this.root = '';
    this.code = '';
    this.newCode = this.code;
    this.ws = this.watch();
  }

  // Static method that controls access to the singleton instance
  public static getInstance(location: string): NodeLoader {
    if (!NodeLoader.instance) {
      NodeLoader.instance = new NodeLoader(location);
      console.log(new Date().getTime());
    }
    return NodeLoader.instance;
  }

  watch() {
    const parts = this.location.split('/');
    const protocol = parts[0].replace('http', 'ws');
    const domain = parts[2];

    const ws = new WebSocket(`${protocol}//${domain}/ws`);

    ws.onopen = () => {
        console.log('WebSocket Connected');
    };

    ws.onmessage = (event) => {
        console.log('File change detected:', event.data);
    };

    ws.onerror = (error) => {
        console.error('WebSocket Error:', error);
    };

    ws.onclose = () => {
        console.log('WebSocket Connection Closed');
    };

    return ws;
  }

  setScene(scene: THREE.Scene) {
    this.scene = scene;
    for (const shape of this.shapes) {
      this.scene.add(shape.mesh);
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

  load(path: string) {
    const tstamp = new Date().getTime(); // avoid cache
    this.stlLoader.load(`api${path}?t={tstamp}`, (geometry) => {
      const material = new THREE.MeshNormalMaterial();
      const mesh = new THREE.Mesh(geometry, material);
      if (this.scene) {
        this.scene.add(mesh);
        this.ws.send(path);
      }
      this.shapes.push({ mesh, path });
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
    for (const shape of this.shapes) {
      if (this.scene) {
        this.scene.remove(shape.mesh);
      }
    }
    this.code = '';
    this.shapes = [];
  }
}
