/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  AssemblyPath,
  assemblyPathKey,
  WidgetTree,
} from './tree';

export class AssemblyNavigation {
  private focusedPath: string[] | null = null;
  private hiddenPaths = new Map<string, string[]>();

  root(): string[] | null {
    return this.focusedPath === null ? null : [...this.focusedPath];
  }

  isVisible(path: AssemblyPath): boolean {
    return !this.hiddenPaths.has(assemblyPathKey(path));
  }

  setRoot(tree: WidgetTree, path: AssemblyPath | null): void {
    if (path !== null) {
      tree.requirePath(path);
    }
    this.focusedPath = path === null ? null : [...path];
    this.apply(tree);
  }

  setVisible(tree: WidgetTree, path: AssemblyPath, visible: boolean): void {
    tree.requirePath(path);
    const key = assemblyPathKey(path);
    if (visible) {
      this.hiddenPaths.delete(key);
    } else {
      this.hiddenPaths.set(key, [...path]);
    }
    this.apply(tree);
  }

  reconcile(tree: WidgetTree): boolean {
    let rootChanged = false;
    if (this.focusedPath !== null && !tree.hasPath(this.focusedPath)) {
      this.focusedPath = null;
      rootChanged = true;
    }
    for (const [key, path] of this.hiddenPaths) {
      if (!tree.hasPath(path)) {
        this.hiddenPaths.delete(key);
      }
    }
    this.apply(tree);
    return rootChanged;
  }

  private apply(tree: WidgetTree): void {
    tree.applyVisibility(this.focusedPath, new Set(this.hiddenPaths.keys()));
  }
}
