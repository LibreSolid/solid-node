/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { frameBounds, ViewerView } from './camera';
import { AssemblyNavigation } from './assembly';
import { controlPlan, resolveBaseUrl, resolveOptions } from './options';
import { DriverListener, DriverStore, TriggerHandle } from './drivers';
import { EvalScope, freeVariables, TIME_ID } from './evaluator';
import { AssemblyNode, AssemblyPath, WidgetTree } from './tree';
import { Manifest, ManifestDriver, ManifestInstruction, ManifestNode } from './types';
import { API_VERSION } from './version';

export type AnimationMode = 'inline' | 'toggle' | 'none' | 'external';
export type View = ViewerView;
export type { AssemblyNode, AssemblyPath } from './tree';
export type VectorInput = THREE.Vector3 | readonly [number, number, number];
export interface ViewInput {
  camera: VectorInput;
  target: VectorInput;
}

export interface ViewerOptions {
  baseUrl?: string;
  animation?: AnimationMode;
  time?: number;
  autoplay?: boolean;
  view?: ViewInput;
  up?: VectorInput;
  fov?: number;
  className?: string;
  role?: string;
  ariaLabel?: string;
}

export interface ViewerHandle {
  dispose(): void;
  view(): View;
  reload(): Promise<void>;
  artifactChanged(path: string): Promise<void>;
  manifestChanged(): Promise<void>;
  assembly(): AssemblyNode;
  setRoot(path: AssemblyPath | null): void;
  setVisible(path: AssemblyPath, visible: boolean): void;
  setTime(time: number): void;
  // The driving API (ADR-056 stage 3b). Values are NATIVE driver units
  // and ids are verbatim from the document; `range` never clamps.
  drivers(): Record<string, ManifestDriver>;
  driver(id: string): number;
  setDriver(id: string, value: number): void;
  onDriverChange(listener: DriverListener): () => void;
  instructions(): Record<string, ManifestInstruction>;
  trigger(name: string): TriggerHandle;
  apiVersion: number;
}

