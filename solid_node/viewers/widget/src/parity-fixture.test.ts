/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// Cross-runtime parity, enforced (ADR-022's option 1, ADR-056 stage 3b
// design D7). Every expected value in the fixture is a PRODUCER value:
// the framework rendered the spike's two-axis machine under a numeric
// snapshot, and the same tree serialized symbolically gave the wire
// expression beside it. Nothing recomputes an expression a second way,
// so a disagreement here means the client drifted from `math.py` --
// which is exactly the defect ADR-022 recorded and could not catch.
//
// This runs against the SHIPPED module. The expression spike had to
// hand-copy `evaluator.ts` into plain JavaScript to measure parity at
// all (spike/expressions/FINDINGS.md seam 7); `parity_harness.js` is
// superseded as the parity authority by this file.
//
// Regenerate with:
//   PYTHONPATH="$PWD" python \
//     solid_node/viewers/widget/tools/generate_parity_fixture.py

import * as THREE from 'three';
import { describe, expect, it } from 'vitest';
import { evalExpr, EvalScope } from './evaluator';
import { toNative } from './drivers';
import { FlexibleShape } from './flexible';
import { ManifestDriver } from './types';
import fixture from './parity-fixture.json';

interface ParityCase {
  key: string;
  expression: string;
  scope: EvalScope;
  expected: number;
}

interface ConversionCase {
  driver: ManifestDriver;
  target: number;
  native: number;
}

interface FlexibleCase {
  name: string;
  scope: EvalScope;
  params: Record<string, number>;
  vertices: number[][];
  bbox: { min: number[]; max: number[] };
}

interface FlexibleFixture {
  corpus: string;
  node: string;
  tech: string;
  spec: Record<string, unknown>;
  expressions: Record<string, string>;
  drivers: Record<string, ManifestDriver>;
  tolerance: { binding: number; js: number };
  vertex_count: number;
  triangle_count: number;
  sentinels: number[];
  cases: FlexibleCase[];
}

const cases = fixture.cases as unknown as ParityCase[];
const conversions = fixture.conversions as unknown as ConversionCase[];
const flexible = fixture.flexible as unknown as FlexibleFixture;

// ADR-022's discipline is identical SEMANTICS with only float rounding
// between runtimes. The spike measured the worst deviation over this
// corpus at 2.5e-14; this bound is far above that and far below every
// defect it guards against (the `^` rewrite is worth up to 0.186, and
// radian trig is worth whole units).
const TOLERANCE = 1e-9;

const deviation = (parity: ParityCase): number =>
  Math.abs(evalExpr(parity.expression, parity.scope) - parity.expected);

describe('evaluator parity with the producer', () => {
  it('carries the spike corpus, `^` terms included', () => {
    expect(cases.length).toBeGreaterThan(100);
    expect(cases.filter((one) => one.expression.includes('^')).length)
      .toBeGreaterThan(0);
    expect(cases.filter((one) => one.expression.includes('$t')).length)
      .toBeGreaterThan(0);
    expect(cases.filter((one) => one.expression.includes('asin')).length)
      .toBeGreaterThan(0);
    expect(cases.filter((one) => one.expression.includes('.motor')).length)
      .toBeGreaterThan(0);
  });

  it('matches every producer value within float rounding', () => {
    const wrong = cases
      .map((one) => ({ key: one.key, delta: deviation(one) }))
      .filter((one) => !(one.delta <= TOLERANCE));

    expect(wrong).toEqual([]);
  });

  it('agrees on the degree-trig chain, the worst case in the corpus', () => {
    const trig = cases.filter((one) => one.expression.includes('asin'));

    for (const one of trig) {
      expect(deviation(one)).toBeLessThanOrEqual(TOLERANCE);
    }
  });

  it('agrees on every `^` term, which XOR would not', () => {
    const powers = cases.filter((one) => one.expression.includes('^'));

    expect(powers.length).toBeGreaterThan(0);
    for (const one of powers) {
      expect(deviation(one)).toBeLessThanOrEqual(TOLERANCE);
    }
  });

  it('agrees on the mixed $t-and-driver formula', () => {
    const mixed = cases.filter((one) =>
      one.expression.includes('$t') && one.expression.includes('.motor'));

    expect(mixed.length).toBeGreaterThan(0);
    for (const one of mixed) {
      expect(deviation(one)).toBeLessThanOrEqual(TOLERANCE);
    }
  });
});

describe('design-to-native conversion parity with Driver.native', () => {
  it('converts every producer case to the same native value', () => {
    const wrong = conversions.filter(
      (one) => toNative(one.target, one.driver) !== one.native);

    expect(wrong).toEqual([]);
  });

  it('covers integer dtypes, including the half-unit cases', () => {
    const integers = conversions.filter((one) => one.driver.dtype === 'int');

    expect(integers.length).toBeGreaterThan(0);
    for (const one of integers) {
      expect(Number.isInteger(one.native)).toBe(true);
    }
  });
});

