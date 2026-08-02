/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// The manifest.json format written by solid_node/core/export.py

export type RawRotation = ['r', string, number[]];
export type RawTranslation = ['t', string[]];
export type RawOperation = RawRotation | RawTranslation;

export interface ManifestNode {
  name: string;
  type: string;
  color: string | null;
  operations: RawOperation[];
  // A rigid node has a model (path relative to the manifest) and no
  // children; a non-rigid node has children.
  model?: string;
  // The builder publishes the source mtime with each model reference.  It is
  // part of the geometry identity: a source edit can retain the same path.
  mtime?: number;
  children?: ManifestNode[];
}

export interface Manifest {
  format: string;
  version: number;
  animation: {
    fps: number;
    frames: number;
  };
  root: ManifestNode;
}
