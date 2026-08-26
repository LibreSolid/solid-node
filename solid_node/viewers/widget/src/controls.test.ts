/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// Every decision the driver chrome makes, made here where it can be
// tested (ADR-056 stage 3c, design D1): what belongs to the focused
// layer, what it is called, what a slider spans and steps by, where its
// thumb sits when the value is outside the declared travel, and which
// way the breadcrumb can go. `viewer.ts` renders what these functions
// return and decides nothing of its own -- there is no DOM test
// framework in this bench, so anything deciding must live here.

import { describe, expect, it } from 'vitest';
import {
  breadcrumb, controlLayer, displayValue, formatDisplay, navigableChildren,
  scopedIds,
} from './controls';
import { ManifestDriver, ManifestInstruction } from './types';

const motor = (): ManifestDriver => ({
  default: 8000, range: [0, 100], unit: 'ustep', dtype: 'int', scale: 0.0125,
});

const lift = (): ManifestDriver => ({
  default: 2.5, range: [0, 40], unit: 'mm', dtype: null, scale: null,
});

const free = (): ManifestDriver => ({
  default: 0, range: null, unit: 'deg', dtype: null, scale: null,
});

// One machine, shaped like the spike's: a root that declares nothing,
// two instances of one axis class, and a deeper branch so "strictly
// below the focus" has something to mean.
const drivers = (): Record<string, ManifestDriver> => ({
  'x_axis.motor': motor(),
  'x_axis.lift': free(),
  'y_axis.motor': motor(),
  'head.spindle.speed': lift(),
});

const instructions = (): Record<string, ManifestInstruction> => ({
  'x_axis.Home': { targets: { 'x_axis.motor': 0 }, duration: 2 },
  'y_axis.Home': { targets: { 'y_axis.motor': 0 }, duration: 2 },
});

const values = (): Record<string, number> => ({
  'x_axis.motor': 8000,
  'x_axis.lift': 0,
  'y_axis.motor': 8000,
  'head.spindle.speed': 2.5,
});

const layer = (focus: readonly string[] | null, overrides = {}) =>
  controlLayer({
    drivers: drivers(),
    instructions: instructions(),
    values: values(),
    focus,
    ...overrides,
  });

describe('scopedIds', () => {
  it('selects the bare ids at the document root', () => {
    const ids = scopedIds(
      ['motor', 'x_axis.motor', 'x_axis.head.motor'], null);

    expect(ids).toEqual(['motor']);
  });

  it('selects exactly the focused layer, one segment down', () => {
    const ids = scopedIds(
      ['motor', 'x_axis.motor', 'x_axis.lift', 'x_axis.head.motor',
        'y_axis.motor'],
      ['x_axis']);

    expect(ids).toEqual(['x_axis.motor', 'x_axis.lift']);
  });

  it('excludes descendants of the focused layer', () => {
    expect(scopedIds(['x_axis.head.motor'], ['x_axis'])).toEqual([]);
  });

  it('excludes another branch that merely shares a prefix string', () => {
    // `x_axis_two` starts with `x_axis` as text; segments are not text.
    expect(scopedIds(['x_axis_two.motor'], ['x_axis'])).toEqual([]);
  });

  it('excludes an ancestor of the focused layer', () => {
    expect(scopedIds(['motor'], ['x_axis'])).toEqual([]);
  });

  it('selects a deep layer by its whole path', () => {
    expect(scopedIds(['head.spindle.speed'], ['head', 'spindle']))
      .toEqual(['head.spindle.speed']);
  });
});

describe('displayValue', () => {
  it('converts native state to design units through the scale', () => {
    expect(displayValue(8000, motor())).toBe(100);
    expect(displayValue(400, motor())).toBe(5);
  });

  it('is the identity for a driver declaring no scale', () => {
    expect(displayValue(2.5, lift())).toBe(2.5);
    expect(displayValue(-7, free())).toBe(-7);
  });
});

