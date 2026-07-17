/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

import { evaluate } from './evaluator';

describe('evaluate', () => {
  it('evaluates a plain numeric string rotation angle', () => {
    expect(evaluate([['r', '90', [0, 0, 1]]], 0)).toEqual([
      ['r', 90, [0, 0, 1]],
    ]);
  });

  it('substitutes $t with the current time', () => {
    expect(evaluate([['r', '(360 * $t)', [0, 0, 1]]], 0.5)).toEqual([
      ['r', 180, [0, 0, 1]],
    ]);
  });

  it('maps the OpenSCAD ln() function to the natural logarithm', () => {
    expect(evaluate([['r', 'ln(1)', [0, 0, 1]]], 0)).toEqual([
      ['r', 0, [0, 0, 1]],
    ]);
  });

  it('maps the OpenSCAD mod() function to the modulo operator', () => {
    expect(evaluate([['r', 'mod(7, 3)', [0, 0, 1]]], 0)).toEqual([
      ['r', 1, [0, 0, 1]],
    ]);
  });

  it('evaluates a translation vector of numeric strings', () => {
    expect(evaluate([['t', ['1', '2', '3']]], 0)).toEqual([
      ['t', [1, 2, 3]],
    ]);
  });

  it('evaluates sin/cos with degree inputs, matching OpenSCAD semantics', () => {
    expect(evaluate([['r', 'sin(90)', [0, 0, 1]]], 0)).toEqual([
      ['r', 1, [0, 0, 1]],
    ]);
    expect(evaluate([['r', 'cos(180)', [0, 0, 1]]], 0)[0][1]).toBeCloseTo(-1);
  });

  it('evaluates asin/acos/atan/atan2 with degree outputs, matching OpenSCAD semantics', () => {
    expect(evaluate([['r', 'asin(0.5)', [0, 0, 1]]], 0)[0][1]).toBeCloseTo(30);
    expect(evaluate([['r', 'acos(0.5)', [0, 0, 1]]], 0)[0][1]).toBeCloseTo(60);
    expect(evaluate([['r', 'atan(1)', [0, 0, 1]]], 0)[0][1]).toBeCloseTo(45);
    expect(evaluate([['r', 'atan2(1, 1)', [0, 0, 1]]], 0)[0][1]).toBeCloseTo(45);
  });

  it('evaluates a composed non-linear $t expression exactly as solid_node/math.py generates it, matching its numeric-mode results', () => {
    // The literal expression string is what
    // solid_node.math.asin(0.25 * solid_node.math.sin(720.0 * $t))
    // produces (see tests/test_math.py,
    // test_composed_nonlinear_expression). The expected values at
    // each $t are solid_node.math's own NUMERIC mode evaluated at
    // that same time (720.0 * t degrees), computed in Python and
    // pasted here -- the two modes (symbolic-then-JS-evaluated vs.
    // numeric-Python) must agree.
    const expression = 'asin((0.25 * sin((720.0 * $t))))';
    const casesTPyValue: [number, number][] = [
      [0.05, 8.450002159087596],
      [0.15, 13.754614934080255],
      [0.3, -8.450002159087594],
      [0.42, -12.185766646624758],
      [0.6, 13.754614934080253],
      [0.77, -3.564519147258074],
      [0.9, -13.754614934080255],
    ];
    for (const [t, expected] of casesTPyValue) {
      const [[, actual]] = evaluate([['r', expression, [0, 0, 1]]], t);
      expect(actual).toBeCloseTo(expected as number, 6);
    }
  });

  it('passes the rotation axis through unevaluated, alongside a translation', () => {
    // The axis vector is not a string expression like the angle/translation
    // components are: it must come through byte-for-byte, untouched by
    // evaluateExpression, even when mixed with other operations.
    expect(
      evaluate(
        [
          ['r', '45', [1, -1, 0]],
          ['t', ['1', '2', '3']],
        ],
        0,
      ),
    ).toEqual([
      ['r', 45, [1, -1, 0]],
      ['t', [1, 2, 3]],
    ]);
  });
});
