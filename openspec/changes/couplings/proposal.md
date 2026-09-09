## Why

Cycle 2 gave a body a place to move. Nothing yet says that one body's
motion IS another's, so every project still writes the transmission by
hand — and writes it in the one direction it happened to need.

Wall clock 01 is the evidence for the hard direction.
`Movement.arbor_angles(seconds)` walks BACKWARDS from the escape wheel,
because the escapement is where the law is prescribed and the great
wheel is where the power comes in:

```python
angles = {escape_index: self.escape_wheel_angle(seconds),
          anchor_index: self.anchor_angle(seconds)}
for index in range(self.escape_index - 1, -1, -1):
    wheel, pinion = self.gear_pair(index, index + 1)
    angles[index] = depthing.wheel_angle_for_pinion(
        wheel, self.wheel_flipped(index), pinion,
        self.pinion_flipped(index + 1), angles[index + 1],
        self.line_of_centres(index, index + 1))
```

Every step of that walk is one affine relation. The framework already
carries it: `solid_node.mechanisms.meshed_angle` is
`driven = A - (driver_teeth / driven_teeth) * driver`, and
`driving_angle` is its algebraic inverse over the same six arguments —
the same relation read the other way, written out twice because the
project had to choose a direction. The clock then hand-builds a
dictionary of angles and fans it out through `simulate_for_seconds`
into every `TrainArbor`, the `MotionWorks`, the `Hands` and the
`Pendulum`.

Thor is the evidence for the easy direction and for the shapes the
clock does not have. Seven root `Driver`s are forwarded by hand down
five levels of ports, with nodes declaring `yaw, wrist, tool, grip`
only to pass them on. At each level a `simulate()` multiplies by a
ratio: 50/10 in the base ring, 60/10 to each shoulder pinion, 117/20 to
the elbow drive pulley, -20/10 for the forearm yaw, 1/2 for the slewing
race's ball cage, 40/20 behind each wrist motor. Two shapes are not
plain ratios: the elbow belt is anchored on the shoulder housing, so
the arm turns by `elbow - shoulder`, and the wrist differential is
`wrist + spin` and `wrist - spin` with `spin = 2 * tool`. Both are
linear formulas over coordinates.

Neither project needs a vocabulary of mechanisms. Both need one verb
that relates two coordinates, a way to write the law as project code,
and a solver that does not care which end the author happened to bind.
This is cycle 3 of the three in `workflow/motion/roadmap.md`, and the
last one: after it, the clock's `arbor_angles`, `motion_works_angles`,
`gear_pair`, `line_of_centres`, the depthing wrappers and the
`simulate()` fan-out can leave the project, and Thor's port forwarding
and ratio arithmetic can leave with them.

## What Changes

- **`a.drives(b)` — one verb, no imports, no hooks.** Written as a
  statement in a class body:
  `power.drives(centre, law=going_train)`,
  `centre.turn.drives(motion_works.cannon.turn, offset=hand_setting)`,
  `elbow_pulley.turn.drives(elbow_belt.travel, ratio=pitch_arc(117))`.
  `drives` is available on a child declaration, a port declaration, a
  joint declaration, a `Driver` declaration, a path reference and a
  derived coordinate; the right-hand end is any of those but a
  `Driver`. A bare statement is recorded on the class being defined;
  `great = power.drives(centre)` also names it, for a test and for an
  error message. A project never defines `drives` and the framework
  looks up no hook on any class.
- **`Affine(ratio, offset)` in `solid_node.motion.couplings`**, the one
  new importable name: `driven = ratio * driver + offset`, invertible
  when the ratio is not zero. `ratio=` and `offset=` on `drives` are
  its shorthand; with neither, the relation is ratio one, offset zero.
- **`law=` takes a callable, and the framework never learns what a gear
  is.** It is called once per parent instance at realization with the
  two realized coordinate OWNERS — the nodes the two ends belong to —
  and returns a law: an object with `forward(x)` and optionally
  `inverse(y)`, which `Affine` is. So the clock's "an arbor drives an
  arbor" is a plain function in the project's shared package, reading
  the tooth counts and the registration off the two arbors it is
  handed. The pilot rejected a `law_for` class hook explicitly: a law
  is passed in, never looked up.
- **Ends resolve to coordinates.** A port or joint end is its
  coordinate. A child-declaration end is the node's ONE joint's
  coordinate; a node with no joint or with more than one is refused at
  class definition naming the node and its joints. A `Driver` end is
  the driver's value and may only be the source.
- **Path references.** Reading an attribute off a child declaration
  that names a child, a port or a joint of that child's class now
  yields a path reference — `shoulder.art2.art3.wrist`, `anchor.turn`,
  `motion_works.cannon.turn` — resolved per parent instance at
  realization to the realized descendant's coordinate. Reading a
  parameter off a declaration stays the `SidewaysReadError` it is:
  ADR-061 is extended, not reversed. A relation on the root may
  therefore reach any depth, and the port forwarding disappears.
- **Derived coordinates.** A class-body formula over coordinate
  references with `+`, `-` and multiplication or division by a number
  is itself a coordinate of the class:
  `relative_elbow = art3.elbow - shoulder`, `left = wrist + 2 * tool`.
  It reads on the instance as a bound port slot, it can drive and be
  driven, and it solves backwards through exactly one unbound term.
  Anything not linear is a `law=`.
