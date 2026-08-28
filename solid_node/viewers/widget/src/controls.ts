/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// What the driver chrome shows, decided as pure data (ADR-056 stage 3c,
// design D1). Nothing here touches the DOM, three.js or the driver
// store: it reads the document's two tables, the focused assembly path
// and the current NATIVE values, and returns the controls a layer has.
// `viewer.ts` renders exactly this and calls the same public driving API
// a host would -- which is what keeps the on-screen and programmatic
// doors indistinguishable, and what lets every decision below be tested
// in plain node, where there is no document object at all.
//
// Two unit systems meet here, deliberately: state and `default` are
// NATIVE (microsteps), while `range` and instruction targets are DESIGN
// units (millimetres). The chrome lives in design units because that is
// what a maker reads, and converts through `scale` exactly once --
// display for the readout, `toNative` on the way back in.

import { ManifestDriver, ManifestInstruction } from './types';

/** An assembly path: the same segments that qualify a driver id. */
export type ControlPath = readonly string[];

/** Where a slider's thumb sits and how far it can travel, in DESIGN
 * units. `step` is null for a continuous (float) driver. */
export interface SliderPlan {
  min: number;
  max: number;
  step: number | null;
  position: number;
}

export interface DriverControl {
  /** The qualified id: what `setDriver` and `driver` are called with. */
  id: string;
  /** The final segment -- the name relative to the focused layer. */
  label: string;
  /** The declared unit, for the readout beside the value. */
  unit: string | null;
  /** The current value in NATIVE units, as the store holds it. */
  value: number;
  /** The same value in DESIGN units: what the readout shows. */
  display: number;
  /** The slider, or null when the driver declares no range. */
  slider: SliderPlan | null;
  /** True when there is no range and the value needs a number field. */
  numeric: boolean;
  /** True when the value lies outside the declared travel: the thumb is
   * pinned at an end while the readout stays truthful. */
  pinned: boolean;
  /** The declaration, for the conversion back to native units. */
  driver: ManifestDriver;
}

export interface InstructionControl {
  /** The qualified name: what `trigger` is called with. */
  name: string;
  label: string;
}

export interface BreadcrumbSegment {
  label: string;
  /** The focus this segment moves to; `[]` is the document root. */
  path: string[];
  current: boolean;
}

export interface ControlLayer {
  /** Whether this document has driver chrome at all. */
  present: boolean;
  breadcrumb: BreadcrumbSegment[];
  drivers: DriverControl[];
  instructions: InstructionControl[];
  /** The next path segments that lead to a declaring layer. */
  children: string[];
}

export interface ControlsInput {
  drivers: Record<string, ManifestDriver>;
  instructions: Record<string, ManifestInstruction>;
  /** Current NATIVE values by qualified id; a missing one reads its
   * declared default, which is what the store would hold anyway. */
  values: Record<string, number>;
  focus: ControlPath | null;
  /** What the root segment of the breadcrumb is called. */
  rootLabel?: string;
}

const DEFAULT_ROOT_LABEL = 'root';

function segments(id: string): string[] {
  return id.split('.');
}

/** The ids belonging to the focused layer: exactly the focus path's
 * segments plus one more (design D2). Root focus selects the bare ids.
 *
 * Segment equality, never string prefixes: `x_axis_two.motor` starts
 * with `x_axis` as text and belongs to another branch entirely.
 */
export function scopedIds(ids: readonly string[],
                          focus: ControlPath | null): string[] {
  const path = focus ?? [];
  return ids.filter((id) => {
    const parts = segments(id);
    return parts.length === path.length + 1
      && path.every((segment, index) => parts[index] === segment);
  });
}

/** A native value in design units: the identity when no scale is
 * declared, because then the two readings are the same number. */
export function displayValue(value: number, driver: ManifestDriver): number {
  return driver.scale === null || driver.scale === undefined
    ? value : value * driver.scale;
}

/** The distinct next segments strictly below the focus, from whichever
 * table names them (design D8).
 *
 * "Strictly below" is what makes this the breadcrumb rather than the
 * control list: an id one segment down is a slider or a button here,
 * and only an id two or more segments down names a layer to descend
 * into. Because every declaring layer is named by some id, this reaches
 * all of them, and a child with nothing declared beneath it is never
 * named -- the spec's "need not be offered", by construction.
 */
