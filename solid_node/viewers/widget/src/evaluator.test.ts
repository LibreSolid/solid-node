/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// `evalExpr` takes an evaluation SCOPE rather than a bare time (ADR-056
// stage 3b, design decision D1): a document's expressions may name
// qualified drivers beside `$t`, and a qualified id like `x_axis.motor`
// is member access to the parser, so the scope carries the driver
// values as a nested map. The existing degree-trig and `^` cases below
// are unchanged in meaning; only the call shape moved.

import { describe, expect, it } from 'vitest';
import { evalExpr, freeVariables, TIME_ID } from './evaluator';

const at = (time: number) => ({ time });

describe('evalExpr', () => {
  it('uses OpenSCAD degree semantics for trigonometry', () => {
    expect(evalExpr('sin(90)', at(0))).toBeCloseTo(1);
    expect(evalExpr('cos(180)', at(0))).toBeCloseTo(-1);
    expect(evalExpr('asin(0.5)', at(0))).toBeCloseTo(30);
    expect(evalExpr('atan2(1, 1)', at(0))).toBeCloseTo(45);
  });

  it('treats ^ as OpenSCAD exponentiation rather than JavaScript XOR', () => {
    expect(evalExpr('(5 ^ 2)', at(0))).toBe(25);
    expect(evalExpr('(2 ^ 0.5)', at(0))).toBeCloseTo(Math.SQRT2);
  });

  it('matches the V8 slider-crank piston height at its kinematic anchors', () => {
    // This is the expression exported by root/kinematics.py for r=15,
    // l=60. The crank is at TDC at t=0 and BDC at t=0.25.
    const expression =
      '((15.0 * cos((720.0 * $t))) + sqrt((3600.0 - ((15.0 * sin((720.0 * $t))) ^ 2))))';

    expect(evalExpr(expression, at(0))).toBeCloseTo(75, 6);
    expect(evalExpr(expression, at(0.125))).toBeCloseTo(58.09475019311126, 6);
    expect(evalExpr(expression, at(0.25))).toBeCloseTo(45, 6);
  });
});

describe('evalExpr over a driver scope', () => {
  it('resolves a qualified dotted id through the nested driver map', () => {
    // 8000 microsteps of a 0.0125 mm/ustep belt: 100 mm of carriage.
    expect(evalExpr('(x_axis.motor * 0.0125)', {
      time: 0,
      drivers: { x_axis: { motor: 8000 } },
    })).toBeCloseTo(100);
  });

  it('keeps sibling instances of one class apart', () => {
    const drivers = { x_axis: { motor: 8000 }, y_axis: { motor: 2000 } };

    expect(evalExpr('(x_axis.motor * 0.0125)', { time: 0, drivers }))
      .toBeCloseTo(100);
    expect(evalExpr('(y_axis.motor * 0.0125)', { time: 0, drivers }))
      .toBeCloseTo(25);
  });

  it('resolves a root-declared bare id at the top level', () => {
    expect(evalExpr('(x * 0.0125)', { time: 0, drivers: { x: 800 } }))
      .toBeCloseTo(10);
  });

  it('binds $t alongside the drivers in one mixed expression', () => {
    // The fixture machine's cover: one formula holding both.
    const expression =
      '((5.0 * cos((360.0 * $t))) + ((x_axis.motor * 0.0125) * 0.1))';

    expect(evalExpr(expression, {
      time: 0, drivers: { x_axis: { motor: 8000 } },
    })).toBeCloseTo(15);
    expect(evalExpr(expression, {
      time: 0.5, drivers: { x_axis: { motor: 8000 } },
    })).toBeCloseTo(5);
  });

  it('keeps degree trig and ^ over driver terms', () => {
    expect(evalExpr('asin((0.25 * sin((x_axis.motor * 0.1125))))', {
      time: 0, drivers: { x_axis: { motor: 800 } },
    })).toBeCloseTo(Math.asin(0.25 * Math.sin(90 * Math.PI / 180)) * 180 / Math.PI);

    expect(evalExpr('(sqrt((400.0 - ((0.01 * (x_axis.motor * 0.1125)) ^ 2))) * 0.1)', {
      time: 0, drivers: { x_axis: { motor: 8000 } },
    })).toBeCloseTo(Math.sqrt(400 - Math.pow(0.01 * 900, 2)) * 0.1);
  });
});

