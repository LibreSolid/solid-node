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
