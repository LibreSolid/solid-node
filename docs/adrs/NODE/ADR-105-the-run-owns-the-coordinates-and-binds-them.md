# ADR-105: The Run Owns the Coordinates and Binds Them

**Status:** Accepted
**Date:** 2026-09-13
**Depends on:**
- [ADR-104: A third time base — elapsed seconds that never wrap](./ADR-104-a-third-time-base-elapsed-seconds-that-never-wrap.md)
**Extends:**
- [ADR-056: Signals, drivers, ports and stepped simulation](./ADR-056-signals-drivers-ports-and-stepped-simulation.md)
**Cites:**
- [ADR-089: `drives` relates two coordinates](./ADR-089-drives-relates-two-coordinates.md)
- [ADR-099: The enumeration's simulate phases are one tree pass](./ADR-099-the-enumerations-simulate-phases-are-one-tree-pass.md)
**OpenSpec change:** `run-owns-the-coordinates`

## Context and Problem Statement

ADR-056 made a driver the only holder of simulation state, so geometry
stays a pure function of the snapshot a tick produces. That guardrail is
right and stays. What it leaves out is the machine's own history: a pose
reduced to a function of the current input values cannot say where a
part WAS. The Curta's transmission pinion stands at 76 after one crank
revolution and at 76 after two, because its law can only say where the
pinion is for a crank angle; the Pascaline module's acceptance record
requires that "repeated commands must accumulate without register
re-entry".

The state a machine keeps is not a new kind of thing. It is where its
coordinates stand. So the question is not what to add to a driver but
what a RUN owns, and everything a run would own sits one layer above a
solver built to do the opposite. Measured on this tree before the change
(`openspec/changes/run-owns-the-coordinates/evidence/probe_binder.py`):

- a coordinate bound outside any enumeration and then rendered is SWEPT
  by `clear_solved` on the next phase and re-solved by its relation —
  the run's bank would be erased on the first tick;
- a relation both of whose ends hold values is refused `DoublyBound` —
  under a run every relation end is bound before the phase runs.

## Decision Drivers

- ADR-056's guardrail: render and simulate stay pure functions of the
  bound snapshot. Whatever the run does, an inspection or an extra
  render must advance nothing.
- ADR-099's whole-tree fixpoint, the freshness clear and the
  clear-with-the-motion rule are the hard-won shape of the solver, and
  must not be special-cased per mode.
- The author must declare no state: the spike campaign proved a stateful
  engine viable and also found that declaring events and memory per law
  was the wrong authoring interface.

## Considered Options

1. **A memory bank the author declares** (the spike's shape) — rejected
   by the pilot's decision of 2026-09-13: a law is integrated, not
   declared, and what a coordinate remembers is where it stands.
2. **A separate `Run(machine, dt)` object the author constructs** —
   rejected: `ScenarioTest` builds a `Sim`, and a second public name for
   one thing splits every scenario in two.
3. **The run writes slots directly, outside `set_state`** — rejected: it
   would put a second write path beside the one binding path, skip the
   joint's range and placement, and make the bank and the posed tree two
   facts that can disagree.
4. **Run the enumeration itself under the run's binder** — rejected, and
   it is the trap the design names: every plain port an author's
   `simulate()` binds during that enumeration would be recorded as
   run-bound, exempt from the freshness clear, and stale from the second
   tick on — the Prusa i3 shape ADR-099 fixed.

## Decision

Under a root declaring `Time.running()` the simulation owns a **BANK**:
every driver AND every joint coordinate of the linked tree — assemblies
and leaves alike, class-declared and site-declared joints alike — keyed
by the qualified ids the driver enumeration and the port enumeration
already produce (`path.joint`, or `path.joint.coordinate` for a joint
owning several). Plain ports and derived coordinates are NOT banked:
they are calculations over the state, recomputed by the ordinary
enumeration on every tick. There is no memory bank and the author
declares no state.

The initial bank is the **untimed rest pose**: construction binds the
requested driver values, enumerates the tree exactly as an untimed root
is enumerated, and reads every joint coordinate off it. A coordinate that
render leaves unbound is refused at construction, by name.

The run **binds through `set_state`**, with the whole bank and the
instant, and is recorded as the binder — a `RunBinder` living in
`motion/ports.py` so the one binding path can recognize it with no
import of its own. The solver recognizes that binder: the freshness
clear leaves a run-bound slot alone, an end that is run-bound reads as
BOUND before any question of freshness is asked, a relation all of whose
driven ends are run-bound is recorded as solved `'run'` in neither
direction, a wiring whose target is run-bound is recorded as applied,
and every message describes the run as "the running simulation". Any
other binding of a run-owned slot is refused as doubly bound, naming the
coordinate, the class whose `simulate()` is running and the run — which
is what makes a law written imperatively (`self.first.turn = self.crank
* 2`) fail at construction with a message that names the model's
mistake.

The run binder wraps the **delivery** of `set_state` and nothing else —
never the enumeration that follows. `set_state` accepts a qualified
joint-coordinate id under a running root and only there, delivering it to
the node that owns the coordinate, a leaf included, through
`set_coordinate`.

Requests replace bindings: `move(input, by=|to=, duration=)`,
`rate(input, rate)` and `trigger(name)` are one path with **one owner per
input** at a time, only a declared driver being movable, each returning a
handle reporting `active`/`completed`/`blocked`/`refused`/`cancelled` and
the travel actually admitted in design units, retired from the active
table the tick it completes. `snapshot`/`restore`/`reset` act on the
bank, `restore` refusing a snapshot whose program identity or `dt`
differs before touching live state; recording is explicit and bounded.

## Consequences

- **The run binder wraps only the delivery.** A plain port an author's
  `simulate()` binds keeps `binder = None`, is cleared and rebound every
  tick, and follows the run-owned coordinate it reads — the Pascaline
  module's `self.stop.angle = self.angle.value` idiom. Were the
  enumeration itself run under the binder, that port would freeze from
  the second tick.
- **An input is never back-driven.** A `Driver` is a source only
  (ADR-089), so the rest render never orients an edge into one and the
  program never determines one: an uncommanded input holds, whatever
  pushes the coordinates behind it. A coordinate physically pushed from
  two sides — the Pascaline column's wheel, turned by its own dial and
  by the previous column's carry — is therefore ONE MULTI-SOURCE LAW,
  `(dial & carry.turn).drives(column.turn, law=…)`, never two relations,
  which the untimed solver already refuses.
- Because the run binds through `set_state` alone, `render()` and
  `simulate()` stay pure over the snapshot: rendering, inspecting or
  rebinding the same snapshot advances nothing, and `sim.state`, the
  node's pose and the bank agree before the first tick.
- The refusal of an unbound joint coordinate bites a `Free` whose
  machine binds four of six; the fix is one guarded line per unused
  coordinate. It is raised as an open question rather than silently
  omitting the coordinate, which would make "every joint coordinate"
  false and give the run a coordinate with no history to keep.
- A run-bound slot survives `clear_solved` even after its `Sim` is
  discarded, exactly as a hand binding outside a phase does today; a
  later `set_state` or construction rebinds it.
- Two extra enumerations at construction and one `set_state` per tick
  cost what every tick already paid for drivers: measured at 1.16 ms per
  tick against the untimed loop's 0.36 ms on the same machine, with
  memory flat under a bounded ring.