describe('evalExpr over a leading negative term', () => {
  // A unary minus binds TIGHTER than the arithmetic beside it, in
  // OpenSCAD as in JavaScript: `-100 + x` is `(-100) + x` and never
  // `-(100 + x)`. Nothing in this module writes the expressions it
  // reads -- they arrive in a published document -- so a parser that
  // gets this backwards silently returns a different number for an
  // expression the emitter, and every other reader, agrees about.
  //
  // Found from Metamaquina2: the machine publishes where its filament
  // enters the extruder as an expression whose first term is the
  // carriage's own rest position, which is negative. The strand tracked
  // the print head BACKWARDS about the middle of the X travel -- the
  // signature of a flipped coefficient -- while the model's own
  // geometry was right at every position.
  it('subtracts a leading negative literal rather than negating the sum', () => {
    expect(evalExpr('(-100.0 + x)', { time: 0, drivers: { x: 100 } }))
      .toBeCloseTo(0);
    expect(evalExpr('(-100.0 + x)', { time: 0, drivers: { x: 0 } }))
      .toBeCloseTo(-100);
  });

  it('keeps a leading negative term out of the products beside it', () => {
    expect(evalExpr('(-2 * 3 + 4)', at(0))).toBeCloseTo(-2);
    expect(evalExpr('(-a - b)', { time: 0, drivers: { a: 5, b: 3 } }))
      .toBeCloseTo(-8);
  });

  it('reads the whole entry expression Metamaquina2 publishes', () => {
    // Verbatim from the machine's serialized document: where the free
    // run of filament ends, in the strand's own frame, as a function of
    // the X driver. It is `400 - x`, so the strand's end follows the
    // carriage and does not mirror it.
    const entry = '(-((((-100.0 + x) - -100.0) + 0) - 400))';

    for (const [x, expected] of [[-100, 500], [0, 400], [100, 300]]) {
      expect(evalExpr(entry, { time: 0, drivers: { x } })).toBeCloseTo(expected);
    }
  });

  it('still negates a parenthesised sum, which says so', () => {
    expect(evalExpr('(-(100.0 + x))', { time: 0, drivers: { x: 100 } }))
      .toBeCloseTo(-200);
  });

  it('keeps ^ as exponentiation under a leading minus', () => {
    // OpenSCAD binds ^ tighter than unary minus, so this is -(2^2).
    expect(evalExpr('(-2 ^ 2)', at(0))).toBeCloseTo(-4);
  });
});

describe('freeVariables', () => {
  it('finds nothing in a static expression', () => {
    expect([...freeVariables('90')]).toEqual([]);
    expect([...freeVariables('(5 ^ 2)')]).toEqual([]);
  });

  it('finds $t alone in a time-driven expression', () => {
    expect([...freeVariables('(360.0 * $t)')]).toEqual([TIME_ID]);
  });

  it('collapses a Member chain to its dotted qualified name', () => {
    expect([...freeVariables('(x_axis.motor * 0.1125)')])
      .toEqual(['x_axis.motor']);
  });

  // The producer writes every value into the document through Python's
  // str(), which prints exponent notation below 1e-4 and at or above
  // 1e16. The OpenFlexure Microscope's steppers advance
  // 6.103515625e-05 mm of lead screw per step, so every one of its
  // placement expressions carries such a literal -- and the tokenizer
  // used to stop at the `e`, refusing the whole document.
  it('reads a numeric literal in exponent notation', () => {
    expect(evalExpr('6.103515625e-05', at(0))).toBe(6.103515625e-05);
    expect(evalExpr('1.592040838891559e-15', at(0))).toBe(1.592040838891559e-15);
    expect(evalExpr('2e3', at(0))).toBe(2000);
    expect(evalExpr('1.5E+2', at(0))).toBe(150);
    expect(evalExpr('1e21', at(0))).toBe(1e21);
  });

  it('reads an exponent literal inside an expression', () => {
    const drivers = { x_motor: -8192 };
    expect(evalExpr('((-x_motor) * 6.103515625e-05)', { time: 0, drivers }))
      .toBeCloseTo(0.5, 12);
    expect(evalExpr('(1.0 - 1.592040838891559e-15)', at(0)))
      .toBe(1.0 - 1.592040838891559e-15);
    expect(evalExpr('sqrt(4e0)', at(0))).toBeCloseTo(2);
  });

  it('keeps every digit rather than round-tripping through a float', () => {
    // A rewrite that reconstructed the number and printed it back could
    // lose the tail; these are the digits the producer wrote.
    expect(evalExpr('1.2345678901234567e-7', at(0)))
      .toBe(1.2345678901234567e-7);
  });

  it('leaves a name that merely carries the exponent marker alone', () => {
    expect(evalExpr('(e5 * 2)', { time: 0, drivers: { e5: 3 } })).toBe(6);
    expect(evalExpr('(stage.e10 * 2)', { time: 0, drivers: { stage: { e10: 4 } } }))
      .toBe(8);
    expect(evalExpr('exp(0)', at(0))).toBe(1);
    expect([...freeVariables('(e5 * 2)')]).toEqual(['e5']);
  });

  it('separates a mixed expression into both of its free variables', () => {
    const found = freeVariables(
      '((5.0 * cos((360.0 * $t))) + ((x_axis.motor * 0.0125) * 0.1))',
    );

    expect([...found].sort()).toEqual(['$t', 'x_axis.motor']);
  });

  it('never counts a function name as a variable', () => {
    expect([...freeVariables('asin((0.25 * sin((x_axis.motor * 0.1125))))')])
      .toEqual(['x_axis.motor']);
    expect([...freeVariables('sqrt((3600.0 - 1))')]).toEqual([]);
  });

  it('does not find a driver named `total` by substring', () => {
    // The defect the substring test cannot survive: an author may name a
    // driver `total`, and `includes('total')` then fires on any function
    // or variable whose name merely contains those letters.
    const callee = freeVariables('(total_of(3) * 2)');
    expect([...callee]).toEqual([]);

    const other = freeVariables('(subtotal * 2)');
    expect([...other]).toEqual(['subtotal']);
    expect(other.has('total')).toBe(false);

    expect([...freeVariables('(total * 2)')]).toEqual(['total']);
  });
});
