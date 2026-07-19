/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// Evaluates the raw operation expressions from the manifest (OpenSCAD
// expressions of $t, e.g. "(360 * $t)") to numbers. Same approach as
// the dev app's evaluator.ts, plus token caching: expressions are
// re-evaluated every animation frame but never change.

import { tokenize, evaluate as jokEvaluate } from 'jokenizer';

// Math's built-in properties are non-enumerable, so a plain
// Object.assign({}, Math) would copy nothing -- walk them explicitly.
const context: Record<string, unknown> = {};
for (const name of Object.getOwnPropertyNames(Math)) {
  context[name] = Math[name as keyof Math];
}

// OpenSCAD names and semantics that differ from JS Math.
context.ln = Math.log;
context.log = (base: number, value: number) =>
  Math.log(value) / Math.log(base);
context.mod = (a: number, b: number) => a % b;
context.sin = (degrees: number) => Math.sin(degrees * Math.PI / 180);
context.cos = (degrees: number) => Math.cos(degrees * Math.PI / 180);
context.tan = (degrees: number) => Math.tan(degrees * Math.PI / 180);
context.asin = (value: number) => Math.asin(value) * 180 / Math.PI;
context.acos = (value: number) => Math.acos(value) * 180 / Math.PI;
context.atan = (value: number) => Math.atan(value) * 180 / Math.PI;
context.atan2 = (y: number, x: number) => Math.atan2(y, x) * 180 / Math.PI;

const tokenCache = new Map<string, ReturnType<typeof tokenize>>();

export function evalExpr(expression: string, time: number): number {
  const value = jokEvaluate(tokensFor(expression), { ...context, $t: time });
  return typeof value === 'number' ? value : Number(value);
}

export function isAnimated(expression: string): boolean {
  return expression.includes('$t');
}

// OpenSCAD's ^ is exponentiation, while jokenizer follows JavaScript and
// evaluates it as bitwise XOR. Convert its parsed Binary nodes to pow() calls
// before caching and evaluating the expression.
function powify(node: any): any {
  if (node === null || typeof node !== 'object') return node;
  if (Array.isArray(node)) return node.map(powify);

  const result: any = {};
  for (const key of Object.keys(node)) {
    result[key] = powify(node[key]);
  }
  if (result.type === 'Binary' && result.operator === '^') {
    return {
      type: 'Call',
      callee: { type: 'Variable', name: 'pow' },
      args: [result.left, result.right],
    };
  }
  return result;
}

function tokensFor(expression: string): ReturnType<typeof tokenize> {
  const cached = tokenCache.get(expression);
  if (cached !== undefined) return cached;

  const tokens = powify(tokenize(expression)) as ReturnType<typeof tokenize>;
  tokenCache.set(expression, tokens);
  return tokens;
}
