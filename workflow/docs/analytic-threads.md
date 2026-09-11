# Threaded rods and nuts as analytic parts

Status: design note, **not ratified, not implemented, not a public API
promise**. Date: 2026-09-09. Written after two days of discussion with the
pilot, who is the design authority, and revised against the motion layer
that landed the same day (`archive/motion-layer-2026-09-09/`). Nothing in
any repository is changed by this document. Names below are placeholders
for the pilot to rename. The library it proposes does not exist and has no
name yet.

## The finding

Four projects thread a rod and a nut, and every one of them pays for it.

- **Metamaquina 2** draws its two Z screws as an ISO M8 thread swept in
  OCCT (`metamaquina2/thread.py`), because "a nut on a plain cylinder is a
  nut around a pole: it does not hang on anything, it cannot be lifted by
  turning the pole, and the model has no way to be wrong about either". The
  sweep must be cut into segments of ten turns because one long OCCT pipe
  sweep of a Z bar "comes back with the volume of no solid at all —
  negative". The nut is the same profile grown by a clearance of 0.05 mm
  and subtracted from a hex blank. Each threaded rod's STL is 13 to 14 MB,
  the largest artifacts in the project, and every exact test that touches
  the pair pays the boolean on that thread.
- **Prusa i3 vanilla** carries the same file verbatim, at M5.
- **snappy-reprap** lifts its bridge on printed acme rods and printed nuts,
  cut by the design's own `acme_threaded_rod`. Its thread phase, the
  registration between rod and socket, had to be measured off the metal:
  the design's `-90` is half a turn out under the current OpenSCAD, and the
  sockets clear the rods only between 174 and 213 degrees further, so the
  project holds `PHASE = -90 + 193.5`.
- **3DPrintedClocks** has a third independent implementation
  (`simulation/shared/parts.py`, M3), which threads a rod only over the
  spans that carry a nut because a full-length sweep exceeds what OCCT's
  pipe shell survives; and wall clock 48's test of the real pair had to
  admit `volume_epsilon=2.5` and prove engagement on a short specimen
  instead.

Three copies of one thread, two of them worked around OCCT, one of them
measuring a phase the design should have stated, all of them shipping meshes
to the browser that a maker's laptop should not have to decode.

## What is wanted

Two things, both stated by the pilot, and nothing else:

1. **Tests without the physical calculation.** Whether the nut clears the
   rod, how much it can move before it binds, and whether the X carriage is
   held by the screws, answered by arithmetic over the thread parameters
   and the parts' placements, never by a boolean over a swept thread.
2. **Threads in the browser as parameters.** The viewer receives the thread
   as a few numbers and draws it in high definition itself, as it already
   does for molejo belts and springs, instead of receiving megabytes of
   triangles.

## The decision

Recorded here as the pilot settled it in discussion, in the order it moved.

- **Not molejo.** A thread is not a swept profile and a nut is not
  flexible; putting it there stretches molejo's charter, and the pilot
  refused that.
- **Not in solid-node either.** A **new sibling library** on the molejo
  pattern: a Python package and a JavaScript package implementing one
  serializable spec, pinned to each other by parity fixtures, consumable
  outside this workspace, depending on nothing here. The framework adapts
  it through an abstract **`AnalyticLeafNode`**, the way `FlexibleNode`
  adapts molejo.
- **Analytic is a third geometry kind**, beside exact and mesh. The
  parameter record is the truth. The OCCT solid and the mesh are
  *representations* derived from it, used only against parts that are not
  analytic, and for the viewer. Two analytic parts are never checked
  against each other through a solid or a mesh: their contracts are
  closed-form mathematics over the two records and the two placements.
  Saying "exact" or "mesh" of an analytic part is a category error, and
  it was made twice in the discussion before this was understood.
- **Never fused.** Fusing an analytic part throws away the only thing that
  makes it analytic. A fusion refuses one by name; a project that wants a
  thread in a fused body uses an ordinary leaf.
- **Nothing about manufacturing.** The kind says how a part's geometry is
  answered, not how the part is made. Sourced M8 studding and a printed
  acme lifter are both analytic parts. An earlier phrasing, "outside the
  print inventory", was wrong and is withdrawn: printing is not this
  layer's concern, and there are printed nuts and bolts.
- **Rod, nut and screw** are each their own case. The screw is not
  difficult and is not deferred.

