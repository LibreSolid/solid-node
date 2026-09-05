# ADR-072: A Declared Time Base

**Status:** Accepted
**Date:** 2026-09-05
**Extends:** [ADR-008: Time-Based Animation System for Assemblies](./ADR-008-time-based-animation-system-for-assemblies.md)
**Depends on:**
- [ADR-056: Signals, drivers, ports, and stepped simulation](./ADR-056-signals-drivers-ports-and-stepped-simulation.md)
- [ADR-066: render() Builds the Machine at Rest, simulate() Moves It](./ADR-066-render-at-rest-simulate-per-instant.md)
**Related:** [ADR-051: Producer-owned animation time in node-tree documents](../EXPORT/ADR-051-producer-owned-animation-time-in-node-documents.md)
**OpenSpec change:** `declared-time-base`

## Context and Problem Statement

ADR-008 gave every assembly a `time` normalized to 0..1, delegating to
OpenSCAD's `$t`, and left scaling to the model: "users scale in code". Under
ADR-056 that value became one entry of the driver snapshot, with the
0..1 fallback when unbound, and the property's contract said what the value
*means* is the binder's choice — a keyframe binds a fraction, a stepped
`Sim` binds seconds. Nothing let the model settle that choice, and every
document producer published the same fixed `animation: {fps: 30, frames:
360}`, so every loop plays in twelve seconds in every viewer.

The originating project, 3DPrintedClocks `wall_clock_01`, models a clock
whose kinematics speak seconds throughout — a 1.5 s pendulum, an escape
wheel turning in 45 s, hands at 1/3600 and 1/43200 turns per second. Its
root multiplied the fraction by a project constant to make one turn twelve
hours; its tests divided by the same constant to hand `@testing_steps`
fractions back. In `solid develop` the twelve-hour turn played in twelve
seconds: 120 s of machine time and 80 beats of the pendulum per frame.
Nothing but the hands could be seen at any playback rate, because the
problem was the resolution of a fixed cycle, not its speed. The framework
and the viewer never learned that a turn was twelve hours.

## Decision Drivers

- A model must be able to say what one turn of its timeline *is*, once,
  where the framework and every document consumer can read it.
- Seconds must mean the same thing on every path — symbolic build, keyframe,
  test decorator, snapshot, stepped simulation — so a project's kinematics,
  tests and documents speak one unit.
- The declaration must follow the class-body idiom the declarative node API
  settled (a typed wrapper per concern, read as an attribute, enumerable
  off the class), not introduce a second idiom.
- The published documents must tell a consumer the loop without a schema
  bump, so an old viewer keeps working at the right pose.
- Nothing may change for a root that declares nothing.
- Playback speed is not a model fact: the model declares what a turn is,
  the viewer decides how fast to watch it.

## Considered Options

1. A `Time(loop=<seconds>)` declaration on the root, bound to the name
   `time`, with `self.time` reading seconds on every path and the symbolic
   fallback `$t * loop`.
2. A Django-style `class Meta` on the root holding a `timescale`.
3. A project-level setting in `pyproject.toml`.
4. Keeping fractions everywhere and converting inside the `time` reader
   (`fraction * loop`), leaving `Sim` to bind fractions too.
5. ADR-008's rejected option 3, a real-time clock replacing `$t`.

## Decision Outcome

Chosen option 1.

**The declaration.** `Time` is a frozen dataclass and a data descriptor,
exported from `solid_node.node` beside the ports. Bound to any name but
`time`, or on a class that is not an `AssemblyNode`, it is refused at class
definition. Off the class it returns itself (`Root.time.loop`); off an
instance it returns what the shared time reader returns; assignment is
refused naming `set_keyframe`. It is not a `DriverDeclaration`: `time` is
the one global snapshot entry, is never enumerated into the `drivers`
table, has no default to bind, and is already published as `$t`. The
descriptor *shape* is copied from drivers; the class is its own.

**One reader.** `read_time(node)` in `solid_node/node/assembly.py` serves
both the base property and the descriptor: note the read to the phase
stack; return the bound `_states['time']` when present; otherwise walk
`_parent` to the root of the linked tree and return `$t * loop` when the
root class declares a `Time`, bare `$t` when it does not. A descendant
therefore reads exactly what its root reads with no state propagated to
make it so, and `set_state`'s numbers-only contract is untouched — an
expression is never bound. While walking up, a node strictly below the
root whose class declares a `Time` makes the read fail naming that node
and the root: a stray declaration can never silently scale one subtree
differently. An assembly that is the root of the tree it is read in — a
component under test, or loaded alone — uses its own declaration.

