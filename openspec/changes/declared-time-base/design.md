## Context

`AssemblyNode.time` (ADR-008) is one entry of the multi-driver snapshot
(ADR-056): bound, it reports the bound number; unbound, it falls back to
solid2's symbolic `$t`, the normalized 0..1 timeline every document
consumer plays. The property's own docstring already says what the value
*means* is the binder's choice — a keyframe binds a fraction, `Sim` binds
seconds — and nothing lets the model settle that choice. Every producer
publishes the same hardcoded `animation: {fps: 30, frames: 360}` (builder,
export default, browser snapshot), so every loop plays in twelve seconds.

The declarative node API (spec `declarative-nodes`) settled the idiom for
what a class body declares: a typed wrapper per concern — `Length`,
`RotationalPort`, `Driver` — read as an attribute of the instance and
enumerable off the class. `DriverDeclaration` in `solid_node/node/qualified.py`
is the shape: a data descriptor whose `__get__` hands back the snapshot
entry and whose `__set__` refuses assignment, frozen so nothing per-instance
can be stored on it.

The originating project (`wall_clock_01`) multiplies the fraction by
`SECONDS_PER_TURN` in `simulate()` and divides by it in its tests; the
framework and the viewer never learn that a turn is twelve hours.

## Goals / Non-Goals

**Goals:**

- One declaration, on the root, in the existing class-body idiom, from which
  every binder and every producer derives the meaning of `time`.
- Seconds everywhere under a declaration — symbolic path, keyframes, tests,
  snapshots, simulation — so a project's kinematics, tests and documents
  speak one unit.
- The published documents tell a consumer the loop length without a schema
  bump, so an old viewer keeps working and a new one can play real time.
- Nothing changes for a root that declares nothing.

**Non-Goals:**

- Playback speed. That is a presentation choice, owned by the viewer with a
  real-time default; the model declares what a turn *is*, not how fast to
  watch it (paired viewer change, separate repository).
- A `Meta`-style option bag. Time is one input with one property; the
  wrapper idiom already covers it, and a bag would be a second declaration
  idiom for one item.
- Time units other than seconds. Kinematics and `Sim` already speak seconds;
  a `unit=` would only add a conversion nobody asked for.
