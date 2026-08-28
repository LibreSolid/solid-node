/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { frameBounds, ViewerView } from './camera';
import { AssemblyNavigation } from './assembly';
import {
  controlPlan, resolveBaseUrl, resolveOptions, showsDriverChrome,
} from './options';
import {
  BreadcrumbSegment, ControlLayer, controlLayer, DriverControl,
  driverControl, formatDisplay, formatReadout,
} from './controls';
import {
  DriverListener, DriverStore, TriggerHandle, toNative,
} from './drivers';
import { EvalScope, freeVariables, TIME_ID } from './evaluator';
import { AssemblyNode, AssemblyPath, WidgetTree } from './tree';
import { Manifest, ManifestDriver, ManifestInstruction, ManifestNode } from './types';
import { API_VERSION } from './version';

export type AnimationMode = 'inline' | 'toggle' | 'none' | 'external';
// Whether the widget presents the driver chrome itself. A host building
// its own instrument panel on the driving API asks for 'none' and keeps
// every method below (ADR-056 stage 3c, design D9).
export type DriverControlsMode = 'inline' | 'none';
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
  driverControls?: DriverControlsMode;
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
  // The driver chrome, rebuilt whenever the focused layer or the
  // document changes and updated in place while values move.
  let driverChrome: DriverChrome | undefined;
  // True while a control of ours is writing a value, so the change we
  // hear back does not fight the input the maker is dragging.
  let drivingFromChrome = false;
  const assemblyNavigation = new AssemblyNavigation();
  // One driver state for this mount, reconciled (not replaced) when the
  // document is republished, so a host's listeners and its current pose
  // survive a live rebuild.
  const drivers = new DriverStore();

  const scope = (): EvalScope => ({ time, drivers: drivers.scope() });

  // One door for a driver value, whether the maker moved a slider or
  // the host called setDriver: identical store semantics, identical
  // re-evaluation, and a listener cannot tell the two apart.
  const driveTo = (id: string, value: number) => {
    drivers.setDriver(id, value);
    // The set is answered this frame: only the operations naming this
    // driver are re-evaluated, and the rest keep the matrices they
    // have.
    tree?.update(scope(), { time: false, drivers: drivers.tick() });
    renderer.render(scene, camera);
  };

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
    // After the store and the navigation have reconciled, so the chrome
    // reflects the values that survived the republish and a focus the
    // update may have reset (design D10).
    rebuildDriverChrome();
  };

  // The ONE place focus moves, whether the host called `setRoot` or the
  // maker clicked the breadcrumb (design D8). Navigation, camera and
  // chrome move together, so the widget and the host can never disagree
  // about what is focused.
  const focusOn = (path: AssemblyPath | null) => {
    if (!tree) {
      throw new Error('Viewer assembly is unavailable');
    }
    assemblyNavigation.setRoot(tree, path);
    applyFrame(null);
    rebuildDriverChrome();
    renderer.render(scene, camera);
  };

  const nativeValues = (): Record<string, number> => {
    const values: Record<string, number> = {};
    for (const id of Object.keys(drivers.drivers())) {
      values[id] = drivers.driver(id);
    }
    return values;
  };

  function rebuildDriverChrome(): void {
    driverChrome?.remove();
    driverChrome = undefined;
    const table = drivers.drivers();
    if (!showsDriverChrome(resolved.driverControls,
                           Object.keys(table).length > 0)) {
      return;
    }
    driverChrome = buildDriverChrome(container, controlLayer({
      drivers: table,
      instructions: drivers.instructions(),
      values: nativeValues(),
      focus: assemblyNavigation.root(),
      rootLabel: tree?.name ?? 'root',
    }), {
      setDriver(id: string, value: number) {
        // Marked so the change we hear back does not write over the
        // input the maker is still dragging.
        drivingFromChrome = true;
        try {
          driveTo(id, value);
        } finally {
          drivingFromChrome = false;
        }
      },
      trigger: (name: string) => drivers.trigger(name),
      focus: focusOn,
    });
  }

  await replaceTree(resolved.view);

  // The public channel, subscribed once per mount: a ramp moving a
  // driver reaches its slider exactly the way it reaches a host's
  // listener, with no private path into the store (design D7).
  const unsubscribeDrivers = drivers.onDriverChange((id, value) => {
    driverChrome?.apply(id, value, drivingFromChrome);
  });

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
      unsubscribeDrivers();
      driverChrome?.remove();
      driverChrome = undefined;
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
      focusOn(path);
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
      driveTo(id, value);
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

