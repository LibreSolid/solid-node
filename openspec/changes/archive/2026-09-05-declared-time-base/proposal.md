## Why

A model cannot say what its animation time *means*. `self.time` is the
normalized 0..1 turn of ADR-008, every producer publishes the same fixed
`animation: {fps: 30, frames: 360}`, and the viewer plays every turn in
twelve seconds. A project that models real time has to multiply the fraction
by a constant of its own and has no way to tell the framework or the viewer
about it.

Originating project: 3DPrintedClocks `design/wall_clock_01`. Its root maps
one turn to twelve hours through a project constant (`SECONDS_PER_TURN`),
and its kinematics speak seconds throughout — a 1.5 s pendulum, an escape
wheel turning once in 45 s, hands at 1/3600 and 1/43200 turns per second.
In `solid develop` that twelve-hour turn plays in twelve seconds: 120 s of
machine time and 80 beats of the pendulum per frame. Nothing but the hands
can be seen at any playback rate, because the problem is the resolution of a
fixed cycle, not its speed. Its tests carry the same constant the other way
(`SWING = PENDULUM_PERIOD / SECONDS_PER_TURN`) to turn seconds back into
fractions for `@testing_steps`.

The framework already holds the concept from the other side: under a stepped
`Sim` the same `self.time` reads the simulation clock in seconds
(spec `simulation`), and the `time` property's contract says what the value
means is the binder's choice. What is missing is the model's declaration of
its time base, so that every binder — the symbolic build path, keyframes,
tests, snapshots, the simulation loop — and every consumer of a published
document agree on it.

## What Changes

- A root assembly MAY declare its time base as a class attribute,
  `time = Time(loop=<seconds>)`, in the class-body idiom ports and drivers
  already use. `loop` is the span of machine time, in seconds, that one turn
  of the animation timeline covers.
- Under a declaration `self.time` reads **seconds** on every path: the
  symbolic build/viewer path yields `$t * loop` (so `$t` stays the 0..1
  timeline and the multiplication travels inside the published expressions),
  `set_keyframe(t)` and the testing decorators bind seconds, and `Sim`'s
  seconds now mean the same thing the rest of the model means. Every
  assembly below the root reads the root's time base; a declaration on a
  linked descendant is refused when read.
- The three document producers — the normal-build `viewer.json`, the export
  `manifest.json`, and the browser-snapshot document — publish `loop` in
  their `animation` object when the root declares one. The key is additive
  and the schema version does not change; a consumer without it plays
  `frames / fps` exactly as before.
- `solid snapshot --time` keeps its 0..1 timeline meaning under either
  renderer and keyframes the node at `fraction * loop` when a time base is
  declared.
- A root that declares nothing is untouched: `self.time` is the 0..1
  fraction, keyframes and decorators are fractions, documents carry no
  `loop`.
- The paired viewer change (solid-node-viewer, its own OpenSpec change) reads
  `animation.loop`, plays the loop at real time by default with a speed
  control, and shows the machine time. It is a separate change in a separate
  repository; this change is complete and consistent without it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `kinematics`: the "Normalized animation time" requirement becomes the
  undeclared case of a new "Declared time base" requirement — `Time(loop=)`,
  seconds on every path, root-only, `$t * loop` symbolically.
- `build-viewer-artifacts`: `viewer.json`'s `animation` object carries
  `loop` when the root declares a time base.
- `export`: the manifest contract's `animation` object carries `loop` the
  same way, still within the current schema version.
- `cli`: `solid snapshot --time` converts the timeline fraction to seconds
  under a declared time base before keyframing.
- `test-framework`: `@testing_instant` / `@testing_steps` instants are
  seconds under a declared time base; their mechanics and defaults do not
  change.

## Impact

- `solid_node/node/assembly.py` — the `time` property reads through a shared
  time-base resolver; new `Time` declaration (descriptor) exported from
  `solid_node.node`.
- `solid_node/core/builder.py`, `solid_node/core/export.py`,
  `solid_node/viewers/browser.py` — publish `animation.loop`.
- `solid_node/manager/snapshot.py` — convert `--time` under a declaration.
- `docs/animation.rst`, `docs/declaring.rst`, `docs/api-reference.rst`,
  `docs/changelog.rst` — document the declaration; one ADR extending
  ADR-008; `docs/architecture.md` kinematics and export sections.
- Consumers: the published documents gain one optional key. The viewer
  package is unchanged by this change and keeps playing `frames / fps`
  until its own change lands.
- Originating project: `wall_clock_01` drops `SECONDS_PER_TURN` from its
  `simulate()` and its tests, and its tests state instants in seconds.
