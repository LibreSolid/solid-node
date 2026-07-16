/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// Entry point of the embeddable viewer. Mounts into a container
// element, loads a `solid export` manifest, and renders it with orbit
// controls; animated models ($t expressions) get play/pause and a
// timeline slider. Containers with a data-solid-widget attribute
// (holding the manifest URL) mount automatically on page load.

import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { Manifest } from './types';
import { WidgetTree } from './tree';

interface MountOptions {
  // Start with the animation running (default true for animated models)
  autoplay?: boolean;
  // Initial animation time, 0..1 (default 0)
  time?: number;
}

export async function mount(
  target: HTMLElement | string,
  manifestUrl: string,
  options: MountOptions = {},
): Promise<void> {
  const container = resolveContainer(target);

  const response = await fetch(manifestUrl);
  if (!response.ok) {
    throw new Error(`Failed to load ${manifestUrl}: ${response.status}`);
  }
  const manifest = (await response.json()) as Manifest;
  const baseUrl = manifestUrl.replace(/[^/]*$/, '');

  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xffffff, 0x556677, 1.2));
  const sun = new THREE.DirectionalLight(0xffffff, 1.5);
  sun.position.set(1, -1, 2);
  scene.add(sun);

  const tree = new WidgetTree(manifest.root, baseUrl);
  scene.add(tree.group);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  container.style.position = 'relative';
  renderer.domElement.style.display = 'block';
  container.appendChild(renderer.domElement);

  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 10000);
  camera.up.set(0, 0, 1); // Z is up, as in OpenSCAD

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.rotateSpeed = 0.5;

  let time = options.time ?? 0;
  let playing = false;

  tree.update(time);
  await tree.loaded;
  fitCamera(camera, controls, scene);

  const resize = () => {
    const width = container.clientWidth;
    const height = container.clientHeight;
    renderer.setSize(width, height);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  };
  resize();
  new ResizeObserver(resize).observe(container);

  let slider: HTMLInputElement | undefined;
  if (tree.animated) {
    playing = options.autoplay ?? true;
    slider = buildControls(
      container,
      manifest.animation.frames,
      () => playing,
      (p) => { playing = p; },
      (t) => { time = t; },
    );
    slider.value = String(time);
  }

  const cycleSeconds =
    manifest.animation.frames / manifest.animation.fps;
  let lastTimestamp: number | undefined;

  renderer.setAnimationLoop((timestamp: number) => {
    const elapsed = lastTimestamp === undefined
      ? 0 : (timestamp - lastTimestamp) / 1000;
    lastTimestamp = timestamp;

    if (playing) {
      time = (time + elapsed / cycleSeconds) % 1;
      if (slider) {
        slider.value = String(time);
      }
    }
    tree.update(time);
    renderer.render(scene, camera);
  });
}

function resolveContainer(target: HTMLElement | string): HTMLElement {
  if (typeof target !== 'string') {
    return target;
  }
  const element = document.querySelector<HTMLElement>(target);
  if (!element) {
    throw new Error(`solid-widget: no element matches "${target}"`);
  }
  return element;
}

function fitCamera(
  camera: THREE.PerspectiveCamera,
  controls: OrbitControls,
  scene: THREE.Scene,
): void {
  scene.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(scene);
  if (box.isEmpty()) {
    return;
  }
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3()).length();

  const distance = (size / 2) /
    Math.tan((camera.fov * Math.PI) / 360) * 1.2;
  const direction = new THREE.Vector3(1, -1, 0.8).normalize();

  camera.position.copy(center).addScaledVector(direction, distance);
  camera.near = distance / 100;
  camera.far = distance * 100;
  camera.updateProjectionMatrix();
  controls.target.copy(center);
  controls.update();
}

function buildControls(
  container: HTMLElement,
  frames: number,
  isPlaying: () => boolean,
  setPlaying: (playing: boolean) => void,
  setTime: (time: number) => void,
): HTMLInputElement {
  const bar = document.createElement('div');
  bar.style.cssText =
    'position:absolute;left:0;right:0;bottom:0;display:flex;' +
    'align-items:center;gap:8px;padding:6px 10px;' +
    'background:rgba(30,33,38,0.65);color:#fff;' +
    'font:13px system-ui,sans-serif;';

  const button = document.createElement('button');
  button.style.cssText =
    'background:none;border:none;color:inherit;cursor:pointer;' +
    'font-size:15px;padding:0 4px;line-height:1;';
  const updateButton = () => {
    button.textContent = isPlaying() ? '⏸' : '▶';
    button.title = isPlaying() ? 'Pause' : 'Play';
  };
  updateButton();
  button.addEventListener('click', () => {
    setPlaying(!isPlaying());
    updateButton();
  });

  const slider = document.createElement('input');
  slider.type = 'range';
  slider.min = '0';
  slider.max = '1';
  slider.step = String(1 / frames);
  slider.value = '0';
  slider.style.cssText = 'flex:1;margin:0;';
  slider.addEventListener('input', () => {
    setPlaying(false);
    updateButton();
    setTime(Number(slider.value));
  });

  bar.appendChild(button);
  bar.appendChild(slider);
  container.appendChild(bar);
  return slider;
}

// Auto-mount containers marked with data-solid-widget="<manifest url>".
// The page's own query string can control the initial state -- used by
// the Sphinx directive (iframe src="...?t=0.25&autoplay=0") to embed
// static poses:
//   ?t=<0..1>      initial animation time
//   ?autoplay=0    start paused
function autoMount(): void {
  const params = new URLSearchParams(window.location.search);
  const options: MountOptions = {};
  const t = Number(params.get('t'));
  if (params.has('t') && !Number.isNaN(t)) {
    options.time = Math.min(Math.max(t, 0), 1);
  }
  if (params.get('autoplay') === '0') {
    options.autoplay = false;
  }

  document
    .querySelectorAll<HTMLElement>('[data-solid-widget]')
    .forEach((element) => {
      const url = element.dataset.solidWidget;
      if (url) {
        mount(element, url, options).catch((error) => {
          element.textContent = `solid-widget: ${error.message}`;
          console.error(error);
        });
      }
    });
}

if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoMount);
  } else {
    autoMount();
  }
}