export async function mount(
  target: HTMLElement | string,
  sourceUrl: string,
  options: ViewerOptions = {},
): Promise<ViewerHandle> {
  const container = resolveContainer(target);
  const resolved = resolveOptions(options);
  const baseUrl = resolveBaseUrl(sourceUrl, resolved.baseUrl ?? undefined);
  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xffffff, 0x556677, 1.2));
  const sun = new THREE.DirectionalLight(0xffffff, 1.5);
  sun.position.set(1, -1, 2);
  scene.add(sun);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  container.style.position = 'relative';
  renderer.domElement.style.display = 'block';
  if (resolved.className !== null) {
    renderer.domElement.className = resolved.className;
  }
  if (resolved.role !== null) {
    renderer.domElement.setAttribute('role', resolved.role);
  }
  if (resolved.ariaLabel !== null) {
    renderer.domElement.setAttribute('aria-label', resolved.ariaLabel);
  }
  container.appendChild(renderer.domElement);

  const camera = new THREE.PerspectiveCamera(resolved.fov, 1, 0.1, 10000);
  camera.up.copy(resolved.up);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.rotateSpeed = 0.5;

  let tree: WidgetTree | undefined;
  let time = resolved.time;
  let playing = false;
  let slider: HTMLInputElement | undefined;
  let controlElements: HTMLElement[] = [];
  let cycleSeconds = 1;
  let disposed = false;
  const assemblyNavigation = new AssemblyNavigation();
  // One driver state for this mount, reconciled (not replaced) when the
  // document is republished, so a host's listeners and its current pose
  // survive a live rebuild.
  const drivers = new DriverStore();

  const scope = (): EvalScope => ({ time, drivers: drivers.scope() });

  const setTime = (next: number) => {
    time = Math.min(Math.max(next, 0), 1);
    if (slider) {
      slider.value = String(time);
    }
    tree?.update(scope(), { time: true, drivers: EMPTY });
    renderer.render(scene, camera);
  };

  const applyFrame = (view: View | null) => {
    scene.updateMatrixWorld(true);
    const framed = frameBounds(visibleBounds(scene), camera.fov, view, resolved.up);
    if (!framed) {
      return;
    }
    camera.position.copy(framed.position);
    camera.up.copy(framed.up);
    camera.near = framed.near;
    camera.far = framed.far;
    camera.updateProjectionMatrix();
    controls.target.copy(framed.target);
    controls.update();
  };

  const captureView = (): View => ({
    camera: camera.position.clone(),
    target: controls.target.clone(),
  });

  const replaceTree = async (view: View | null) => {
    const document = await loadDocument(sourceUrl);
    drivers.reconcile(document.drivers ?? {}, document.instructions ?? {});
    const next = new WidgetTree(document.root, baseUrl);
    next.update(scope());
    await next.loaded;
    if (disposed) {
      next.dispose();
      return;
    }
    if (tree) {
      scene.remove(tree.group);
      tree.dispose();
    }
    tree = next;
    scene.add(tree.group);
    assemblyNavigation.reconcile(tree);
    applyFrame(view);

    refreshControls(document);
  };

  const refreshControls = (document: Manifest) => {
    controlElements.forEach((element) => element.remove());
    controlElements = [];
    slider = undefined;
    const plan = controlPlan(resolved.animation, tree!.animated);
    playing = tree!.animated && !plan.hostDriven && resolved.autoplay;
    cycleSeconds = document.animation.frames / document.animation.fps;
    if (plan.bar) {
      const built = buildControls(
        container,
        document.animation.frames,
        plan,
        () => playing,
        (nextPlaying) => { playing = nextPlaying; },
        setTime,
      );
      slider = built.slider;
      controlElements = built.elements;
      slider.value = String(time);
    }
  };

  await replaceTree(resolved.view);

  const resize = () => {
    if (disposed) {
      return;
    }
    const width = container.clientWidth;
    const height = container.clientHeight;
    renderer.setSize(width, height);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  };
  resize();
  const observer = new ResizeObserver(resize);
  observer.observe(container);

  let lastTimestamp: number | undefined;
  renderer.setAnimationLoop((timestamp: number) => {
    const elapsed = lastTimestamp === undefined
      ? 0 : (timestamp - lastTimestamp) / 1000;
    lastTimestamp = timestamp;
    // Ramps advance on wall-clock elapsed time, in the same loop: their
    // endpoints and duration are exact, and only the sampling between
    // them varies with the frame rate (design D4 -- this is an
    // animation, and determinism stays with the Python simulation).
    const movedDrivers = drivers.tick();
    if (playing) {
      setTime((time + elapsed / cycleSeconds) % 1);
    }
    tree?.update(scope(), { time: playing, drivers: movedDrivers });
    renderer.render(scene, camera);
  });

  return {
    apiVersion: API_VERSION,
    dispose() {
      if (disposed) {
        return;
      }
      disposed = true;
      renderer.setAnimationLoop(null);
      observer.disconnect();
      controls.dispose();
      // Nothing will advance the ramps again, so their promises settle
      // here rather than never.
      drivers.dispose();
      tree?.dispose();
      renderer.dispose();
      container.replaceChildren();
    },
    view: captureView,
    async reload() {
      await replaceTree(captureView());
    },
    async artifactChanged(path: string) {
      await tree?.artifactChanged(path, baseUrl);
      if (tree) {
        assemblyNavigation.reconcile(tree);
      }
      renderer.render(scene, camera);
    },
    async manifestChanged() {
      const document = await loadDocument(sourceUrl);
      drivers.reconcile(document.drivers ?? {}, document.instructions ?? {});
      await tree?.reconcile(document.root, baseUrl);
      if (tree) {
        const rootChanged = assemblyNavigation.reconcile(tree);
        tree.update(scope());
        refreshControls(document);
        if (rootChanged) {
          applyFrame(null);
        }
      }
      renderer.render(scene, camera);
    },
    assembly() {
      if (!tree) {
        throw new Error('Viewer assembly is unavailable');
      }
      return tree.assembly();
    },
    setRoot(path: AssemblyPath | null) {
      if (!tree) {
        throw new Error('Viewer assembly is unavailable');
      }
      assemblyNavigation.setRoot(tree, path);
      applyFrame(null);
      renderer.render(scene, camera);
    },
    setVisible(path: AssemblyPath, visible: boolean) {
      if (!tree) {
        throw new Error('Viewer assembly is unavailable');
      }
      assemblyNavigation.setVisible(tree, path, visible);
      renderer.render(scene, camera);
    },
    setTime,
    drivers: () => drivers.drivers(),
    driver: (id: string) => drivers.driver(id),
    setDriver(id: string, value: number) {
      drivers.setDriver(id, value);
      // The set is answered this frame: only the operations naming this
      // driver are re-evaluated, and the rest keep the matrices they
      // have.
      tree?.update(scope(), { time: false, drivers: drivers.tick() });
      renderer.render(scene, camera);
    },
    onDriverChange: (listener: DriverListener) =>
      drivers.onDriverChange(listener),
    instructions: () => drivers.instructions(),
    trigger: (name: string) => drivers.trigger(name),
  };
}