## The model

### The library

Its vocabulary is thread forms, parts, pair mathematics and representations.

A **thread form** is what a rod and its nut share: family, nominal
diameter, pitch, number of starts, handedness and the profile numbers. The
standard forms, ISO metric coarse and fine and the trapezoidal series, come
as tables; a form may also be written out in full, because snappy-reprap's
acme is the design's own and clock 48's author already types profile
numbers by hand. A form is a value, so one declaration feeds every part cut
to it, and the pair mathematics refuses two parts whose forms differ.

A **part** is a record over a form: a rod with a length and its threaded
spans; a nut with a body outline and a height; a screw with a head kind,
head dimensions and threaded length. Every part carries its **thread
start**, the angle at which its helix crosses the part's own base plane.
That is what the projects call phase, and it belongs to the part because it
is a property of the specimen, not of where the specimen sits.

The **pair mathematics** is Python only; the browser never needs it. Given
two records and two world matrices it answers, for a rod-like and a
nut-like part: whether the axes coincide within a stated tolerance, the
relative phase modulo one pitch, the axial play, the number of engaged
turns, and whether the flanks interfere. Relative phase is the nut's axial
offset along the rod, less the lead times the rod's rotation, plus the two
thread starts, modulo the pitch; lead is starts times pitch; handedness
fixes the sign. The reference implementation is the projects' own
arithmetic, in one place.

The **representations** are all derived. The mesh evaluators produce the
true thread form at a declared tessellation, in both runtimes, for the
viewer, and both runtimes agree to parity fixtures as molejo's do. The OCCT
representation produces the **envelope** by default: the crest cylinder for
a rod, the body with a minor-diameter bore for a nut. An envelope is a
superset of the material, so it is conservative for interference against
any non-analytic part, and it costs nothing to build. The true form in OCCT
stays available on explicit request, at the cost every project knows, for
the rare exact part that is itself tapped.

### The framework

An abstract analytic leaf sits beside the exact, sheet and flexible bases,
and one adapter binds the library. A project declares a part as it declares
any node: class-body parameters that enter identity, a `render()` that
returns the library's record, validated by namespace like every adapter's.
An analytic part is rigid and one body. It may share a joint coordinate
passed down from its parent, as the clock's printed wheel shares its
arbor's revolute; it owns no coordinate of its own.

```python
class ZRod(AnalyticLeafNode):
    form   = M8            # a thread form value, a constant
    length = Length(min=0)
    start  = Angle(0.0)

    def render(self):
        return Rod(form=self.form, length=self.length,
                   threaded=[(0, self.length)], start=self.start)
```

**Routing.** The kernel rule gains one clause in front of the existing two.
Two analytic parts are answered by the library's pair mathematics: matching
forms and coincident axes give phase, play, engaged turns and interference;
anything else falls back to the envelopes, and overlapping envelopes there
are interference. An analytic part against an exact part is answered on the
envelope solid; against a mesh part, on the envelope mesh. No declaration
tells the router that a pair is meant to mesh, because none is needed: two
same-form coaxial threaded parts are either meshed or colliding, and the
arithmetic says which.

**Contracts.** The consequence worth stating first is that the existing
Metamaquina 2 assertions on the nut and its rod — not intersecting, free
within the play, blocked beyond the stop, all along the rod's axis — need
no rewriting. A perturbation is a matrix change, the pair goes to the
mathematics, and the same test text runs in microseconds where it now
builds a thread. Two assertions are new because only the pair mathematics
can answer them: engaged for at least so many turns, and backlash within so
much.

**Support.** `assertAssemblySupported` meets an analytic pair and asks the
pair mathematics instead of the kernel, the same routing the interference
assertions use: engaged turns mean an axial hold in both senses. This is
the "X carriage held by the rod without a surface check" of the original
ask, and it adds no concept, only a route. The declared-supports argument
stays for glue and press fits the geometry cannot show.

**The document.** A fourth node shape for the viewer: rigid, a technology
name, the part record verbatim, no expressions and no model reference. The
viewer evaluates it once into buffers and refuses a technology it does not
know, as it does today for flexible parts. That is a document version and a
viewer API version, and a change in two repositories under the two-repo
rule; it lands on the viewer release already pending.

## What the motion layer changes, and what it does not

