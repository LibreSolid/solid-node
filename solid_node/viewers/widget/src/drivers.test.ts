/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// The driving half of the viewer handle (ADR-056 stage 3b): one driver
// state per mount, in NATIVE driver units -- the units the expressions
// consume and the units `default`/`range` declare. A host converts for
// presentation from the published `scale`/`unit`; the API does not,
// because `driver(id)` and what the expressions read would otherwise
// disagree and integer dtypes would round twice (design D3).

import { describe, expect, it, vi } from 'vitest';
import { DriverStore, toNative } from './drivers';
import { ManifestDriver, ManifestInstruction } from './types';

const TABLE: Record<string, ManifestDriver> = {
  'x_axis.motor': {
    default: 8000, range: [0, 8000], unit: 'ustep', dtype: 'int',
    scale: 0.0125,
  },
  'y_axis.motor': {
    default: 2000, range: [0, 8000], unit: 'ustep', dtype: 'int',
    scale: 0.0125,
  },
  spin: { default: 0, range: null, unit: 'deg', dtype: null, scale: null },
};

const INSTRUCTIONS: Record<string, ManifestInstruction> = {
  'x_axis.Home': { targets: { 'x_axis.motor': 0.0 }, duration: 2.0 },
  'y_axis.Home': { targets: { 'y_axis.motor': 0.0 }, duration: 2.0 },
  // 100 mm of travel: 8000 microsteps at 0.0125 mm each.
  'x_axis.Park': { targets: { 'x_axis.motor': 100.0 }, duration: 1.0 },
  Turn: { targets: { spin: 90 }, duration: 1.0 },
  Both: {
    targets: { 'x_axis.motor': 0.0, 'y_axis.motor': 0.0 },
    duration: 1.0,
  },
};

class Clock {
  now = 0;
  read = () => this.now;
  advance(seconds: number) { this.now += seconds; }
}

const store = (clock = new Clock()) =>
  new DriverStore(TABLE, INSTRUCTIONS, clock.read);

describe('DriverStore state', () => {
  it('opens at the table\'s declared defaults', () => {
    const drivers = store();

    expect(drivers.driver('x_axis.motor')).toBe(8000);
    expect(drivers.driver('y_axis.motor')).toBe(2000);
    expect(drivers.driver('spin')).toBe(0);
  });

  it('publishes the table entries verbatim', () => {
    expect(store().drivers()).toEqual(TABLE);
  });

  it('does not hand out its own table to be edited', () => {
    const drivers = store();

    drivers.drivers()['x_axis.motor'].default = 1;

    expect(drivers.drivers()['x_axis.motor'].default).toBe(8000);
  });

  it('binds a set value and reports it back', () => {
    const drivers = store();

    drivers.setDriver('x_axis.motor', 1600);

    expect(drivers.driver('x_axis.motor')).toBe(1600);
    expect(drivers.driver('y_axis.motor')).toBe(2000);
  });

  it('scopes qualified ids as a nested map and bare ids at the top', () => {
    const drivers = store();

    drivers.setDriver('x_axis.motor', 1600);
    drivers.setDriver('spin', 45);

    expect(drivers.scope()).toEqual({
      x_axis: { motor: 1600 },
      y_axis: { motor: 2000 },
      spin: 45,
    });
  });

  it('binds a value past the declared range verbatim', () => {
    // A crash scenario drives past travel. `range` is presentation
    // metadata; nothing in this framework clamps to it.
    const drivers = store();

    drivers.setDriver('x_axis.motor', -4000);

    expect(drivers.driver('x_axis.motor')).toBe(-4000);
  });

  it('fails loudly on an unknown id, listing the declared ones', () => {
    const drivers = store();

    expect(() => drivers.setDriver('z_axis.motor', 0))
      .toThrow(/z_axis\.motor/);
    expect(() => drivers.setDriver('z_axis.motor', 0))
      .toThrow(/x_axis\.motor.*y_axis\.motor/);
    expect(() => drivers.driver('z_axis.motor')).toThrow(/z_axis\.motor/);
  });

  it('changes nothing when an unknown id is refused', () => {
    const drivers = store();
    const seen: string[] = [];
    drivers.onDriverChange((id) => seen.push(id));

    expect(() => drivers.setDriver('z_axis.motor', 0)).toThrow();

    expect(seen).toEqual([]);
    expect(drivers.scope()).toEqual({
      x_axis: { motor: 8000 }, y_axis: { motor: 2000 }, spin: 0,
    });
  });

  it('marks only the set driver dirty for the next frame', () => {
    const drivers = store();

    drivers.setDriver('x_axis.motor', 1600);

    expect([...drivers.tick()]).toEqual(['x_axis.motor']);
    expect([...drivers.tick()]).toEqual([]);
  });
});

