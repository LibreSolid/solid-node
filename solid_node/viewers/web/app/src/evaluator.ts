/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

import { tokenize, evaluate as _evaluate } from 'jokenizer';
import { RawOperation, Operation, TranslationOperation, RotationOperation } from './operations.d';

export const evaluate = (operations: RawOperation[], time: number): Operation[] => {
  return operations.map((operation) => {
    if (operation[0] === "r") {
      return ["r",
              evaluateExpression(operation[1], time),
              operation[2],
             ] as RotationOperation;
    }
    if (operation[0] === "t") {
      return ["t",
              operation[1].map(t => evaluateExpression(t, time)),
             ] as TranslationOperation;
    }
    throw Error("Programming error, this should be unreachable");

  });
}

const evaluateExpression = (expression: string, time: number): number => {

  const tokens = powify(tokenize(expression));

  const context = Object.assign({ '$t': time }, Scad2JS);

  return _evaluate(tokens, context);
}

// In OpenSCAD, ^ is exponentiation; jokenizer evaluates it as JS
// bitwise XOR. Rewrite every ^ Binary node into a pow() Call before
// evaluation (pow is in Scad2JS via the Math copy below).
const powify = (node: any): any => {
  if (node === null || typeof node !== 'object') return node;
  if (Array.isArray(node)) return node.map(powify);
  const out: any = {};
  for (const key of Object.keys(node)) out[key] = powify(node[key]);
  if (out.type === 'Binary' && out.operator === '^') {
    return {
      type: 'Call',
      callee: { type: 'Variable', name: 'pow' },
      args: [out.left, out.right],
    };
  }
  return out;
}

// Math's own properties are non-enumerable, so Object.assign (and
// spread) copy NONE of them -- enumerate explicitly, or sqrt() et al.
// are undefined in the evaluation context.
const JsMath: { [name: string]: any } = {};
for (const name of Object.getOwnPropertyNames(Math)) {
  JsMath[name] = (Math as any)[name];
}

const Scad2JS = Object.assign(JsMath, {

  // ln in OpenSCAD is the natural logarithm, equivalent to log in JS
  ln: Math.log,
  log: (base: number, value: number) => Math.log(value) / Math.log(base),

  mod: (a: number, b: number) => a % b,

  // OpenSCAD's trig builtins are degree-in/degree-out, unlike JS's
  // Math.* (radians). Plugging Math straight into this context (as
  // the JsMath copy above does) silently evaluated $t expressions
  // wrong the instant a build put a genuinely non-linear function
  // (e.g. asin()) of $t into a rotation/translation expression --
  // solid_node/math.py generates exactly these degree-semantics
  // calls (see solid_node/math.py), so the frontend evaluator must
  // match it function-for-function.
  sin: (degrees: number) => Math.sin(degrees * Math.PI / 180),
  cos: (degrees: number) => Math.cos(degrees * Math.PI / 180),
  tan: (degrees: number) => Math.tan(degrees * Math.PI / 180),
  asin: (x: number) => Math.asin(x) * 180 / Math.PI,
  acos: (x: number) => Math.acos(x) * 180 / Math.PI,
  atan: (x: number) => Math.atan(x) * 180 / Math.PI,
  atan2: (y: number, x: number) => Math.atan2(y, x) * 180 / Math.PI,

  // Functions below are not implemented
  //
  // concat: (arr1: any[], arr2: any[]) => [...arr1, ...arr2],
  // cross: (v1: number[], v2: number[]) => { /* Cross product implementation */ },
  // lookup: (value: number, pairs: [number, number][]) => { /* Lookup implementation */ },
  // len: (value: any) => { /* Length calculation for arrays or strings */ },
  // let: (variables: object, expression: () => number) => { /* Implement let functionality */ },
  // norm: (v: number[]) => { /* Vector normalization */ },
  // rands: (min: number, max: number, n: number, seed: number) => { /* Random number generation */ },
});
