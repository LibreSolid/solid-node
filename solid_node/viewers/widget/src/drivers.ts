/*
 * Solid Node - A framework for mechanical CAD projects
 * Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
 * SPDX-License-Identifier: Apache-2.0
 */

// One driver state per mounted document (ADR-056 stage 3b, design D3).
//
// Values are held in NATIVE driver units -- microsteps, not millimetres.
// That is what the document's expressions consume and what `default` and
// `range` declare, so a design-unit API would make `driver(id)` disagree
// with the pose on screen and would round integer dtypes twice. Hosts
// convert for presentation from the `scale` and `unit` the table
// publishes.
//
// `range` is never a clamp. A machine can be driven past its declared
// travel -- that is what a crash is -- and the framework refuses to
// invent a limit the declaration did not state.

import { DriverScope } from './evaluator';
import { ManifestDriver, ManifestInstruction } from './types';

export type DriverListener = (id: string, value: number) => void;

/** What `trigger` hands back: when the run lands, and how to stop it. */
export interface TriggerHandle {
  done: Promise<void>;
  cancel(): void;
}

const defaultClock = () => performance.now() / 1000;

/** `target`, in design units, as native driver state.
 *
 * The same arithmetic `Driver.native` performs in Python, and performed
 * ONCE, here, when a design-unit target becomes machine state -- never
 * per frame, where repeated rounding would let a ramp drift off its
 * landing. Integer dtypes round half to EVEN, as Python's `round` does,
 * so a target landing exactly between two native units converts to the
 * same one in both runtimes.
 */
export function toNative(target: number, driver: ManifestDriver): number {
  const value = driver.scale === null || driver.scale === undefined
    ? target : target / driver.scale;
  return driver.dtype === 'int' ? roundHalfToEven(value) : value;
}

function roundHalfToEven(value: number): number {
  const floor = Math.floor(value);
  const rest = value - floor;
  if (rest > 0.5) return floor + 1;
  if (rest < 0.5) return floor;
  return floor % 2 === 0 ? floor : floor + 1;
}

/** One driver's linear ramp, advanced on wall-clock elapsed time.
 *
 * Intermediate values are sampling and endpoints are contract: an
 * integer driver is whole at every frame (floor of the distributed
 * delta, as `RampProgram` does with `//`) and the last frame returns the
 * target itself rather than computing it.
 */
class Ramp {
  constructor(
    readonly start: number,
    readonly target: number,
    readonly startedAt: number,
    readonly duration: number,
    readonly integer: boolean,
    readonly run: Run,
  ) {}

  valueAt(now: number): number {
    const elapsed = now - this.startedAt;
    if (this.duration <= 0 || elapsed >= this.duration) return this.target;
    if (elapsed <= 0) return this.start;
    const delta = (this.target - this.start) * (elapsed / this.duration);
    return this.start + (this.integer ? Math.floor(delta) : delta);
  }

  landed(now: number): boolean {
    return this.duration <= 0 || now - this.startedAt >= this.duration;
  }
}

/** One `trigger` call: the ramps it started and the promise they settle.
 *
 * A run is finished when every driver it moved has landed, been
 * cancelled, or been taken over by a later trigger -- the last of which
 * is why `done` can resolve without the old target ever being reached
 * (`Sim`'s program replacement, seen from the caller's side).
 */
class Run {
  readonly done: Promise<void>;
  private resolve!: () => void;
  private pending = new Set<string>();

  constructor(private readonly store: DriverStore) {
    this.done = new Promise<void>((resolve) => { this.resolve = resolve; });
  }

  expect(id: string): void {
    this.pending.add(id);
  }

  settle(id: string): void {
    this.pending.delete(id);
    if (this.pending.size === 0) {
      this.resolve();
    }
  }

  cancel(): void {
    for (const id of [...this.pending]) {
      this.store.stopRamp(id, this);
    }
    this.pending.clear();
    this.resolve();
  }
}

export class DriverStore {
  private table: Record<string, ManifestDriver>;
  private events: Record<string, ManifestInstruction>;
  private values = new Map<string, number>();
  private ramps = new Map<string, Ramp>();
  private listeners = new Set<DriverListener>();
  // Changed since the last frame: what the tree must re-evaluate.
  private dirty = new Set<string>();
  // Changed by a ramp since the last frame: what listeners have not
  // heard yet. A `setDriver` tells them synchronously instead, so it
  // never lands here and is never announced twice.
  private pending = new Set<string>();

  constructor(
    table: Record<string, ManifestDriver> = {},
    instructions: Record<string, ManifestInstruction> = {},
    private readonly clock: () => number = defaultClock,
  ) {
    this.table = {};
    this.events = {};
    this.reconcile(table, instructions);
  }

  /** Adopt a newly published document, keeping the values of every
   * driver it still declares: a live rebuild is the same machine, and
   * resetting a host's pose to the defaults under it would be a
   * surprise the document did not ask for. */
  reconcile(table: Record<string, ManifestDriver>,
            instructions: Record<string, ManifestInstruction>): void {
    this.table = table;
    this.events = instructions;
    for (const id of [...this.values.keys()]) {
      if (!(id in table)) {
        this.stopRamps(id);
        this.values.delete(id);
      }
    }
    for (const [id, declaration] of Object.entries(table)) {
      if (!this.values.has(id)) {
        this.values.set(id, declaration.default);
      }
    }
  }

