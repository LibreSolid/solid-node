/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
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