describe('DriverStore change notification', () => {
  it('calls listeners synchronously on setDriver', () => {
    const drivers = store();
    const listener = vi.fn();
    drivers.onDriverChange(listener);

    drivers.setDriver('x_axis.motor', 1600);

    expect(listener).toHaveBeenCalledWith('x_axis.motor', 1600);
  });

  it('does not repeat the synchronous call on the following frame', () => {
    const drivers = store();
    const listener = vi.fn();
    drivers.onDriverChange(listener);

    drivers.setDriver('x_axis.motor', 1600);
    drivers.tick();

    expect(listener).toHaveBeenCalledTimes(1);
  });

  it('stops calling an unsubscribed listener', () => {
    const drivers = store();
    const listener = vi.fn();
    const unsubscribe = drivers.onDriverChange(listener);

    unsubscribe();
    drivers.setDriver('x_axis.motor', 1600);

    expect(listener).not.toHaveBeenCalled();
  });

  it('says nothing when a set does not move the value', () => {
    const drivers = store();
    const listener = vi.fn();
    drivers.onDriverChange(listener);

    drivers.setDriver('x_axis.motor', 8000);

    expect(listener).not.toHaveBeenCalled();
    expect([...drivers.tick()]).toEqual([]);
  });
});

// Triggering an instruction is the degenerate simulator ADR-056 planned
// as the seat of the future G-code interpreter (design D4): design-unit
// targets converted to native exactly as `Driver.native` does, then one
// linear ramp per target driver, advanced on wall-clock elapsed time.
// Intermediate values are sampling; the endpoints are contract.
describe('toNative', () => {
  const int = TABLE['x_axis.motor'];

  it('divides a design-unit target by the declared scale', () => {
    expect(toNative(100.0, int)).toBe(8000);
    expect(toNative(0.0, int)).toBe(0);
  });

  it('rounds an integer driver to the nearest native unit', () => {
    expect(toNative(0.01, int)).toBe(1);       // 0.8 usteps
    expect(toNative(-0.01, int)).toBe(-1);
  });

  it('rounds a half native unit to even, as Python does', () => {
    // Python: round(0.00625/0.0125) == 0, and round(0.01875/0.0125) == 1
    // because that quotient is 1.4999999999999998 rather than 1.5 --
    // matching the producer means matching its arithmetic, not an
    // idealized decimal.
    expect(toNative(0.00625, int)).toBe(0);
    expect(toNative(0.01875, int)).toBe(1);

    const whole = { ...int, scale: null };
    expect(toNative(1.5, whole)).toBe(2);
    expect(toNative(2.5, whole)).toBe(2);
    expect(toNative(-1.5, whole)).toBe(-2);
    expect(toNative(-0.5, whole)).toBe(0);
  });

  it('leaves a scaleless float driver alone', () => {
    expect(toNative(90, TABLE.spin)).toBe(90);
    expect(toNative(12.5, TABLE.spin)).toBe(12.5);
  });
});

describe('DriverStore instructions', () => {
  it('publishes the declared instructions verbatim', () => {
    expect(store().instructions()).toEqual(INSTRUCTIONS);
  });

  it('fails loudly on an unknown name, listing the declared ones', () => {
    const drivers = store();

    expect(() => drivers.trigger('x_axis.Retract')).toThrow(/x_axis\.Retract/);
    expect(() => drivers.trigger('x_axis.Retract'))
      .toThrow(/x_axis\.Home.*y_axis\.Home/);
    expect(drivers.driver('x_axis.motor')).toBe(8000);
  });
});