const EMPTY: ReadonlySet<string> = new Set();

function visibleBounds(root: THREE.Object3D): THREE.Box3 {
  const bounds = new THREE.Box3();
  root.updateWorldMatrix(true, true);
  const visit = (object: THREE.Object3D) => {
    if (!object.visible) {
      return;
    }
    if (object instanceof THREE.Mesh) {
      if (object.geometry.boundingBox === null) {
        object.geometry.computeBoundingBox();
      }
      if (object.geometry.boundingBox !== null) {
        bounds.union(object.geometry.boundingBox.clone().applyMatrix4(object.matrixWorld));
      }
    }
    object.children.forEach(visit);
  };
  visit(root);
  return bounds;
}

// The document schema this viewer evaluates. Version 2 added the
// `drivers` table, and since ADR-056 stage 3b this viewer EVALUATES
// driver-referencing expressions rather than refusing them: a non-empty
// table is now a document to render at its declared defaults and drive,
// not one to turn away.
//
// What is still refused is a document that contradicts itself: an
// expression naming a qualified id its own table does not declare has
// no value to bind, and rendering it anyway would show a wrong machine
// instead of an error. The producer guarantees every referenced id
// appears in the table; this is what makes a broken producer loud.
export function assertRenderable(document: Manifest, sourceUrl: string): void {
  const declared = new Set(Object.keys(document.drivers ?? {}));
  const missing = new Set<string>();

  const visit = (node: ManifestNode) => {
    for (const operation of node.operations) {
      const expressions = operation[0] === 'r'
        ? [operation[1]] : operation[1];
      for (const expression of expressions) {
        for (const name of freeVariables(expression)) {
          if (name !== TIME_ID && !declared.has(name)) {
            missing.add(name);
          }
        }
      }
    }
    (node.children ?? []).forEach(visit);
  };
  visit(document.root);

  if (missing.size > 0) {
    const known = [...declared].sort().join(', ') || 'none';
    throw new Error(
      `${sourceUrl} has expressions naming undeclared drivers ` +
      `(${[...missing].sort().join(', ')}); its drivers table declares: ` +
      `${known}. The document is malformed: refusing it rather than ` +
      'rendering a wrong pose.',
    );
  }
}

async function loadDocument(sourceUrl: string): Promise<Manifest> {
  let response: Response;
  try {
    response = await fetch(sourceUrl);
  } catch (error) {
    throw new Error(`Failed to load ${sourceUrl}: ${String(error)}`);
  }
  if (!response.ok) {
    throw new Error(`Failed to load ${sourceUrl}: ${response.status}`);
  }
  let document: Manifest;
  try {
    document = await response.json() as Manifest;
  } catch (error) {
    throw new Error(`Failed to parse ${sourceUrl}: ${String(error)}`);
  }
  assertRenderable(document, sourceUrl);
  return document;
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

function buildControls(
  container: HTMLElement,
  frames: number,
  plan: ReturnType<typeof controlPlan>,
  isPlaying: () => boolean,
  setPlaying: (playing: boolean) => void,
  setTime: (time: number) => void,
): { slider: HTMLInputElement; elements: HTMLElement[] } {
  const bar = document.createElement('div');
  bar.className = 'animation-controls';
  if (plan.styled) {
    bar.style.cssText =
      'position:absolute;left:0;right:0;bottom:0;display:flex;' +
      'align-items:center;gap:8px;padding:6px 10px;' +
      'background:rgba(30,33,38,0.65);color:#fff;' +
      'font:13px system-ui,sans-serif;';
  }

  const button = document.createElement('button');
  if (plan.styled) {
    button.style.cssText =
      'background:none;border:none;color:inherit;cursor:pointer;' +
      'font-size:15px;padding:0 4px;line-height:1;';
  }
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
  if (plan.styled) {
    slider.style.cssText = 'flex:1;margin:0;';
  }
  slider.addEventListener('input', () => {
    setPlaying(false);
    updateButton();
    setTime(Number(slider.value));
  });

  bar.append(button, slider);
  const elements: HTMLElement[] = [bar];
  if (plan.toggle) {
    const toggle = document.createElement('button');
    toggle.className = 'timeline-toggle';
    toggle.textContent = 'Timeline';
    toggle.setAttribute('aria-expanded', 'false');
    bar.hidden = true;
    toggle.addEventListener('click', () => {
      bar.hidden = !bar.hidden;
      toggle.setAttribute('aria-expanded', String(!bar.hidden));
    });
    container.append(toggle);
    elements.unshift(toggle);
  }
  container.append(bar);
  return { slider, elements };
}
