/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

import * as THREE from 'three';
import type {
  ViewerOptions, AnimationMode, DriverControlsMode, VectorInput,
} from './viewer';
import type { ViewerView } from './camera';

export interface ResolvedViewerOptions {
  baseUrl: string | null;
  animation: AnimationMode;
  driverControls: DriverControlsMode;
  time: number;
  autoplay: boolean;
  view: ViewerView | null;
  up: THREE.Vector3;
  fov: number;
  className: string | null;
  role: string | null;
  ariaLabel: string | null;
}

export interface ControlPlan {
  bar: boolean;
  toggle: boolean;
  collapsed: boolean;
  styled: boolean;
  hostDriven: boolean;
}

export function resolveOptions(
  options: ViewerOptions = {},
): ResolvedViewerOptions {
  const time = Number.isFinite(options.time) ? options.time! : 0;
  return {
    baseUrl: options.baseUrl ?? null,
    animation: options.animation ?? 'inline',
    // Presented by default, like the animation bar: a self-contained
    // export is opened by a maker with no host code behind it.
    driverControls: options.driverControls ?? 'inline',
    time: Math.min(Math.max(time, 0), 1),
    autoplay: options.autoplay ?? true,
    view: options.view ? {
      camera: resolveVector(options.view.camera),
      target: resolveVector(options.view.target),
    } : null,
    up: resolveVector(options.up, [0, 0, 1]),
    fov: Number.isFinite(options.fov) && options.fov! > 0 ? options.fov! : 50,
    className: options.className ?? null,
    role: options.role ?? null,
    ariaLabel: options.ariaLabel ?? null,
  };
}

function resolveVector(
  value: VectorInput | undefined,
  fallback?: readonly [number, number, number],
): THREE.Vector3 {
  const selected = value ?? fallback;
  if (!selected) {
    throw new Error('a viewer vector is required');
  }
  if (Array.isArray(selected)) {
    return new THREE.Vector3(selected[0], selected[1], selected[2]);
  }
  return (selected as THREE.Vector3).clone();
}

export function resolveBaseUrl(sourceUrl: string, baseUrl?: string): string {
  const root = baseUrl ?? sourceUrl.replace(/[?#].*$/, '').replace(/[^/]*$/, '');
  // A document naming no directory is beside its models, not at the server
  // root -- './' keeps the base joinable without rooting it at the host.
  if (!root) return './';
  return root.endsWith('/') ? root : `${root}/`;
}

/** Whether this mount presents the driver chrome (ADR-056 stage 3c,
 * design D9).
 *
 * Two independent conditions, and neither is the animation bar's: the
 * host must want the chrome, and the document must declare a driver for
 * there to be any. A driverless document is therefore untouched by this
 * option, and a host suppressing the chrome still holds the whole
 * driving API -- what is gated is the pixels, not the interface.
 */
export function showsDriverChrome(
  mode: DriverControlsMode,
  declaresDrivers: boolean,
): boolean {
  return mode === 'inline' && declaresDrivers;
}

export function controlPlan(
  mode: AnimationMode,
  animated: boolean,
): ControlPlan {
  if (!animated) {
    return { bar: false, toggle: false, collapsed: false, styled: false,
      hostDriven: mode === 'external' };
  }

  switch (mode) {
    case 'toggle':
      return { bar: true, toggle: true, collapsed: true, styled: false,
        hostDriven: false };
    case 'none':
      return { bar: false, toggle: false, collapsed: false, styled: false,
        hostDriven: false };
    case 'external':
      return { bar: false, toggle: false, collapsed: false, styled: false,
        hostDriven: true };
    case 'inline':
      return { bar: true, toggle: false, collapsed: false, styled: true,
        hostDriven: false };
  }
}
