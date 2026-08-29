/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// molejo ships as plain ESM with no type declarations, so the part of it
// this package uses is declared here. Only `evaluate` and its buffer
// contract are named: the spec itself is the evaluator's business and
// travels through this module opaquely, exactly as `ManifestFlexible`
// says.

declare module 'molejo' {
  /** What one evaluation of a spec produces, and what the next one
   * refills. `vertexCount` and `triangleCount` follow the DOCUMENT
   * alone -- never a parameter -- which is what lets the same arrays
   * serve every binding. */
  export interface MolejoBuffers {
    positions: Float32Array;
    index: Uint32Array;
    vertexCount: number;
    triangleCount: number;
  }

  /** Spec plus parameter values to vertex buffers.
   *
   * Called without `buffers` it allocates them and writes the index;
   * called with the return value of a previous evaluation of the SAME
   * spec it refills `positions` in place, leaves `index` untouched, and
   * hands the same object back. Nothing is written on the way to
   * failing. */
  export function evaluate(
    spec: unknown,
    values: Record<string, number>,
    buffers?: MolejoBuffers,
  ): MolejoBuffers;

  export class EvaluationError extends Error {}
  export class NotImplementedError extends EvaluationError {}
  export class SpecError extends Error {}

  export const SPEC_VERSION: number;
  export const VERSION: string;

  export function parseSpec(spec: unknown): Record<string, unknown>;
  export function validate(spec: unknown): void;
  export function parameterNames(spec: unknown): string[];
}
