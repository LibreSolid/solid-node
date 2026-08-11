/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// Framing is arithmetic on bounds, so it is tested without a renderer:
// three.js maths runs in node, only WebGL and OrbitControls need a
// browser.

import * as THREE from 'three';
import { describe, expect, it } from 'vitest';
import { frameBounds } from './camera';

const FOV = 50;

function unitBoxAt(center: THREE.Vector3): THREE.Box3 {
  return new THREE.Box3().setFromCenterAndSize(
    center,
    new THREE.Vector3(1, 1, 1),
  );
}

describe('frameBounds', () => {
  it('looks at the middle of the model from the established direction', () => {
    const center = new THREE.Vector3(2, -3, 4);
    const framed = frameBounds(unitBoxAt(center), FOV);

    expect(framed).not.toBeNull();
    expect(framed!.target.distanceTo(center)).toBeCloseTo(0);

    // The viewer's established vantage point, unchanged by this cycle
    const direction = framed!.position.clone().sub(center).normalize();
    expect(direction.x).toBeCloseTo(new THREE.Vector3(1, -1, 0.8)
      .normalize().x);
    expect(direction.y).toBeCloseTo(new THREE.Vector3(1, -1, 0.8)
      .normalize().y);
    expect(direction.z).toBeCloseTo(new THREE.Vector3(1, -1, 0.8)
      .normalize().z);
  });

  it('keeps the whole model between the clipping planes', () => {
    const framed = frameBounds(unitBoxAt(new THREE.Vector3()), FOV)!;
    const distance = framed.position.length();

    expect(framed.near).toBeGreaterThan(0);
    expect(framed.near).toBeLessThan(distance);
    expect(framed.far).toBeGreaterThan(distance);
  });

  it('frames a larger model from further away', () => {
    const small = frameBounds(unitBoxAt(new THREE.Vector3()), FOV)!;
    const large = frameBounds(
      new THREE.Box3().setFromCenterAndSize(
        new THREE.Vector3(),
        new THREE.Vector3(100, 100, 100),
      ),
      FOV,
    )!;

    expect(large.position.length()).toBeGreaterThan(small.position.length());
  });

  it('adopts a restored view while still clipping to the model', () => {
    const center = new THREE.Vector3(1, 1, 1);
    const view = {
      camera: new THREE.Vector3(10, 10, 10),
      target: new THREE.Vector3(1, 1, 1),
    };
    const framed = frameBounds(unitBoxAt(center), FOV, view)!;
    const fitted = frameBounds(unitBoxAt(center), FOV)!;

    expect(framed.position.distanceTo(view.camera)).toBeCloseTo(0);
    expect(framed.target.distanceTo(view.target)).toBeCloseTo(0);
    // Clipping still comes from the model, not from where the maker stood
    expect(framed.near).toBeCloseTo(fitted.near);
    expect(framed.far).toBeCloseTo(fitted.far);
  });

  it('carries a host-supplied up direction without changing clipping', () => {
    const box = unitBoxAt(new THREE.Vector3());
    const view = {
      camera: new THREE.Vector3(10, 10, 10),
      target: new THREE.Vector3(),
    };
    const baseline = frameBounds(box, FOV, view)!;
    const up = new THREE.Vector3(0, 1, 0);
    const framed = frameBounds(box, FOV, view, up)!;

    expect(framed.up.distanceTo(up)).toBeCloseTo(0);
    expect(framed.near).toBeCloseTo(baseline.near);
    expect(framed.far).toBeCloseTo(baseline.far);
  });

  it('keeps a model inside the far plane from a distant restored view', () => {
    const center = new THREE.Vector3();
    const box = unitBoxAt(center);
    const view = {
      camera: new THREE.Vector3(1000, 0, 0),
      target: center.clone(),
    };
    const framed = frameBounds(box, FOV, view)!;
    const radius = box.getSize(new THREE.Vector3()).length() / 2;

    expect(framed.position.distanceTo(view.camera)).toBeCloseTo(0);
    expect(framed.far).toBeGreaterThan(
      view.camera.distanceTo(center) + radius,
    );
  });

  it('declines to frame a model that loaded nothing', () => {
    expect(frameBounds(new THREE.Box3(), FOV)).toBeNull();
  });
});