describe('formatDisplay', () => {
  it('writes a whole design value without a decimal point', () => {
    expect(formatDisplay(100)).toBe('100');
    expect(formatDisplay(-5)).toBe('-5');
  });

  it('keeps a fraction a maker can act on', () => {
    expect(formatDisplay(0.0125)).toBe('0.0125');
    expect(formatDisplay(2.5)).toBe('2.5');
  });

  it('drops the float noise a conversion leaves behind', () => {
    // 3 microsteps of 0.0125mm is 0.037500000000000006 in binary
    // floating point, and a readout is not the place to say so.
    expect(formatDisplay(3 * 0.0125)).toBe('0.0375');
  });
});

describe('driver controls', () => {
  it('labels a control by its final segment, relative to the layer', () => {
    const control = layer(['x_axis']).drivers[0];

    expect(control.id).toBe('x_axis.motor');
    expect(control.label).toBe('motor');
  });

  it('keeps the unit on the readout, not on the label', () => {
    const control = layer(['x_axis']).drivers[0];

    expect(control.label).toBe('motor');
    expect(control.unit).toBe('ustep');
  });

  it('shows design units while holding the native value', () => {
    const control = layer(['x_axis']).drivers[0];

    expect(control.value).toBe(8000);
    expect(control.display).toBe(100);
  });

  it('spans the declared range, in design units', () => {
    const slider = layer(['x_axis']).drivers[0].slider!;

    expect(slider.min).toBe(0);
    expect(slider.max).toBe(100);
    expect(slider.position).toBe(100);
  });

  it('steps an integer driver one native unit at a time', () => {
    // Every stop converts back to a whole microstep: step = scale.
    expect(layer(['x_axis']).drivers[0].slider!.step).toBe(0.0125);
  });

  it('steps an integer driver by one when it declares no scale', () => {
    const whole: ManifestDriver = {
      default: 0, range: [0, 10], unit: 'step', dtype: 'int', scale: null,
    };
    const control = controlLayer({
      drivers: { step: whole }, instructions: {},
      values: { step: 3 }, focus: null,
    }).drivers[0];

    expect(control.slider!.step).toBe(1);
  });

  it('leaves a float driver continuous', () => {
    const control = controlLayer({
      drivers: { lift: lift() }, instructions: {},
      values: { lift: 2.5 }, focus: null,
    }).drivers[0];

    expect(control.slider!.step).toBeNull();
  });

  it('offers a numeric input when no range is declared', () => {
    // Bounds cannot be invented from a default: the maker gets an
    // honest number field instead of a slider spanning a guess.
    const control = layer(['x_axis']).drivers
      .find((one) => one.label === 'lift')!;

    expect(control.slider).toBeNull();
    expect(control.numeric).toBe(true);
  });

  it('pins the thumb and still reads the true value out of range', () => {
    const control = controlLayer({
      drivers: { 'x_axis.motor': motor() }, instructions: {},
      // -400 microsteps: 5mm the wrong side of the declared travel.
      values: { 'x_axis.motor': -400 }, focus: ['x_axis'],
    }).drivers[0];

    expect(control.slider!.position).toBe(0);
    expect(control.pinned).toBe(true);
    expect(control.display).toBe(-5);
    expect(control.value).toBe(-400);
  });

  it('pins at the far end for a value past the top of the range', () => {
    const control = controlLayer({
      drivers: { 'x_axis.motor': motor() }, instructions: {},
      values: { 'x_axis.motor': 16000 }, focus: ['x_axis'],
    }).drivers[0];

    expect(control.slider!.position).toBe(100);
    expect(control.pinned).toBe(true);
    expect(control.display).toBe(200);
  });

  it('is not pinned inside the declared travel', () => {
    expect(layer(['x_axis']).drivers[0].pinned).toBe(false);
  });

  it('falls back to the declared default when no value is held', () => {
    const control = controlLayer({
      drivers: { 'x_axis.motor': motor() }, instructions: {},
      values: {}, focus: ['x_axis'],
    }).drivers[0];

    expect(control.value).toBe(8000);
  });
});

