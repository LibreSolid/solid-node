/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

import * as THREE from 'three';
import { describe, expect, it, vi } from 'vitest';

const { loadAsync } = vi.hoisted(() => ({
  loadAsync: vi.fn(() => Promise.resolve(new THREE.BoxGeometry())),
}));

vi.mock('three/examples/jsm/loaders/STLLoader.js', () => ({
  STLLoader: class { loadAsync = loadAsync; },
}));

import { materialForColor, WidgetTree } from './tree';
import { ManifestNode } from './types';

const leaf = (overrides: Partial<ManifestNode> = {}): ManifestNode => ({
  name: 'leaf', type: 'part', color: '#cc4444', operations: [],
  model: 'leaf.stl', mtime: 1, ...overrides,
});

const root = (children: ManifestNode[]): ManifestNode => ({
  name: 'root', type: 'assembly', color: null, operations: [], children,
});

describe('materialForColor', () => {
  it('uses the development viewer normal material when no color is supplied', () => {
    expect(materialForColor(null)).toBeInstanceOf(THREE.MeshNormalMaterial);
  });

  it('keeps the standard material for an explicit color', () => {
    expect(materialForColor('#cc4444')).toBeInstanceOf(
      THREE.MeshStandardMaterial,
    );
  });
});

describe('WidgetTree targeted updates', () => {
  it('uses model path and mtime together as geometry identity', async () => {
    const tree = new WidgetTree(root([leaf()]), '/build/');
    await tree.loaded;
    loadAsync.mockClear();

    await tree.reconcile(root([leaf()]), '/build/');
    expect(loadAsync).not.toHaveBeenCalled();

    await tree.reconcile(root([leaf({ mtime: 2 })]), '/build/');
    await tree.reconcile(root([leaf({ model: 'other.stl', mtime: 2 })]), '/build/');
    expect(loadAsync.mock.calls.map(([url]) => url)).toEqual([
      '/build/leaf.stl', '/build/other.stl',
    ]);
  });

  it('replaces only the named artifact and leaves an unknown path alone', async () => {
    const tree = new WidgetTree(root([leaf(), leaf({ name: 'other', model: 'other.stl' })]), '/build/');
    await tree.loaded;
    const otherGroup = tree.children[1].group;
    loadAsync.mockClear();

    await tree.artifactChanged('leaf.stl', '/build/');
    await tree.artifactChanged('missing.stl', '/build/');

    expect(loadAsync.mock.calls.map(([url]) => url)).toEqual(['/build/leaf.stl']);
    expect(tree.children[1].group).toBe(otherGroup);
  });

  it('keeps the old tree when fetching a changed document mesh fails', async () => {
    const tree = new WidgetTree(root([leaf()]), '/build/');
    await tree.loaded;
    const previous = tree.children[0].group;
    loadAsync.mockRejectedValueOnce(new Error('network down'));

    await expect(tree.reconcile(root([leaf({ mtime: 2 })]), '/build/'))
      .rejects.toThrow('network down');
    expect(tree.children[0].group).toBe(previous);
  });

  it('does not partially update siblings when one replacement fails', async () => {
    const tree = new WidgetTree(root([
      leaf(), leaf({ name: 'other', model: 'other.stl' }),
    ]), '/build/');
    await tree.loaded;
    const first = tree.children[0].group;
    const second = tree.children[1].group;
    loadAsync.mockResolvedValueOnce(new THREE.BoxGeometry());
    loadAsync.mockRejectedValueOnce(new Error('second failed'));

    await expect(tree.reconcile(root([
      leaf({ mtime: 2 }), leaf({ name: 'other', model: 'other.stl', mtime: 2 }),
    ]), '/build/')).rejects.toThrow('second failed');
    expect(tree.children[0].group).toBe(first);
    expect(tree.children[1].group).toBe(second);
  });

  it('does not refetch a manifest reconcile that follows an artifact update for the same artifact', async () => {
    const tree = new WidgetTree(root([leaf()]), '/build/');
    await tree.loaded;
    loadAsync.mockClear();

    await tree.artifactChanged('leaf.stl', '/build/');
    expect(loadAsync).toHaveBeenCalledTimes(1);
    loadAsync.mockClear();

    await tree.reconcile(root([leaf({ mtime: 2 })]), '/build/');
    expect(loadAsync).not.toHaveBeenCalled();
  });

  it('reconciles structure and operations without refetching unchanged geometry', async () => {
    const tree = new WidgetTree(root([leaf()]), '/build/');
    await tree.loaded;
    const retained = tree.children[0].group;
    loadAsync.mockClear();

    await tree.reconcile(root([
      leaf({ operations: [['t', ['1', '0', '0']] as const] }),
      leaf({ name: 'added', model: 'added.stl' }),
    ]), '/build/');

    expect(tree.children[0].group).toBe(retained);
    expect(tree.children[0].operations).toEqual([['t', ['1', '0', '0']]]);
    expect(loadAsync.mock.calls.map(([url]) => url)).toEqual(['/build/added.stl']);
  });
});
