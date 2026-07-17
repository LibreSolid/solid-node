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

// OpenSCAD names that differ from JS Math
context.ln = Math.log;
context.log = (base: number, value: number) =>
  Math.log(value) / Math.log(base);
context.mod = (a: number, b: number) => a % b;

const tokenCache = new Map<string, ReturnType<typeof tokenize>>();

export function evalExpr(expression: string, time: number): number {
  let tokens = tokenCache.get(expression);
  if (!tokens) {
    tokens = tokenize(expression);
    tokenCache.set(expression, tokens);
  }
  const value = jokEvaluate(tokens, { ...context, $t: time });
  return typeof value === 'number' ? value : Number(value);
}

export function isAnimated(expression: string): boolean {
  return expression.includes('$t');
}
