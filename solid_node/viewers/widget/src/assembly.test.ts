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

import { AssemblyNavigation } from './assembly';
import { WidgetTree } from './tree';
import { ManifestNode } from './types';

const leaf = (name: string): ManifestNode => ({
  name, type: 'part', color: null, operations: [], model: `${name}.stl`, mtime: 1,
});

const root = (names: string[]): ManifestNode => ({
  name: 'root', type: 'assembly', color: null, operations: [],
  children: names.map(leaf),
});

describe('AssemblyNavigation', () => {
  it('keeps focus and hidden paths when a reconciled tree retains them', async () => {
    const tree = new WidgetTree(root(['left', 'right']), '/build/');
    await tree.loaded;
    const navigation = new AssemblyNavigation();
    navigation.setRoot(tree, ['left']);
    navigation.setVisible(tree, ['right'], false);

    await tree.reconcile(root(['left', 'right', 'added']), '/build/');
    loadAsync.mockClear();
    navigation.reconcile(tree);

    expect(navigation.root()).toEqual(['left']);
    expect(navigation.isVisible(['right'])).toBe(false);
    expect(tree.children.find((child) => child.name === 'left')!.group.visible).toBe(true);
    expect(tree.children.find((child) => child.name === 'right')!.group.visible).toBe(false);
    expect(loadAsync).not.toHaveBeenCalled();
  });

  it('returns to the document root and discards hidden paths that disappear', async () => {
    const tree = new WidgetTree(root(['left', 'right']), '/build/');
    await tree.loaded;
    const navigation = new AssemblyNavigation();
    navigation.setRoot(tree, ['left']);
    navigation.setVisible(tree, ['right'], false);

    await tree.reconcile(root(['added']), '/build/');
    navigation.reconcile(tree);

    expect(navigation.root()).toBeNull();
    expect(navigation.isVisible(['right'])).toBe(true);
    expect(tree.children[0].group.visible).toBe(true);
  });
});
