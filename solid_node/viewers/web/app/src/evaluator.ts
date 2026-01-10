/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
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

  const tokens = tokenize(expression);

  const context = Object.assign({ '$t': time }, Scad2JS);

  return _evaluate(tokens, context);
}


const Scad2JS = Object.assign({}, Math, {

  // ln in OpenSCAD is the natural logarithm, equivalent to log in JS
  ln: Math.log,
  log: (base: number, value: number) => Math.log(value) / Math.log(base),

  mod: (a: number, b: number) => a % b,

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