// The BINDING seam of a flexible part. Between the two molejo
// evaluators sits one boundary this repository owns: an expression is
// evaluated here and its value handed to molejo-js, where the producer
// evaluated the same expression in Python and handed its value to
// molejo-python. Vertex-for-vertex agreement between the two evaluators
// is molejo's own parity contract, held by molejo's fixtures; what is
// held here is the binding in front of it, on the real spring of
// `tests/flexible_project/spring.py`.
//
// It runs through `FlexibleShape` -- the SHIPPED module -- so the thing
// under test is the path a mounted document actually takes, expression
// parse and buffer reuse included, and not a second arrangement of the
// same parts.

// molejo's own comparison formula (its fixtures/README.md): one number
// covers coordinates near zero and far from it.
const agrees = (actual: number, expected: number, tolerance: number): boolean =>
  Math.abs(actual - expected) <= tolerance * (1 + Math.abs(expected));

const shape = () => new FlexibleShape(flexible.node, {
  tech: flexible.tech, spec: flexible.spec, params: flexible.expressions,
}, null);

const positionsOf = (part: FlexibleShape): Float32Array =>
  (part.mesh.geometry.getAttribute('position') as THREE.BufferAttribute)
    .array as Float32Array;

describe('flexible binding parity with the producer', () => {
  it('carries a real spring at more than one binding', () => {
    expect(flexible.corpus).toBe('tests/flexible_project/spring.py');
    expect(flexible.tech).toBe('molejo');
    expect(flexible.cases.length).toBeGreaterThan(1);
    expect(Object.values(flexible.expressions)
      .some((expression) => expression.includes('valvetrain.lift'))).toBe(true);
    expect(Object.keys(flexible.drivers)).toContain('valvetrain.lift');
  });

  it('binds every parameter to the value the producer bound', () => {
    const wrong: unknown[] = [];
    for (const one of flexible.cases) {
      for (const [name, expression] of Object.entries(flexible.expressions)) {
        const value = evalExpr(expression, one.scope);
        if (!agrees(value, one.params[name], flexible.tolerance.binding)) {
          wrong.push({ case: one.name, name, value,
                       expected: one.params[name] });
        }
      }
    }

    expect(wrong).toEqual([]);
  });

  it('evaluates to the producer\'s geometry at every binding', () => {
    // ONE part across every case, so the buffers under test are the
    // reused ones and not a fresh allocation per binding.
    const part = shape();
    const wrong: unknown[] = [];

    for (const one of flexible.cases) {
      part.evaluate(one.scope);
      const positions = positionsOf(part);
      expect(positions.length).toBe(flexible.vertex_count * 3);

      flexible.sentinels.forEach((vertex, at) => {
        for (let axis = 0; axis < 3; axis += 1) {
          const actual = positions[vertex * 3 + axis];
          const expected = one.vertices[at][axis];
          if (!agrees(actual, expected, flexible.tolerance.js)) {
            wrong.push({ case: one.name, vertex, axis, actual, expected });
          }
        }
      });

      const box = part.mesh.geometry.boundingBox!;
      const bounds: [number[], number[]] = [
        [box.min.x, box.min.y, box.min.z], [box.max.x, box.max.y, box.max.z],
      ];
      [one.bbox.min, one.bbox.max].forEach((expected, side) => {
        for (let axis = 0; axis < 3; axis += 1) {
          if (!agrees(bounds[side][axis], expected[axis],
                      flexible.tolerance.js)) {
            wrong.push({ case: one.name, bbox: side === 0 ? 'min' : 'max',
                         axis, actual: bounds[side][axis],
                         expected: expected[axis] });
          }
        }
      });
    }

    expect(wrong).toEqual([]);
  });

  it('moves the coordinates while the numbering holds still', () => {
    // One case cannot show this, which is why the fixture carries
    // several: a comparison that only ever sees one binding would pass
    // on an evaluator that ignored its parameters entirely.
    const part = shape();
    const first = flexible.cases[0];
    const last = flexible.cases[flexible.cases.length - 1];

    part.evaluate(first.scope);
    const array = positionsOf(part);
    const before = Array.from(array);
    part.evaluate(last.scope);

    expect(positionsOf(part)).toBe(array);
    expect(array.length).toBe(before.length);
    expect(Array.from(array)).not.toEqual(before);
    expect(first.params).not.toEqual(last.params);
  });

  it('would catch a drift, and tolerate only float rounding', () => {
    // The comparator under test, as molejo's own suites test theirs: a
    // budget nothing can fail is a budget that proves nothing.
    const reference = flexible.cases[0].vertices[0][0];
    const budget = flexible.tolerance.js * (1 + Math.abs(reference));

    expect(agrees(reference + budget * 0.5, reference,
                  flexible.tolerance.js)).toBe(true);
    expect(agrees(reference + budget * 10, reference,
                  flexible.tolerance.js)).toBe(false);
    // A whole millimetre is what a wrong binding is worth; the budget is
    // some six orders below it.
    expect(agrees(reference + 1, reference, flexible.tolerance.js))
      .toBe(false);
  });
});
