/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// Geometry that follows the machine, evaluated the way pose already is.
//
// A flexible node carries no mesh. It carries the analytic spec its
// evaluator reads plus one expression per shape parameter, in the same
// scope operation expressions are evaluated in (`$t` and the nested
// driver map). Evaluating shape is therefore the same mechanism as
// evaluating pose with `geometry = f(params)` where the matrix path has
// `matrix = f(params)`, and it is bounded by the same rule: a node
// recomputes only on frames where a free variable of one of its own
// expressions changed.
//
// What makes that affordable at frame rate is molejo's declared
// tessellation. Vertex count, vertex ordering and the whole index follow
// the DOCUMENT and never a parameter, so the buffers are allocated once
// per node -- by the first evaluation, which is the only call that can
// know the counts -- and every later binding refills the same
// `Float32Array` in place. Nothing is reallocated, no attribute is
// replaced, and the index is never rewritten.

import * as THREE from 'three';
import { evaluate, validate, MolejoBuffers } from 'molejo';
import { EvalScope, evalExpr, freeVariables } from './evaluator';
import { ManifestFlexible } from './types';

/** Every `tech` this package can evaluate. A document naming another one
 * is refused rather than rendered wrong -- the posture the loader
 * already takes toward an undeclared driver id. */
export const FLEXIBLE_TECHNOLOGIES: readonly string[] = ['molejo'];

export function evaluatesTech(tech: string): boolean {
  return FLEXIBLE_TECHNOLOGIES.includes(tech);
}

/** The technologies, listed for an error message. */
export function knownTechnologies(): string {
  return [...FLEXIBLE_TECHNOLOGIES].sort().join(', ');
}

/** Why the bundled evaluator cannot read `spec`, or `null` if it can.
 *
 * This viewer does not read a spec. Which documents are readable -- the
 * version they declare, the vocabulary they use -- is the evaluator's
 * question, and ADR-057 put the document through here opaquely on
 * purpose. So this asks molejo and carries its answer back verbatim,
 * which is also why the message a caller builds from it says something
 * specific rather than "invalid spec".
 *
 * Called once per node at construction, never per frame. */
export function specRefusal(spec: unknown): string | null {
  try {
    validate(spec);
    return null;
  } catch (error) {
    return error instanceof Error ? error.message : String(error);
  }
}

/** The one mesh of one flexible node, and the buffers behind it.
 *
 * Owns the spec, the parsed parameter expressions, their free-variable
 * union (this node's geometry dependency set, exactly parallel to the
 * one its operations have), the molejo buffers and the three.js
 * geometry wired onto them.
 */
export class FlexibleShape {
  readonly mesh: THREE.Mesh;

  private readonly tech: string;
  private readonly spec: Record<string, unknown>;
  private readonly geometry: THREE.BufferGeometry;
  private params: [string, string][];
  private freeVars: ReadonlySet<string> | undefined;
  // Undefined until the first evaluation: molejo derives the counts from
  // the spec, so the first call is what allocates and writes the index.
  private buffers: MolejoBuffers | undefined;

  constructor(name: string, flexible: ManifestFlexible,
              color: string | null) {
    if (!evaluatesTech(flexible.tech)) {
      throw new Error(
        `The node "${name}" is a flexible part evaluated by ` +
        `"${flexible.tech}", which this viewer cannot evaluate; it ` +
        `evaluates: ${knownTechnologies()}. Refusing it rather than ` +
        'rendering a wrong shape.',
      );
    }
    // The same refusal one step further in: a technology this viewer
    // evaluates, carrying a spec its evaluator cannot read -- a document
    // written for an older molejo, say. Caught here rather than left to
    // the first evaluate(), so it names the node at load instead of
    // surfacing as a bare evaluator error on some later frame.
    const refusal = specRefusal(flexible.spec);
    if (refusal !== null) {
      throw new Error(
        `The node "${name}" is a flexible part whose spec this viewer's ` +
        `${flexible.tech} cannot read: ${refusal}. Refusing it rather ` +
        'than failing while rendering.',
      );
    }
    this.tech = flexible.tech;
    this.spec = flexible.spec;
    this.params = parameterList(flexible);
    this.geometry = new THREE.BufferGeometry();
    // Flat shading, because that is the look every other part already
    // has: an STL arrives non-indexed, so the vertex normals computed
    // for it are per-face. This geometry is indexed and shares its rim
    // vertices between the wall and the caps, so smooth normals would
    // round the rim off and disagree with the rigid part beside it.
    // Shading from the derivatives also spares an O(V) normal pass on
    // every frame a driver moves.
    this.mesh = new THREE.Mesh(this.geometry,
                               materialForFlexible(color));
  }

