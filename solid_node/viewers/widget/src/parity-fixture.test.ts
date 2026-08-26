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

import { describe, expect, it } from 'vitest';
import { evalExpr, EvalScope } from './evaluator';
import { toNative } from './drivers';
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

const cases = fixture.cases as unknown as ParityCase[];
const conversions = fixture.conversions as unknown as ConversionCase[];

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