export function navigableChildren(ids: readonly string[],
                                  focus: ControlPath | null): string[] {
  const path = focus ?? [];
  const found = new Set<string>();
  for (const id of ids) {
    const parts = segments(id);
    if (parts.length < path.length + 2) {
      continue;
    }
    if (!path.every((segment, index) => parts[index] === segment)) {
      continue;
    }
    found.add(parts[path.length]);
  }
  return [...found].sort();
}

/** The focused path from the document root, one segment per step. */
export function breadcrumb(focus: ControlPath | null,
                           rootLabel = DEFAULT_ROOT_LABEL): BreadcrumbSegment[] {
  const path = focus ?? [];
  const trail: BreadcrumbSegment[] = [
    { label: rootLabel, path: [], current: path.length === 0 },
  ];
  path.forEach((segment, index) => {
    trail.push({
      label: segment,
      path: path.slice(0, index + 1) as string[],
      current: index === path.length - 1,
    });
  });
  return trail;
}

/** A design-unit value as an EDITABLE string, for a field the maker
 * types into.
 *
 * Rounded to a precision no machine this chrome drives can act below,
 * then written without trailing zeros: a conversion through a scale
 * leaves binary-float noise (3 microsteps of 0.0125mm is
 * 0.037500000000000006), and a readout claiming that precision would be
 * lying about the machine rather than reporting it. The shortest
 * faithful form is what a field wants -- rewriting a maker's `2.5` as
 * `2.5000` fights the hand that typed it.
 */
export function formatDisplay(value: number): string {
  return String(Number(value.toFixed(6)));
}

/** A design-unit value as a READ string, for the output beside a
 * slider.
 *
 * The opposite job to `formatDisplay`, and why they are two functions:
 * a readout changes sixty times a second under a drag, so it wants one
 * constant SHAPE rather than the shortest one. Fixed decimals, trailing
 * zeros kept, so the digit count never changes; `toFixed` rounds on the
 * way, which handles the same conversion noise as above. Four places is
 * finer than any millimetre-scale machine here resolves and coarser
 * than binary noise.
 */
export function formatReadout(value: number): string {
  return value.toFixed(READOUT_DECIMALS);
}

/** How many decimal places a readout writes -- the whole of the fixed
 * precision policy, in one place, if it ever needs to vary by driver. */
export const READOUT_DECIMALS = 4;

function sliderPlan(display: number, driver: ManifestDriver): SliderPlan | null {
  const range = driver.range;
  if (range === null || range === undefined || range.length !== 2) {
    return null;
  }
  const [min, max] = range;
  // An integer driver stops on whole native units, so one step is worth
  // one native unit in design units: the scale itself, or 1 when native
  // and design units are the same thing. A float driver is continuous.
  const step = driver.dtype !== 'int' ? null
    : (driver.scale === null || driver.scale === undefined ? 1 : driver.scale);
  return {
    min, max, step,
    position: Math.min(Math.max(display, min), max),
  };
}

/** One driver's control, at one native value. Exported because a live
 * value change re-derives exactly this and nothing else. */
export function driverControl(id: string, driver: ManifestDriver,
                              value: number): DriverControl {
  const display = displayValue(value, driver);
  const slider = sliderPlan(display, driver);
  return {
    id,
    label: segments(id).slice(-1)[0],
    unit: driver.unit,
    value,
    display,
    slider,
    numeric: slider === null,
    // The range bounds the thumb, never the value: a machine driven
    // past its travel says so instead of pretending it stopped.
    pinned: slider !== null && slider.position !== display,
    driver,
  };
}

/** Everything the chrome shows for one focused layer. */
export function controlLayer(input: ControlsInput): ControlLayer {
  const driverIds = Object.keys(input.drivers);
  const instructionNames = Object.keys(input.instructions);
  const known = [...driverIds, ...instructionNames];
  return {
    // Instructions move drivers, so a document with no drivers has no
    // chrome to show and looks exactly as it did before this change.
    present: driverIds.length > 0,
    breadcrumb: breadcrumb(input.focus, input.rootLabel),
    drivers: scopedIds(driverIds, input.focus).map((id) => driverControl(
      id, input.drivers[id],
      input.values[id] ?? input.drivers[id].default,
    )),
    instructions: scopedIds(instructionNames, input.focus).map((name) => ({
      name, label: segments(name).slice(-1)[0],
    })),
    children: navigableChildren(known, input.focus),
  };
}
