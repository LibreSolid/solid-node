/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// Evaluates the raw operation expressions from the manifest (OpenSCAD
// expressions of `$t` and of qualified driver ids, e.g. "(360 * $t)" or
// "(x_axis.motor * 0.1125)") to numbers. Same approach as the dev app's
// evaluator.ts, plus token caching: expressions are re-evaluated every
// animation frame but never change.
//
// A qualified driver id is a DOTTED name, and the parser reads it as
// member access -- so the scope carries driver values as a NESTED map
// (`{x_axis: {motor: 8000}}`) and the grammar needs no extension at all
// (ADR-056 stage 3b, D1; spike/expressions/FINDINGS.md sub-question 3).
// A driver declared on the root keeps its bare name and sits at the top
// level of that map.
//
// Beside evaluation this module answers WHICH inputs an expression
// depends on, read off the same cached parse (D2). That replaces the old
// `isAnimated` substring test, which cannot survive author-chosen driver
// names: a driver called `total` would have to be looked for with
// `includes('total')`, which fires on the letters wherever they appear,
// including inside a function name. Free variables come from the parsed
// tree, so a `Call`'s callee is never a variable and a `Member` chain is
// one dotted name rather than its pieces.

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

// The animation time's name in an expression, and the one free variable
// that is not a driver id.
export const TIME_ID = '$t';

// Driver values as the expressions read them: nested by qualified id, so
// `x_axis.motor` resolves as member access. A root-declared driver is a
// number at the top level.
export type DriverScope = Record<string, number | Record<string, number>>;

export interface EvalScope {
  /** Normalized animation time, bound as `$t`. */
  time: number;
  /** The document's drivers, in NATIVE driver units. */
  drivers?: DriverScope;
}

const tokenCache = new Map<string, ReturnType<typeof tokenize>>();
const freeCache = new Map<string, ReadonlySet<string>>();

export function evalExpr(expression: string, scope: EvalScope): number {
  const value = jokEvaluate(tokensFor(expression), {
    ...context,
    ...(scope.drivers ?? {}),
    $t: scope.time,
  });
  return typeof value === 'number' ? value : Number(value);
}

/** Every input `expression` reads: `$t` and qualified driver ids.
 *
 * Read off the cached parse, so it costs one extra walk per DISTINCT
 * expression and is then cached beside the tokens. An operation is
 * time-driven iff `$t` is in this set, driver-driven iff any declared
 * driver id is, static iff the set is empty, and mixed when both.
 */
export function freeVariables(expression: string): ReadonlySet<string> {
  const cached = freeCache.get(expression);
  if (cached !== undefined) return cached;

  const found = new Set<string>();
  collectFree(tokensFor(expression), found);
  freeCache.set(expression, found);
  return found;
}

// OpenSCAD's ^ is exponentiation, while jokenizer follows JavaScript and
// evaluates it as bitwise XOR. Convert its parsed Binary nodes to pow() calls
// before caching and evaluating the expression.
//
// The two languages also disagree about which side of a leading minus ^
// falls on, and converting the operator is the only place that can be
// settled. JavaScript has no answer -- `-2 ** 2` is a syntax error there
// exactly because the conventions differ -- while OpenSCAD binds ^ tighter
// than the unary minus, as Python does, so `-2 ^ 2` is -(2^2) and not
// (-2)^2. A parsed `^` whose left operand is a negation is therefore
// rebuilt with the negation outside it. Nothing solid-node emits reaches
// this: the manifest's expressions are fully parenthesised. An expression
// written by hand does.
function powify(node: any): any {
  if (node === null || typeof node !== 'object') return node;
  if (Array.isArray(node)) return node.map(powify);

  const result: any = {};
  for (const key of Object.keys(node)) {
    result[key] = powify(node[key]);
  }
  if (result.type === 'Binary' && result.operator === '^') {
    const negated = result.left.type === 'Unary'
      && (result.left.operator === '-' || result.left.operator === '+');
    const base = negated ? result.left.target : result.left;
    const power = {
      type: 'Call',
      callee: { type: 'Variable', name: 'pow' },
      args: [base, result.right],
    };
    return negated
      ? { type: 'Unary', operator: result.left.operator, target: power }
      : power;
  }
  return result;
}

// The free-variable walk (D2). Two node kinds carry the whole point:
// a `Member` chain is ONE dotted id (`x_axis.motor`, not `x_axis` and
// `motor`), and a `Call`'s callee is a function name, never an input --
// which is what a substring test cannot tell apart.
function collectFree(node: any, found: Set<string>): void {
  if (node === null || typeof node !== 'object') return;
  if (Array.isArray(node)) {
    node.forEach((item) => collectFree(item, found));
    return;
  }

  if (node.type === 'Variable') {
    found.add(node.name);
    return;
  }
  if (node.type === 'Member') {
    const dotted = dottedName(node);
    if (dotted !== null) {
      found.add(dotted);
    } else {
      // Member access on something that is not a plain name chain: the
      // owner may still hold free variables of its own.
      collectFree(node.owner, found);
    }
    return;
  }
  if (node.type === 'Call') {
    collectFree(node.args, found);
    return;
  }

  for (const key of Object.keys(node)) {
    collectFree(node[key], found);
  }
}

/** `x_axis.motor` for a Member chain rooted in a plain name, else null. */
function dottedName(node: any): string | null {
  const parts: string[] = [];
  let current: any = node;
  while (current !== null && typeof current === 'object'
         && current.type === 'Member') {
    parts.unshift(current.name);
    current = current.owner;
  }
  if (current !== null && typeof current === 'object'
      && current.type === 'Variable') {
    parts.unshift(current.name);
    return parts.join('.');
  }
  return null;
}

function tokensFor(expression: string): ReturnType<typeof tokenize> {
  const cached = tokenCache.get(expression);
  if (cached !== undefined) return cached;

  const tokens = powify(tokenize(expression)) as ReturnType<typeof tokenize>;
  tokenCache.set(expression, tokens);
  return tokens;
}
