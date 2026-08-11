/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// The decisions a mount makes before it touches the DOM: what the
// options mean when the host omits them, where meshes are fetched from,
// and which controls a presentation mode is asking for. Kept pure so
// they are testable in node, where there is no document and no WebGL.

import { describe, expect, it } from 'vitest';
import { controlPlan, resolveBaseUrl, resolveOptions } from './options';

describe('resolveOptions', () => {
  it('reproduces the published export behavior when given nothing', () => {
    const resolved = resolveOptions();

    expect(resolved.animation).toBe('inline');
    expect(resolved.time).toBe(0);
    expect(resolved.autoplay).toBe(true);
    expect(resolved.view).toBeNull();
    expect(resolved.up.toArray()).toEqual([0, 0, 1]);
    expect(resolved.fov).toBe(50);
    expect(resolved.className).toBeNull();
    expect(resolved.role).toBeNull();
    expect(resolved.ariaLabel).toBeNull();
  });

  it('keeps what the host asked for', () => {
    const resolved = resolveOptions({
      animation: 'toggle',
      time: 0.25,
      autoplay: false,
      className: 'functional-model',
      role: 'img',
      ariaLabel: 'Functional model',
      up: [0, 1, 0],
      fov: 22.5,
      view: { camera: [10, 20, 30], target: [1, 2, 3] },
    });

    expect(resolved.animation).toBe('toggle');
    expect(resolved.time).toBe(0.25);
    expect(resolved.autoplay).toBe(false);
    expect(resolved.className).toBe('functional-model');
    expect(resolved.role).toBe('img');
    expect(resolved.ariaLabel).toBe('Functional model');
    expect(resolved.up.toArray()).toEqual([0, 1, 0]);
    expect(resolved.fov).toBe(22.5);
    expect(resolved.view!.camera.toArray()).toEqual([10, 20, 30]);
    expect(resolved.view!.target.toArray()).toEqual([1, 2, 3]);
  });

  it('clamps time into the animation cycle', () => {
    expect(resolveOptions({ time: 1.5 }).time).toBe(1);
    expect(resolveOptions({ time: -1 }).time).toBe(0);
    expect(resolveOptions({ time: Number.NaN }).time).toBe(0);
  });
});

describe('resolveBaseUrl', () => {
  it('resolves meshes beside a self-contained export by default', () => {
    expect(resolveBaseUrl('https://example.test/models/demo/manifest.json'))
      .toBe('https://example.test/models/demo/');
    expect(resolveBaseUrl('/_build/viewer.json')).toBe('/_build/');
  });

  it('prefers a host-supplied root, for a snapshot served elsewhere', () => {
    expect(resolveBaseUrl('/state/viewer.json', '/artifacts/'))
      .toBe('/artifacts/');
  });

  it('keeps a supplied root joinable to a model path', () => {
    expect(resolveBaseUrl('/state/viewer.json', '/artifacts'))
      .toBe('/artifacts/');
  });

  // The shipped export page mounts this way, so a document URL naming no
  // directory must stay beside the document: an export served under a
  // subpath would otherwise request its models from the server root.
  it('resolves beside a document that names no directory', () => {
    expect(resolveBaseUrl('manifest.json')).toBe('./');
  });

  it('resolves beside such a document carrying a query string', () => {
    expect(resolveBaseUrl('manifest.json?v=2')).toBe('./');
  });
});

describe('controlPlan', () => {
  it('shows the bar inline, as a published export does', () => {
    const plan = controlPlan('inline', true);

    expect(plan.bar).toBe(true);
    expect(plan.toggle).toBe(false);
    expect(plan.collapsed).toBe(false);
    // A published export renders with no stylesheet of its own
    expect(plan.styled).toBe(true);
    expect(plan.hostDriven).toBe(false);
  });

  it('hides the bar behind a toggle the host styles', () => {
    const plan = controlPlan('toggle', true);

    expect(plan.bar).toBe(true);
    expect(plan.toggle).toBe(true);
    expect(plan.collapsed).toBe(true);
    expect(plan.styled).toBe(false);
    expect(plan.hostDriven).toBe(false);
  });

  it('builds nothing when the host wants no controls', () => {
    const plan = controlPlan('none', true);

    expect(plan.bar).toBe(false);
    expect(plan.toggle).toBe(false);
    expect(plan.hostDriven).toBe(false);
  });

  it('yields the clock to the host when animation is external', () => {
    const plan = controlPlan('external', true);

    expect(plan.bar).toBe(false);
    expect(plan.toggle).toBe(false);
    expect(plan.hostDriven).toBe(true);
  });

  it('builds no controls for a model with no $t operation', () => {
    for (const mode of ['inline', 'toggle', 'none', 'external'] as const) {
      const plan = controlPlan(mode, false);
      expect(plan.bar, mode).toBe(false);
      expect(plan.toggle, mode).toBe(false);
    }
  });
});