describe('DriverStore ramps', () => {
  it('ramps to the converted target and lands exactly', async () => {
    const clock = new Clock();
    const drivers = store(clock);

    const run = drivers.trigger('x_axis.Home');
    clock.advance(0.5);
    drivers.tick();
    expect(drivers.driver('x_axis.motor')).toBe(6000);

    clock.advance(1.0);
    drivers.tick();
    expect(drivers.driver('x_axis.motor')).toBe(2000);

    clock.advance(0.5);
    drivers.tick();
    await run.done;
    expect(drivers.driver('x_axis.motor')).toBe(0);
  });

  it('holds the drivers the instruction does not target', () => {
    const clock = new Clock();
    const drivers = store(clock);

    drivers.trigger('x_axis.Home');
    clock.advance(1.0);
    drivers.tick();

    expect(drivers.driver('y_axis.motor')).toBe(2000);
    expect(drivers.driver('spin')).toBe(0);
  });

  it('keeps an integer driver whole at every frame', () => {
    const clock = new Clock();
    const drivers = store(clock);
    drivers.setDriver('x_axis.motor', 777);

    // 777 microsteps over 17 uneven frames: not one of them divides,
    // and every one of them must still be a whole native unit.
    const run = drivers.trigger('x_axis.Home');
    for (let frame = 0; frame < 17; frame += 1) {
      clock.advance(2.0 / 17);
      drivers.tick();
      expect(Number.isInteger(drivers.driver('x_axis.motor'))).toBe(true);
    }
    clock.advance(0.1);
    drivers.tick();

    expect(drivers.driver('x_axis.motor')).toBe(0);
    return run.done;
  });

  it('converts a scaled non-zero target through the driver table', async () => {
    const clock = new Clock();
    const drivers = store(clock);
    drivers.setDriver('x_axis.motor', 0);

    const run = drivers.trigger('x_axis.Park');
    clock.advance(1.0);
    drivers.tick();

    await run.done;
    expect(drivers.driver('x_axis.motor')).toBe(8000);
  });

  it('reports every ramped driver as changed once per frame', () => {
    const clock = new Clock();
    const drivers = store(clock);
    const listener = vi.fn();
    drivers.onDriverChange(listener);

    drivers.trigger('Both');
    clock.advance(0.5);
    const changed = drivers.tick();

    expect([...changed].sort()).toEqual(['x_axis.motor', 'y_axis.motor']);
    expect(listener).toHaveBeenCalledTimes(2);
    expect(listener).toHaveBeenCalledWith('x_axis.motor', 4000);
    expect(listener).toHaveBeenCalledWith('y_axis.motor', 1000);
  });

  it('replaces an active ramp from the current value, last wins', async () => {
    const clock = new Clock();
    const drivers = store(clock);

    const homing = drivers.trigger('x_axis.Home');
    clock.advance(0.5);
    drivers.tick();
    expect(drivers.driver('x_axis.motor')).toBe(6000);

    const parking = drivers.trigger('x_axis.Park');
    // The displaced run finishes where it stood, not on its old target.
    await homing.done;
    expect(drivers.driver('x_axis.motor')).toBe(6000);

    clock.advance(0.5);
    drivers.tick();
    expect(drivers.driver('x_axis.motor')).toBe(7000);

    clock.advance(0.5);
    drivers.tick();
    await parking.done;
    expect(drivers.driver('x_axis.motor')).toBe(8000);
  });

  it('stops where it stands when cancelled, and settles done', async () => {
    const clock = new Clock();
    const drivers = store(clock);

    const run = drivers.trigger('x_axis.Home');
    clock.advance(0.5);
    drivers.tick();
    run.cancel();

    clock.advance(5.0);
    drivers.tick();

    await run.done;
    expect(drivers.driver('x_axis.motor')).toBe(6000);
  });

  it('settles a run whose driver a host takes over by hand', async () => {
    const clock = new Clock();
    const drivers = store(clock);

    const run = drivers.trigger('x_axis.Home');
    clock.advance(0.5);
    drivers.tick();
    drivers.setDriver('x_axis.motor', 1234);

    await run.done;
    clock.advance(5.0);
    drivers.tick();
    expect(drivers.driver('x_axis.motor')).toBe(1234);
  });

  it('cancels active ramps on dispose', async () => {
    const clock = new Clock();
    const drivers = store(clock);

    const run = drivers.trigger('x_axis.Home');
    clock.advance(0.5);
    drivers.tick();
    drivers.dispose();

    await run.done;
    expect(drivers.driver('x_axis.motor')).toBe(6000);
  });
});