describe('instruction controls', () => {
  it('offers one button per instruction of the focused layer', () => {
    const buttons = layer(['x_axis']).instructions;

    expect(buttons).toEqual([{ name: 'x_axis.Home', label: 'Home' }]);
  });

  it('offers the root-declared instructions at the root', () => {
    const buttons = controlLayer({
      drivers: { x: free() },
      instructions: { Home: { targets: { x: 0 }, duration: 2 } },
      values: { x: 0 }, focus: null,
    }).instructions;

    expect(buttons).toEqual([{ name: 'Home', label: 'Home' }]);
  });
});

describe('navigableChildren', () => {
  it('offers the next segment of every id strictly below the focus', () => {
    expect(navigableChildren(
      ['x_axis.motor', 'y_axis.motor', 'head.spindle.speed'], null))
      .toEqual(['head', 'x_axis', 'y_axis']);
  });

  it('names each child once, however many controls it holds', () => {
    expect(navigableChildren(
      ['x_axis.motor', 'x_axis.lift', 'x_axis.head.motor'], null))
      .toEqual(['x_axis']);
  });

  it('does not offer a child that declares controls itself', () => {
    // Focused on `x_axis`, `motor` is a slider here -- not a layer to
    // descend into.
    expect(navigableChildren(['x_axis.motor'], ['x_axis'])).toEqual([]);
  });

  it('offers a grandchild layer that does declare something', () => {
    expect(navigableChildren(['head.spindle.speed'], ['head']))
      .toEqual(['spindle']);
  });

  it('ignores ids outside the focused layer entirely', () => {
    expect(navigableChildren(['y_axis.head.motor'], ['x_axis'])).toEqual([]);
  });
});

describe('breadcrumb', () => {
  it('is the root alone when focus is the document root', () => {
    expect(breadcrumb(null, 'Machine')).toEqual([
      { label: 'Machine', path: [], current: true },
    ]);
  });

  it('names every ancestor of the focused path', () => {
    expect(breadcrumb(['head', 'spindle'], 'Machine')).toEqual([
      { label: 'Machine', path: [], current: false },
      { label: 'head', path: ['head'], current: false },
      { label: 'spindle', path: ['head', 'spindle'], current: true },
    ]);
  });
});

describe('controlLayer', () => {
  it('reaches every declaring layer through the breadcrumb children', () => {
    // The construction is the guarantee: a layer declaring anything is
    // named by some id, so descending its segments always arrives.
    const root = layer(null);

    expect(root.drivers).toEqual([]);
    expect(root.instructions).toEqual([]);
    expect(root.children).toEqual(['head', 'x_axis', 'y_axis']);

    const axis = layer(['x_axis']);
    expect(axis.drivers.map((one) => one.label)).toEqual(['motor', 'lift']);
    expect(axis.instructions.map((one) => one.label)).toEqual(['Home']);
    expect(axis.children).toEqual([]);
  });

  it('scopes back to the root layer when focus resets', () => {
    // A republish that removes the focused instance resets focus; the
    // controls are recomputed from the new focus and nothing else.
    const focused = layer(['x_axis']);
    const reset = layer(null);

    expect(focused.drivers.length).toBe(2);
    expect(reset.drivers.length).toBe(0);
    expect(reset.breadcrumb.map((one) => one.label)).toEqual(['root']);
  });

  it('shows a focused layer that declares nothing as empty but reachable', () => {
    const head = layer(['head']);

    expect(head.drivers).toEqual([]);
    expect(head.instructions).toEqual([]);
    expect(head.children).toEqual(['spindle']);
    expect(head.present).toBe(true);
  });

  it('presents nothing at all for a driverless document', () => {
    const nothing = controlLayer({
      drivers: {}, instructions: {}, values: {}, focus: null,
    });

    expect(nothing.present).toBe(false);
    expect(nothing.drivers).toEqual([]);
    expect(nothing.instructions).toEqual([]);
    expect(nothing.children).toEqual([]);
  });

  it('carries the focused path for the affordance to show', () => {
    expect(layer(['head', 'spindle']).breadcrumb.map((one) => one.path))
      .toEqual([[], ['head'], ['head', 'spindle']]);
  });
});