// ---------------------------------------------------------------------
// The driver chrome's DOM (ADR-056 stage 3c). Everything below RENDERS a
// `ControlLayer` and calls back through the same driving API a host
// uses; it decides nothing itself, because there is no DOM test
// framework in this bench and an untestable decision is a decision
// nobody checks (design D1). Its proof is the live browser drive.

interface DriverChromeActions {
  setDriver(id: string, value: number): void;
  trigger(name: string): TriggerHandle;
  focus(path: AssemblyPath | null): void;
}

interface DriverChrome {
  /** A driver moved: update its readout, and its input unless the
   * maker's own hand is what moved it. */
  apply(id: string, value: number, fromChrome: boolean): void;
  remove(): void;
}

type ControlUpdate = (value: number, fromChrome: boolean) => void;

const PANEL_STYLE =
  'position:absolute;left:0;top:0;display:flex;flex-direction:column;' +
  'gap:6px;padding:8px 10px;max-width:75%;' +
  'background:rgba(30,33,38,0.65);color:#fff;' +
  'font:13px system-ui,sans-serif;';

const BUTTON_STYLE =
  'background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.25);' +
  'color:inherit;cursor:pointer;border-radius:4px;padding:2px 8px;' +
  'font:inherit;';

function buildDriverChrome(
  container: HTMLElement,
  layer: ControlLayer,
  actions: DriverChromeActions,
): DriverChrome {
  const panel = document.createElement('div');
  panel.className = 'driver-controls';
  panel.style.cssText = PANEL_STYLE;

  panel.append(buildBreadcrumb(layer, actions));

  if (layer.instructions.length > 0) {
    const row = document.createElement('div');
    row.className = 'driver-instructions';
    row.style.cssText = 'display:flex;flex-wrap:wrap;gap:6px;';
    layer.instructions.forEach((entry) => {
      row.append(buildInstructionButton(entry.name, entry.label, actions));
    });
    panel.append(row);
  }

  const updates = new Map<string, ControlUpdate>();
  layer.drivers.forEach((control) => {
    panel.append(buildDriverRow(control, actions, updates));
  });

  container.append(panel);

  return {
    apply(id: string, value: number, fromChrome: boolean) {
      updates.get(id)?.(value, fromChrome);
    },
    remove() {
      panel.remove();
    },
  };
}

function buildBreadcrumb(
  layer: ControlLayer,
  actions: DriverChromeActions,
): HTMLElement {
  const nav = document.createElement('nav');
  nav.className = 'driver-breadcrumb';
  nav.setAttribute('aria-label', 'Assembly focus');
  nav.style.cssText =
    'display:flex;flex-wrap:wrap;align-items:center;gap:4px;';

  layer.breadcrumb.forEach((segment, index) => {
    if (index > 0) {
      nav.append(separator('/'));
    }
    nav.append(buildBreadcrumbStep(segment, actions));
  });

  const focused = layer.breadcrumb[layer.breadcrumb.length - 1].path;
  layer.children.forEach((name) => {
    nav.append(separator('|'));
    const button = document.createElement('button');
    button.className = 'driver-descend';
    button.textContent = `${name} ▸`;
    button.setAttribute('aria-label', `Focus ${name}`);
    button.style.cssText = BUTTON_STYLE;
    button.addEventListener('click', () => {
      actions.focus([...focused, name]);
    });
    nav.append(button);
  });

  return nav;
}

function buildBreadcrumbStep(
  segment: BreadcrumbSegment,
  actions: DriverChromeActions,
): HTMLElement {
  const button = document.createElement('button');
  button.className = 'driver-breadcrumb-step';
  button.textContent = segment.label;
  button.setAttribute('aria-label', `Focus ${segment.label}`);
  button.style.cssText = BUTTON_STYLE;
  if (segment.current) {
    button.setAttribute('aria-current', 'true');
    button.disabled = true;
    button.style.cssText += 'opacity:0.75;cursor:default;';
    return button;
  }
  button.addEventListener('click', () => {
    // The document root is `null` to the focus API, not an empty path.
    actions.focus(segment.path.length === 0 ? null : segment.path);
  });
  return button;
}

function separator(mark: string): HTMLElement {
  const span = document.createElement('span');
  span.textContent = mark;
  span.setAttribute('aria-hidden', 'true');
  span.style.cssText = 'opacity:0.5;';
  return span;
}