- Independent per-assembly timelines (ADR-008's rejected option 2).
- Changing `@testing_steps` defaults or `set_keyframe`'s signature.
- Changing what `Sim` binds: it already binds seconds.

## Decisions

### D1. A `Time` declaration on the root, bound to the name `time`

`time = Time(loop=<seconds>)` is a frozen declaration held as a class
attribute, exported from `solid_node.node` beside the ports. It is a data
descriptor: on the class it returns itself (so `Root.time.loop` is readable
without constructing anything, the way `declared_drivers` reads a class);
on an instance it returns what the shared time reader returns; `__set__`
refuses assignment naming `set_keyframe`. `__set_name__` refuses any name
but `time` and any owner that is not an `AssemblyNode`.

*Why a descriptor named `time` rather than a differently named attribute?*
The name `time` is the one global snapshot entry and the property every
existing `simulate()` reads; the declaration is metadata *about that
property*. Shadowing the base property with a descriptor of the same name is
the only way to keep `self.time` as the single read surface. A separate
name (`clock = Time(...)`) would leave two things to read and nothing to
tie them together.

*Why not a `DriverDeclaration` subclass?* Drivers are enumerated into the
document's `drivers` table by qualified id and bound by `Sim` from their
defaults; `time` is neither — it is global, has no default to bind, and is
already published as `$t`. Sharing the base would also trip its
own shadow check (`AssemblyNode.time` exists). The descriptor shape is
copied; the class is its own.

*Alternatives:* a `Meta` inner class (rejected in the proposal); a
`pyproject.toml` key (project configuration, but the time base is a property
of a model class and a project may hold several roots); a constructor
argument (the declarative API removed those on purpose).

### D2. One time reader for the property and the descriptor

`AssemblyNode.time` and `Time.__get__` both call one module-level reader:
note the read to the phase stack, return the bound `_states['time']` if
present, else the symbolic fallback. The fallback resolves the time base off
the **root of the linked tree** — walk `_parent` up as `instance_path` does —
and returns `get_animation_time() * loop` when the root class declares a
`Time`, bare `get_animation_time()` otherwise. Because the reader walks to
the root on every unbound read, a descendant without a declaration reads
the same `$t * loop` its root reads; no state has to be propagated to make
descendants agree, and the numbers-only contract of `set_state` stays
untouched (an expression is never bound).

*Why resolve off the root rather than propagate at link time?* Children are
linked before they render (the scad, serializer and state walks all link
first), and `simulate()` — the one place time is read — runs during those
walks. The walk up is a few pointer hops per unbound read; unbound reads
happen once per render, not per frame.

### D3. A declaration below the root is refused at the read

While walking up, the reader checks every node strictly below the root: if
one's class declares a `Time`, the read fails naming that node and the root.
The check sits in the read rather than in `set_state` or the serializer
because a driverless tree on the symbolic path is never walked by either —
the read is the one place every path goes through. A declaring assembly
that is the root of the tree it is read in (a sub-assembly under test, or
loaded alone) uses its own declaration: the rule is about the *linked*
tree, so component classes can declare a time base and be composed only by
a root that declares its own — or not at all, in which case the child's
declaration is a mistake and is reported as one.

### D4. Seconds on every path, `$t * loop` on the symbolic one

Under a declaration the bound value is seconds by contract: `set_keyframe`
binds what it is given, `Sim` already binds `k*dt` seconds, the testing
decorators hand instants through unchanged. The symbolic fallback multiplies
`$t` by the loop so that the published expressions carry the conversion and
the document's `$t` keeps being the 0..1 slider the viewer, the OpenSCAD
animation dialog and `solid snapshot --time` already share. A consumer that
has never heard of `loop` therefore renders the right pose at every slider
position; the only thing it cannot do is play the loop at a meaningful rate.

*Alternative rejected:* keep keyframes as fractions and convert in the
reader. Then `Sim`'s seconds would be multiplied by the loop, and the reader
would need to know which binder bound the entry — exactly the ambiguity the
declaration exists to remove.

### D5. `animation.loop`, additive, on all three producers

The builder's `viewer.json`, `export_node`'s `manifest.json` and the browser
snapshot's staged document read the declaration off `type(root)` and add
`loop` to the `animation` object when present. The key is optional and
additive within the current version, as `instructions` was: the tree shape
and the operation serialization — the two things the version guards — do
not change, and a consumer ignoring the key plays as before. `fps` and
`frames` stay: `frames` is the slider's resolution, and the export options
keep their meaning.

*Alternative rejected:* a top-level `time` object. The loop is a fact about
the animation timeline; putting it beside `fps`/`frames` is where a consumer
computing a cycle already looks.

### D6. `solid snapshot --time` converts, the renderers do not

The web and OpenSCAD renderers both take a 0..1 `$t`; the expressions they
evaluate already include the loop. Only the Python keyframe in
`manager/snapshot.py` — which binds a *number* into `time` — has to convert
`fraction * loop` so the baked pose matches the slider. The CLI option's
range and validation do not change.

### D7. Documentation and ADR

One ADR, "Declared time base", extending ADR-008: the declaration, seconds
everywhere, root-only, `$t * loop` symbolic, `animation.loop` additive.
ADR-008's rejected option 3 (real-time clock) is revisited there: its
objections were OpenSCAD compatibility and test determinism, both answered
by the symbolic product and the integer-tick `Sim`. `docs/animation.rst`
gains the declaration; `docs/api-reference.rst` documents `Time`;
`docs/changelog.rst` records it; `docs/architecture.md`'s kinematics and
export sections are rewritten for the new state.

## Risks / Trade-offs

- [A project migrating to `Time` changes the meaning of every instant it
  states] → Documented as the migration: `simulate()` stops multiplying,
  tests stop dividing, and `set_keyframe` callers state seconds. Nothing
  moves for a project that does not declare.
- [An old viewer plays a 43200 s loop in twelve seconds] → Exactly what it
  does today, and the pose at every slider position is still right; the
  paired viewer change fixes the playback. Documented in the changelog.
- [The root walk in the reader costs a few hops per unbound read] → Unbound
  reads happen once per render, never per frame; bound reads (tests, Sim,
  snapshots) do not walk at all.
- [Component classes that declare a time base cannot be composed under an
  undeclared root] → By design (D3); the error names both nodes and the fix
  is a declaration on the root.
- [`frames` keeps limiting slider granularity to 1/360 of a 12-hour loop] →
  Playback is continuous in the viewer and scrubbing precision is a viewer
  concern; `solid export --frames` remains available to raise it.

## Migration Plan

Additive; no existing project changes behaviour until it declares. The
originating project migrates as the caller check of this change:
`time = Time(loop=spec.SECONDS_PER_TURN)` on `WallClock01`, `simulate()`
assigns `self.time` directly, and `test_clock.py` states its spans in
seconds (`SWING = PENDULUM_PERIOD`, and so on). Its suite must pass
unchanged in verdicts.

## Open Questions

None for this change. The viewer's playback controls (speed ladder, machine
time readout, host option) are decided in the paired viewer change.