  /** The declared drivers, verbatim -- a copy, so a host inspecting the
   * document cannot edit the document. */
  drivers(): Record<string, ManifestDriver> {
    return Object.fromEntries(
      Object.entries(this.table).map(([id, driver]) => [id, { ...driver }]),
    );
  }

  /** The declared instructions, verbatim, targets in design units. */
  instructions(): Record<string, ManifestInstruction> {
    return Object.fromEntries(
      Object.entries(this.events).map(([name, entry]) => [name, {
        targets: { ...entry.targets },
        duration: entry.duration,
      }]),
    );
  }

  driver(id: string): number {
    const value = this.values.get(id);
    if (value === undefined) {
      throw new Error(this.unknownDriver(id));
    }
    return value;
  }

  setDriver(id: string, value: number): void {
    if (!this.values.has(id)) {
      throw new Error(this.unknownDriver(id));
    }
    // A host driving a driver directly takes it off whatever ramp was
    // moving it: two authorities on one value is the one thing that
    // cannot be resolved per frame.
    this.stopRamps(id);
    if (this.values.get(id) === value) {
      return;
    }
    this.values.set(id, value);
    this.dirty.add(id);
    this.pending.delete(id);
    this.announce(id, value);
  }

  onDriverChange(listener: DriverListener): () => void {
    this.listeners.add(listener);
    return () => { this.listeners.delete(listener); };
  }

  /** The driver values as the expressions read them: nested by qualified
   * id, bare root ids at the top level. */
  scope(): DriverScope {
    const scope: DriverScope = {};
    for (const [id, value] of this.values) {
      const dot = id.indexOf('.');
      if (dot < 0) {
        scope[id] = value;
        continue;
      }
      const owner = id.slice(0, dot);
      const name = id.slice(dot + 1);
      const nested = (scope[owner] ??= {}) as Record<string, number>;
      nested[name] = value;
    }
    return scope;
  }

  /** Advance the ramps to now, tell listeners what moved, and hand the
   * render loop the ids it must re-evaluate. */
  tick(): ReadonlySet<string> {
    const now = this.clock();
    for (const [id, ramp] of [...this.ramps]) {
      const value = ramp.valueAt(now);
      if (value !== this.values.get(id)) {
        this.values.set(id, value);
        this.dirty.add(id);
        this.pending.add(id);
      }
      if (ramp.landed(now)) {
        this.ramps.delete(id);
        ramp.run.settle(id);
      }
    }
    for (const id of this.pending) {
      this.announce(id, this.values.get(id)!);
    }
    this.pending.clear();
    const changed = this.dirty;
    this.dirty = new Set();
    return changed;
  }

  /** Start the named instruction's ramps from wherever its drivers
   * stand. Targets are design units; the driver table converts them. */
  trigger(name: string): TriggerHandle {
    const instruction = this.events[name];
    if (instruction === undefined) {
      const known = Object.keys(this.events).sort().join(', ') || 'none';
      throw new Error(
        `no instruction '${name}' in this document; declared: ${known}`);
    }
    const now = this.clock();
    const run = new Run(this);
    for (const [id, target] of Object.entries(instruction.targets)) {
      const declaration = this.table[id];
      if (declaration === undefined) {
        throw new Error(
          `instruction '${name}' targets driver '${id}', which this ` +
          `document does not declare; declared: ` +
          `${Object.keys(this.table).sort().join(', ') || 'none'}`);
      }
      // A driver already ramping is taken over from where it stands,
      // and the run that owned it finishes there rather than on its old
      // target -- `Sim`'s last-wins program replacement.
      this.stopRamps(id);
      run.expect(id);
      this.ramps.set(id, new Ramp(
        this.driver(id), toNative(target, declaration), now,
        instruction.duration, declaration.dtype === 'int', run,
      ));
    }
    return { done: run.done, cancel: () => run.cancel() };
  }

  /** Stop every ramp: the viewer is going away, and a promise nobody can
   * land must still settle. */
  dispose(): void {
    for (const ramp of [...this.ramps.values()]) {
      ramp.run.cancel();
    }
    this.ramps.clear();
    this.listeners.clear();
  }

  /** Drop `id`'s ramp, if it belongs to `run`, and settle it there. */
  stopRamp(id: string, run: Run): void {
    const ramp = this.ramps.get(id);
    if (ramp !== undefined && ramp.run === run) {
      this.ramps.delete(id);
    }
  }

  private stopRamps(id: string): void {
    const ramp = this.ramps.get(id);
    if (ramp === undefined) {
      return;
    }
    this.ramps.delete(id);
    ramp.run.settle(id);
  }

  private announce(id: string, value: number): void {
    for (const listener of [...this.listeners]) {
      listener(id, value);
    }
  }

  private unknownDriver(id: string): string {
    const known = Object.keys(this.table).sort().join(', ') || 'none';
    return `no driver '${id}' in this document; declared: ${known}`;
  }
}
