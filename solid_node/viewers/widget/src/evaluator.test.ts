/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

import { describe, expect, it } from 'vitest';
import { evalExpr } from './evaluator';

describe('evalExpr', () => {
  it('uses OpenSCAD degree semantics for trigonometry', () => {
    expect(evalExpr('sin(90)', 0)).toBeCloseTo(1);
    expect(evalExpr('cos(180)', 0)).toBeCloseTo(-1);
    expect(evalExpr('asin(0.5)', 0)).toBeCloseTo(30);
    expect(evalExpr('atan2(1, 1)', 0)).toBeCloseTo(45);
  });

  it('treats ^ as OpenSCAD exponentiation rather than JavaScript XOR', () => {
    expect(evalExpr('(5 ^ 2)', 0)).toBe(25);
    expect(evalExpr('(2 ^ 0.5)', 0)).toBeCloseTo(Math.SQRT2);
  });

  it('matches the V8 slider-crank piston height at its kinematic anchors', () => {
    // This is the expression exported by root/kinematics.py for r=15,
    // l=60. The crank is at TDC at t=0 and BDC at t=0.25.
    const expression =
      '((15.0 * cos((720.0 * $t))) + sqrt((3600.0 - ((15.0 * sin((720.0 * $t))) ^ 2))))';

    expect(evalExpr(expression, 0)).toBeCloseTo(75, 6);
    expect(evalExpr(expression, 0.125)).toBeCloseTo(58.09475019311126, 6);
    expect(evalExpr(expression, 0.25)).toBeCloseTo(45, 6);
  });
});