- **Direction is mechanical; solving is oriented from the bound side,
  per run.** At the end of the owning assembly's simulate phase, after
  the author's `simulate()` — and together with cycle 2's wirings, which
  become forward-only identity relations in the same solve, so a wiring
  whose source a relation solves no longer finds it unbound — the framework
  clears what it bound itself in the previous run, inventories which of
  the relation's ends are bound in this one, and propagates
  from the bound side — forward through the law, backward through its
  inverse — until nothing changes. A relation of a class is solved for
  each instance of that class, in that instance's own phase, so a
  relation on the root binds a deep coordinate BEFORE the deep node's
  own relations run.
- **Three named refusals**, each naming the node paths, the relation as
  written and the ends: `UnreachedCoordinate` (nothing binds it and no
  relation reaches it), `DoublyBound` (two binders — an author and a
  relation, two relations, a wiring and a relation), and
  `NotInvertible` (a law needed backwards that offers no inverse).
- **Motion follows.** Binding a joint's coordinate through a relation
  places the body exactly as an author's binding does in cycle 2: the
  same operations, the same animator tag, the same sweep.
- **Values stay symbolic.** `Affine` and the derived formulas are
  ordinary arithmetic, so a symbolic driver or `$t` rides through them
  into the published expressions the viewer already evaluates
  (ADR-076, ADR-022), and numbers stay numbers under `set_state` and
  the test runner.
- One ADR (`docs/adrs/NODE/ADR-089`) records the verb, the law as
  project code passed in with no class hook, resolution oriented from
  the bound side per run, the three refusals and the sideways
  relaxation. `docs/architecture.md`, `docs/declaring.rst`,
  `docs/driving.rst` and the changelog follow.

## Capabilities

### New Capabilities

- `couplings`: the relation between two coordinates. What `drives`
  states and where it may be written; how each kind of end resolves to
  a coordinate; the law protocol and `Affine`; derived coordinates as
  linear formulas over coordinates; when and where the relations of a
  class are solved, how the bound side orients each one, and the three
  refusals.

### Modified Capabilities

- `declarative-nodes`: the narrow relaxation of "a sideways read is
  refused" — a class body reading a child, a port or a joint off a
  child declaration yields a path reference; reading a parameter stays
  refused — and `drives` on a child declaration.
- `joints`: a joint declaration has `drives`; a node named as a
  relation's end resolves to its one joint's coordinate, and a node
  with none or several is refused at class definition; a joint bound
  through a relation places its body exactly as any binding does.
- `ports`: a port declaration has `drives`; a derived coordinate is a
  coordinate of the class, readable on the instance as a bound port
  slot and enumerated with the class's ports; a relation binds through
  the one binding path, so a sink's declared scale applies as always.
- `simulation`: a `Driver` declaration has `drives`, so a root driver
  reaches a joint by path without a port to forward it; a driver is a
  source only.
- `kinematics`: "Render at rest, simulate per instant" states when a
  class's relations are solved — at the end of that instance's simulate
  phase, after the author's `simulate()` and after the wirings — and
  that the motion a relation causes is that assembly's motion, tagged
  and swept with it.
- `cli-startup-cost`: `solid_node.motion.couplings` has contents now,
  so it costs what `solid_node.motion.ports` costs and no more, rather
  than nothing.

## Impact

**Framework code.** `solid_node/motion/couplings.py` gains `Affine`,
the relation record, the coordinate references, the derived coordinate,
the solver and the three errors; `solid_node/motion/ports.py` and
`solid_node/motion/joints.py` gain `drives` on their declarations;
`solid_node/node/declarative.py` gains the path reference on
`ChildDeclaration.__getattr__`, `drives` on a child declaration, and
the class-body registration of a bare relation statement through
`_DeclaringNamespace`/`NodeMeta`; `solid_node/node/qualified.py` gains
`drives` on `DriverDeclaration`; `solid_node/node/assembly.py` runs the
solver at the end of the simulate phase. No new operation type, no
serializer change, no schema version, no viewer change.

**Tests.** New `tests/test_couplings.py` and a new fixture project
`tests/coupling_project/` — a three-arbor train with tooth counts as
declared parameters and a registration offset, a root driver reaching a
joint by path, a derived coordinate driving a pulley and a belt — run
through `set_state`, the serializer and the symbolic build.
`tests/test_motion_package.py` has its import-cost expectation for
`motion.couplings` widened.

**Docs.** `docs/architecture.md` (Kinematics, Expression math,
Mechanisms), `docs/declaring.rst`, `docs/driving.rst`,
`docs/api-reference.rst`, `docs/changelog.rst` "Unreleased",
`docs/adrs/NODE/ADR-089`, `docs/adrs/README.md`,
`workflow/motion/roadmap.md`.

**Projects.** Nothing breaks: relations are additive and no existing
declaration changes meaning. The one behaviour change to an existing
rule is the sideways read, which turns three previously-refused reads
into path references — a strictly wider class of legal class bodies.
Wall clock 01 and Thor are the originating projects and are refactored
in their own repositories after this cycle; this cycle commits nothing
outside the framework, and its own evidence is the fixture train.

**Downstream.** Nothing depends on this cycle. Closed loops, stateful
mechanisms, non-linear derived formulas, automatic driver-to-joint
binding beyond `Driver.drives`, and MuJoCo or Modelica emission are all
out, and stay out.