function buildInstructionButton(
  name: string,
  label: string,
  actions: DriverChromeActions,
): HTMLButtonElement {
  const button = document.createElement('button');
  button.className = 'driver-instruction';
  button.textContent = label;
  button.setAttribute('aria-label', `Run ${label}`);
  button.style.cssText = BUTTON_STYLE;
  // Which run this button is showing. A re-press is the ratified
  // last-wins replacement, so the older run's `done` -- which settles
  // when the new one takes its drivers over -- must not clear the busy
  // state the newer press owns. Nothing is debounced: the maker asked
  // twice and the machine obeys twice.
  let latest = 0;
  button.addEventListener('click', () => {
    const run = ++latest;
    button.setAttribute('aria-busy', 'true');
    button.style.cssText = BUTTON_STYLE + 'background:rgba(127,209,255,0.35);';
    actions.trigger(name).done.then(() => {
      if (run !== latest) {
        return;
      }
      button.removeAttribute('aria-busy');
      button.style.cssText = BUTTON_STYLE;
    });
  });
  return button;
}

function buildDriverRow(
  control: DriverControl,
  actions: DriverChromeActions,
  updates: Map<string, ControlUpdate>,
): HTMLElement {
  const row = document.createElement('div');
  row.className = 'driver-control';
  row.style.cssText = 'display:flex;align-items:center;gap:8px;';

  const name = document.createElement('span');
  name.textContent = control.label;
  name.style.cssText = 'min-width:5em;';

  const input = document.createElement('input');
  input.setAttribute('aria-label', control.unit === null
    ? control.label : `${control.label} (${control.unit})`);
  if (control.slider !== null) {
    input.type = 'range';
    input.min = String(control.slider.min);
    input.max = String(control.slider.max);
    // An integer driver stops on whole native units; a float one is
    // continuous, and 'any' is how that is spelled.
    input.step = control.slider.step === null
      ? 'any' : String(control.slider.step);
    input.value = String(control.slider.position);
    input.style.cssText = 'flex:1;margin:0;min-width:120px;';
  } else {
    // No declared range, so no bounds to travel between: a number field
    // is the honest control, rather than a slider spanning a guess.
    input.type = 'number';
    input.value = formatDisplay(control.display);
    input.style.cssText = 'width:8em;font:inherit;';
  }

  // A readout that holds still under a drag. The number and the unit
  // are separate elements so the alignment box is the NUMBER's: writing
  // them as one right-aligned string pins the unit and lets the digits
  // walk about underneath it. Tabular figures make every digit the same
  // width -- the panel's system font is otherwise proportional, so even
  // a constant digit count would shift -- and that is also what makes
  // the `ch` reservation exact, since `ch` is the width of `0`. Ten:
  // sign, four integer digits, point, four decimals. `min-width`, not
  // `width`, so a value past that grows its own row instead of lying.
  const readout = document.createElement('output');

  const figure = document.createElement('span');
  figure.style.cssText = 'display:inline-block;min-width:10ch;'
    + 'text-align:right;font-variant-numeric:tabular-nums;';

  // The separating space lives in the text, not in a flex gap, so the
  // readout still READS as "12.3457 mm" to a screen reader and to
  // anyone who copies it. A single space is a constant width, so it
  // costs the alignment nothing.
  const unit = document.createElement('span');

  readout.append(figure, unit);

  const show = (state: DriverControl) => {
    figure.textContent = formatReadout(state.display);
    unit.textContent = state.unit === null ? '' : ` ${state.unit}`;
    // Pinned thumb, truthful readout: the value is outside the declared
    // travel and the chrome says so instead of hiding it.
    readout.style.color = state.pinned ? '#ffd166' : 'inherit';
    readout.title = state.pinned
      ? 'outside the declared range' : '';
  };
  show(control);

  const write = () => {
    const design = Number(input.value);
    if (!Number.isFinite(design)) {
      return;
    }
    // Through the same conversion an instruction target takes and into
    // the same store call the host API makes -- one door, so a value
    // set on screen and one set programmatically are the same event.
    actions.setDriver(control.id, toNative(design, control.driver));
  };
  input.addEventListener('input', write);
  input.addEventListener('change', write);

  updates.set(control.id, (value: number, fromChrome: boolean) => {
    const state = driverControl(control.id, control.driver, value);
    show(state);
    if (fromChrome) {
      // The maker is holding this control; writing its own value back
      // would fight the drag.
      return;
    }
    input.value = state.slider === null
      ? formatDisplay(state.display) : String(state.slider.position);
  });

  row.append(name, input, readout);
  return row;
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