The motion layer (`solid_node.motion`: ports, joints, couplings; ADR-087
to ADR-089; baseline specs `joints` and `couplings`) was designed and
implemented in parallel with this discussion, on the same day. It is not
the same work, and it removes no physical calculation: it answers where
every part is at an instant, and its own design lists contact and
engagement as deliberately out. It does nothing for a 13 MB rod in the
browser. Both goals above remain this note's alone.

The two meet on one sentence. A rod turning and a nut travelling is the
helical lower pair, which the motion design lists as a revolute driving a
prismatic on one axis with the lead as ratio, and which a project writes
as `rods.turn.drives(x_stage.lift, ratio=-LEAD / 360, offset=PHASE)`. The
projects' turns-to-height modules become that sentence when they migrate,
and that is the motion layer's work, not this note's.

Three things were proposed in the discussion and dropped once the motion
layer was read against them. They are recorded so they are not proposed
again.

- **A `Threaded(nuts, rods)` declaration** to mark a pair as intended. Not
  needed: the router and the support solver answer from the records and
  placements, and the word coupling is the motion layer's.
- **Clearance pairs** (a washer or bearing bore on a rod) as a second kind
  of analytic pair. Not needed for either goal: the rod's envelope is a
  plain cylinder, and a cylinder against an ordinary exact part is already
  cheap. It would matter only if washers and bearings became analytic
  parts, which nobody asked for.
- **A screw law shipped by the library** for `drives(law=...)`, deriving
  the offset from the two thread starts. Not needed: a project writes the
  ratio and offset by hand, and if the offset is wrong the pair mathematics
  reports interference. That is the declared-then-verified order the pilot
  asked for, and it keeps the library entirely out of motion. (The
  framework side would allow it: a `law=` callable receives the two owning
  nodes. It is simply not wanted.)

## The cheaper alternative, stated honestly

A project can have most of the cost relief today with no framework change:
draw the rods as plain cylinders, as the OpenSCAD designs do, declare the
nut supported by the rod, and trust the offset written in `drives`. That
removes the booleans and the big STLs. What it loses is everything the
thread tests prove: the nut becomes a ring around a pole, and phase,
backlash and interference go unverified. This note is worth building only
if those contracts are to be kept and the thread is to be visible in the
browser. That is the pilot's call, and it has not been made.

## Scope that survives

- The sibling library: thread forms, rod, nut and screw records with thread
  start, pair mathematics, envelope OCCT representation, true-form mesh
  evaluators in Python and JavaScript with parity fixtures, a versioned
  spec.
- `AnalyticLeafNode` and the library's adapter in the framework; the
  routing clause; the two new assertions; the support solver's route; the
  fusion refusal.
- The viewer's fourth node shape, in the viewer repository.
- Validation in Metamaquina 2 first, then Prusa i3 vanilla, snappy-reprap
  and clock 48, each deleting its `thread.py` or threaded-part helpers.

Nothing here waits on the motion layer.

## Open for the pilot

- The library's name.
- The coaxiality tolerance of the pair mathematics, and where it is
  declared: on the form, on the assertion, or as a framework default.
- Whether the pair mathematics may pair an analytic part with a tapped
  exact part, or only two analytic parts (the note assumes only two).
- Whether the true-form OCCT representation is in the first version at all,
  or only the envelope.

## References

- `projects/3D-Printers/Metamaquina2/metamaquina2/thread.py`,
  `z_screw.py`, `hardware/m8_nut.py`, `hardware/threaded_rod.py`,
  `test_metamaquina2.py` (the Z pair contracts and their docstrings).
- `projects/3D-Printers/Prusa3-vanilla/simulation/thread.py`.
- `projects/3D-Printers/snappy-reprap/simulation/z_screw.py`.
- `projects/3DPrintedClocks/simulation/shared/parts.py`,
  `wall_clock_48/test_clock.py`.
- `molejo/README.md`, `molejo/docs/spec.md` (the pattern the library
  follows).
- Framework: ADR-057 (the flexible leaf and spec-carried geometry), ADR-073
  (the faceted test kernel), ADR-076 (laws over expression math), ADR-088
  and ADR-089 (joints and drives); `openspec/specs/flexible-parts`,
  `exact-geometry`, `test-framework`, `couplings`.
- `archive/motion-layer-2026-09-09/joints-and-couplings.md`.