**The walk relies on the walkers' links.** The scad, serializer and state
passes link each child before recursing into it, so by the time a child's
`simulate()` reads `time` under any of them it knows its root. A bare
`render()` links nothing — the declarative-nodes contract pins that, and
this change keeps it — so a child rendered by hand before any walker
reached it is its own root for that read, exactly as a component loaded
alone is.

**Seconds on every path.** Under a declaration the bound value is seconds
by contract: `set_keyframe` binds what it is given, the testing decorators
hand instants through unchanged (their defaults do not follow the
declaration; a sweep over a declared root states the span it covers),
`Sim` already binds `k*dt` seconds, and `solid snapshot --time` — still a
0..1 position on the timeline under either renderer — keyframes
`fraction * loop` in Python so the baked pose matches the slider. The
symbolic fallback multiplies `$t` by the loop so the published expressions
carry the conversion and the document's `$t` keeps being the 0..1 slider
that the viewer, the OpenSCAD animation dialog and the capture already
share. A consumer that has never heard of the loop renders the right pose
at every slider position; the only thing it cannot do is play the loop at
a meaningful rate.

**`animation.loop`, additive.** Every producer — the builder's
`viewer.json`, `export_node`'s `manifest.json`, the browser snapshot's
staged document — builds its `animation` object through one helper that
reads the declaration off `type(root)` and adds `loop` beside `fps` and
`frames` when present, omitting it otherwise. The key is optional and
additive within the current schema version, as `instructions` was: the
tree shape and the operation serialization, the two things the version
guards, do not change, and an undeclared root's document is
byte-identical to before. `fps` and `frames` stay — `frames` is the
slider's resolution — and the export options keep their meaning.

**The paired viewer change** (`real-time-playback` in solid-node-viewer)
reads the key, plays the loop at real time by default with a speed control
and a machine-time readout. It is a separate change in a separate
repository; this one is complete and consistent without it.

## Pros and Cons of the Options

### Option 1: `Time(loop=)` on the root

- Good: one declaration, in the idiom ports and drivers use, read off the
  class the way the driver table is.
- Good: `self.time` stays the single read surface; every existing
  `simulate()` keeps compiling and gains a unit.
- Good: `$t` unchanged for every consumer; the loop rides inside the
  expressions.
- Good: `Sim`'s seconds now mean what the rest of the model means.
- Bad: a project migrating changes the meaning of every instant it states
  (documented as the migration; nothing moves for a project that does not
  declare).
- Bad: the reader walks to the root on every unbound read (a few pointer
  hops, once per render, never per frame).

### Option 2: `class Meta`

- Good: familiar to Django users; a place for future per-model options.
- Bad: a second declaration idiom beside the wrapper idiom, for one item
  that is about one input. In Django a field's unit goes on the field, not
  in `Meta`.
- Bad: Django's own `Meta` inheritance rules are a known confusion.

### Option 3: `pyproject.toml`

- Bad: project configuration, while the time base is a property of a
  model class; a project may hold several roots.

### Option 4: fractions everywhere, conversion in the reader

- Bad: `Sim`'s seconds would be multiplied by the loop, and the reader
  would need to know which binder bound the entry — exactly the ambiguity
  the declaration exists to remove.

### Option 5: a real-time clock replacing `$t`

- Good: direct mapping to physical units (ADR-008's own list).
- Bad: OpenSCAD compatibility and test determinism, ADR-008's objections —
  both answered by option 1 without paying them: the symbolic product
  keeps `$t`, and the integer-tick `Sim` keeps determinism.

## Consequences

- `solid_node.node.Time`, `solid_node.node.timebase.declared_time`,
  `solid_node.node.assembly.read_time`.
- `animation_block()` in the serializer; `animation.loop` on every
  producer; `manager/snapshot.py` converts `--time`.
- Specs `kinematics`, `build-viewer-artifacts`, `export`, `cli` and
  `test-framework` amended; `docs/animation.rst` gains the declaration.
- The originating project drops its constant from `simulate()` and its
  tests, and states its test spans in seconds, with the same verdicts.
- ADR-008 remains the account of the undeclared case; this record is the
  account of the declared one.
