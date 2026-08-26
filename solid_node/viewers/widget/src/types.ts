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

// One declared driver, as the producer publishes it. Presentation
// metadata only: `range` is never a clamp.
export interface ManifestDriver {
  default: number;
  range: number[] | null;
  unit: string | null;
  dtype: string | null;
  scale: number | null;
}

export interface Manifest {
  format: string;
  version: number;
  animation: {
    fps: number;
    frames: number;
  };
  // Every qualified driver id the document's expressions may reference.
  // A version 1 document has no table at all, and a version 2 document
  // whose tree declares no drivers has an empty one -- both mean the
  // same thing to this viewer, which evaluates `$t` and nothing else.
  drivers?: Record<string, ManifestDriver>;
  root: ManifestNode;
}
