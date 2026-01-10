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

// The "Raw" operations come as strings and have to be evaluated to numbers
type RotationRawOperation = [
  "r", string, [number, number, number]
];

type TranslationRawOperation = [
  "t", [string, string, string]
];

export type RawOperation = RotationRawOperation | TranslationRawOperation;

export type RotationOperation = [
  "r", number, [number, number, number]
];

export type TranslationOperation = [
  "t", [number, number, number]
];

export type Operation = RotationOperation | TranslationOperation;
