/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

import * as THREE from 'three';

export interface ViewerView {
  camera: THREE.Vector3;
  target: THREE.Vector3;
}

export interface FramedCamera {
  position: THREE.Vector3;
  target: THREE.Vector3;
  up: THREE.Vector3;
  near: number;
  far: number;
}

export function frameBounds(
  box: THREE.Box3,
  fov: number,
  view: ViewerView | null = null,
  up: THREE.Vector3 = new THREE.Vector3(0, 0, 1),
): FramedCamera | null {
  if (box.isEmpty()) {
    return null;
  }
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3()).length();
  const distance = (size / 2) /
    Math.tan((fov * Math.PI) / 360) * 1.2;
  const position = view?.camera.clone() ?? center.clone().addScaledVector(
    new THREE.Vector3(1, -1, 0.8).normalize(), distance,
  );
  const radius = size / 2;
  const far = view === null
    ? distance * 100
    : Math.max(distance * 100, position.distanceTo(center) + radius * 2);

  return {
    position,
    target: view?.target.clone() ?? center,
    up: up.clone(),
    near: distance / 100,
    far,
  };
}