  /** Every input this node's parameter expressions read, `$t` included.
   *
   * The union is the node's geometry dependency set. Computed once off
   * the evaluator's cached parse and dropped whenever a reconcile
   * replaces the expressions. */
  get free(): ReadonlySet<string> {
    if (this.freeVars === undefined) {
      const found = new Set<string>();
      for (const [, expression] of this.params) {
        for (const name of freeVariables(expression)) {
          found.add(name);
        }
      }
      this.freeVars = found;
    }
    return this.freeVars;
  }

  /** Whether `flexible` describes the same shape this already evaluates.
   *
   * Only `tech` and `spec` decide it: the parameter expressions are
   * rebindable in place, because the counts they feed are the
   * document's, not theirs. */
  describes(flexible: ManifestFlexible): boolean {
    return flexible.tech === this.tech
      && JSON.stringify(flexible.spec) === JSON.stringify(this.spec);
  }

  /** Point the same buffers at new expressions, and forget which inputs
   * the old ones read. */
  rebind(flexible: ManifestFlexible): void {
    this.params = parameterList(flexible);
    this.freeVars = undefined;
  }

  setColor(color: string | null): void {
    const previous = this.mesh.material;
    this.mesh.material = materialForFlexible(color);
    (Array.isArray(previous) ? previous : [previous])
      .forEach((material) => material.dispose());
  }

  /** Evaluate the parameters in `scope` and refill the buffers.
   *
   * The first call allocates them and wires the attributes; every later
   * one writes into the arrays already on the GPU's side of the fence. */
  evaluate(scope: EvalScope): void {
    const values: Record<string, number> = {};
    for (const [name, expression] of this.params) {
      values[name] = evalExpr(expression, scope);
    }

    const buffers = evaluate(this.spec, values, this.buffers);
    if (this.buffers === undefined) {
      this.buffers = buffers;
      this.geometry.setIndex(new THREE.BufferAttribute(buffers.index, 1));
      this.geometry.setAttribute(
        'position', new THREE.BufferAttribute(buffers.positions, 3));
    }
    const positions = this.geometry.getAttribute('position');
    positions.needsUpdate = true;
    // The camera frames on these, and a spring that changed length has
    // changed both.
    this.geometry.computeBoundingBox();
    this.geometry.computeBoundingSphere();
  }

  dispose(): void {
    this.geometry.dispose();
    const materials = Array.isArray(this.mesh.material)
      ? this.mesh.material : [this.mesh.material];
    materials.forEach((material) => material.dispose());
  }
}

function parameterList(flexible: ManifestFlexible): [string, string][] {
  // Sorted, so the values handed to the evaluator are built in one
  // order whatever order the document's object happens to hold.
  return Object.keys(flexible.params).sort()
    .map((name): [string, string] => [name, flexible.params[name]]);
}

// Kept beside the shape rather than imported from `tree.ts`, which
// imports this module: the same two materials, with the flat shading a
// swept indexed surface needs to look like the rigid parts around it.
function materialForFlexible(color: string | null): THREE.Material {
  if (color === null) {
    return new THREE.MeshNormalMaterial({ flatShading: true });
  }
  return new THREE.MeshStandardMaterial({
    color: new THREE.Color(color),
    metalness: 0.1,
    roughness: 0.6,
    flatShading: true,
  });
}
