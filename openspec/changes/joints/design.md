## Context

Cycle 2 of the three in `workflow/motion/roadmap.md`. Cycle 1
(`motion-package`) moved ports and the declared time base into
`solid_node.motion.ports` and created `solid_node/motion/joints.py`
empty; this cycle fills it with `Revolute` and `Prismatic`. Cycle 3
(`couplings`) adds `drives`, `Affine`, derived coordinates over ports
and relations by path, and needs a joint to relate.

Read from the source rather than from the design note
(`workflow/motion/joints-and-couplings.md`), the state this builds on:

- **Motion is innermost, in the node's own frame.** `_place_operation`
  (`solid_node/node/base.py`) inserts an operation applied during the
  `simulate()` phase after the node's existing motion operations and
  before every rest operation, tags it with the simulating assembly
  (`operation._animator`) and registers the node in that assembly's
  `_animated_nodes`, so `_sweep` can drop exactly its own tagged
  operations before the next run (ADR-023, ADR-066). Successive calls in
  one phase therefore keep their call order at the head of the list.
- **Operations compose by premultiplication.** `_compose_matrix` walks
  the list applying `matrix = operation.matrix() @ matrix`, so for
  operations in list order the placement is `p_parent = M p_local` with
  `M = M_n · … · M_1`. `Rotation.matrix()` and `Translation.matrix()`
  resolve their values through `node.as_number()` at access time
  (ADR-028), and `as_number` refuses anything that is not a number.
- **A port is a data descriptor with a per-instance slot.**
  `Port.__get__` materializes a `BoundPort` under the instance's private
  `_port_values`; `Port.__set__` calls `bind`, which applies the sink's
  scale and refuses an unbound source. `declared_ports(cls)` scans the
  MRO base-first for `Port` instances. `DriverDeclaration`
  (`node/qualified.py`) is the same shape, and its module docstring
  already names `Port` as its twin.
- **A child declaration resolves its arguments per parent instance.**
  `ChildDeclaration.realize` calls `evaluate(arg, values)` for every
  argument; `resolve_parameters` raises `TypeError` for a keyword the
  child class does not declare as a parameter. `__set_name__` on the
  declaration runs while the parent class is being created, which is
  where a class-definition check belongs.
- **The lifecycle is `_sweep` → `_rest` → push SIMULATE →
  `self.simulate()` → pop** (`node/assembly.py`), and `_rest` runs the
  author's `render()` once for an assembly that read nothing.
- **The published document already carries what a joint needs.**
  `serialize_node` publishes `operations` as `['r', str(angle), axis]` /
  `['t', [str, …]]`, and ADR-076 makes a symbolic angle ordinary. A
  joint that lowers to `Rotation`/`Translation` needs no viewer change,
  no schema version and no serializer edit.

The originating evidence:

- **Thor**, `projects/Robotic-Arms/Thor/simulation/`. `Art2.render()`
  places `art3` with `rotate(90, [1, 0, 0])` then
  `translate([0, 160 + 81.5, 68])`; `Art2.simulate()` calls
  `placing.rotate_about(self.art3, elbow - shoulder, (0, 1, 0),
  (0, 0, 81.5))`. The constants `(0, 1, 0)` and `(0, 0, 81.5)` are the
  elbow axis and pivot **already carried into the forearm's own frame by
  hand**; in the parent's frame the same joint is
  `axis=(0, 0, 1), at=(0, 160, 68)` (`ELBOW_AXIS`, `ELBOW_ALONG_ARM`,
  `ELBOW_ACROSS_ARM` in `art2.py`). Inverting the rest placement gives
  the local pair back exactly, which is the arithmetic
  `placing.into_local` performs and the number the framework test pins.
- **3DPrintedClocks**, `simulation/shared/assemblies.py`. `TrainArbor`
  declares `turn = RotationalPort(unit='deg')`, translates every part to
  `movement.arbors[self.index].bearing_position` in `render()` and
  rotates every turning part about Z in `simulate()`. The bearing
  position is not a formula over declared parameters: it comes off
  `self.built`, the library movement the `Design` mixin builds from the
  clock's parameters. Any rule for joint arguments that admits only
  tokens fails this case.

## Goals / Non-Goals

**Goals:**

- One declaration that says where a body may move, next to the body,
  in the frame the parent places it in.
- The frame arithmetic in `placing.py` — `rotate_about`, `into_local`,
  `turn_about` — becomes framework code with a test that pins Thor's own
  numbers.
- A joint's value is a port for every existing purpose: enumeration,
  per-instance slot, causal binding, symbolic expressions, drivers.
- Nothing new on the wire. A joint lowers to the operations the viewer
  already evaluates.
- Every failure fails by name: an unresolvable argument at realization,
  an out-of-range binding at the binding, a wiring the child cannot
  receive at class definition.

**Non-Goals:**

- `drives`, `Affine`, derived coordinates over ports (`art3.elbow -
  shoulder`), relations by path, and the `declarative-nodes` relaxation
  that lets a class body read a port off a declaration. All cycle 3.
- Spherical, free, and the named compositions (screw, cylindrical,
  universal, planar). The roadmap's "future, not scheduled".
- A joints table in the serialized document, or any MuJoCo/Modelica
  emission. Nothing here is a down payment on one; the joint declaration
  is where an exporter would read from when one is designed.
- Refactoring Thor or clock 01. They are refactored in their own
  repositories after cycle 3, which is when their motion code can leave
  completely. This cycle commits nothing outside the framework.
- Closed loops, stateful mechanisms, mass, flow variables.

## Decisions

### 1. A joint is a descriptor that owns a port; `declared_ports` reports the coordinate, `declared_joints` reports the joints

`Joint` is not a `Port` subclass. It is a data descriptor holding one
`Port` instance as `self.coordinate` — a `RotationalPort(unit=…)` for a
`Revolute`, a `TranslationalPort(unit=…)` for a `Prismatic` — created in
`__init__` and named in `__set_name__` with the joint's own name.
`Joint.__get__` returns `self.coordinate.__get__(instance)`, so reading
a joint yields the same `BoundPort` slot a declared port yields, out of
the same `_port_values` dict. `Joint.__set__` range-checks and then
binds that slot and applies the motion.

**Enumeration:** `declared_ports(cls)` scans the MRO base-first and adds
a `Port` under its name, and now also a `Joint` under its name — as the
joint's `coordinate`, not as the joint. So every existing consumer of
`declared_ports` (`node/flexible.py`, the wiring rule below, later
tooling) sees a uniform map of ports and never has to know about joints.
`declared_joints(cls)`, exported from `solid_node.motion.joints`, is the
sibling that reports the joint objects, for the code that needs the axis
and the anchor. A name declared as both raises at class definition.

**Why not make `Joint` a `Port` subclass** (so one enumerator does
everything): the design note is explicit that a joint is not a port, and
the substance behind that is real — a port carries a value between
nodes, a joint additionally places a body and carries an axis, an anchor
and a range. Subclassing would put `axis` on every port and let
`connect(source, some_joint)` be typed as a port-to-port wire while
meaning "move this body". Composition keeps the two questions apart and
still gives the uniform map, which is the only thing subclassing bought.

**Why not `declared_ports` returning joints themselves as `Port`-like
ducks:** a consumer reading `.scale` or `.out` off a joint would get
attributes that mean nothing on it. Returning the coordinate returns a
real port with real metadata.

**No `scale` and no `out` on a joint.** A joint's value is stated in the
joint's `unit`; a conversion between two coordinates is a relation
(cycle 3), and a joint has no direction to declare because it is not a
node's output — it is the node's own freedom.

### 2. Binding applies the motion, at the binding

The alternative was applying at the end of the owning `simulate()`,
collecting bindings and placing bodies once. Rejected: it makes the
answer to "where is this child now?" depend on where in `simulate()` the
question is asked, and it needs a second mechanism to decide whose
`simulate()` end is the right one for a joint bound by a wiring two
levels down. Binding-time application means one rule — **a joint's
motion is a consequence of its binding, applied where the binding
happens** — and the phase stack then does everything else for free:
`_place_operation` tags the operations with whatever assembly's
`simulate()` is running, and `_sweep` drops them before its next run.

Consequences, all of them wanted:

- An author who binds `self.art3.elbow` and then measures `self.art3`
  in the same `simulate()` sees the moved body.
- A joint bound by the node's own `simulate()` (an assembly binding its
  own joint from a port it was handed) applies motion to itself, tagged
  with itself; assemblies already rotate themselves in `simulate()`.
- A wiring bound at the end of the parent's simulate phase (decision 4)
  is tagged with the parent, which is the assembly that stated the
  wiring.
- A joint bound in `render()` behaves as binding a port in `render()`
  does today: it works, `note_read` reports it, the class earns its one
  `FutureWarning`, and the render is re-run per binding. No new rule.

**Re-binding:** the joint records the operation objects it applied on
the instance (a private `_joint_motion` map keyed by joint name, beside
`_port_values`), and a second binding removes them from
`node.operations` before applying its own. Without that, an author who
binds a joint twice in one `simulate()` would accumulate two motions in
a run the sweep only cleans between runs. The removal tolerates
operations that are no longer in the list: `_sweep` drops tagged
operations by animator identity between runs, and the test runner's
checkpoint restore can replace the list wholesale, so the recorded
objects are a hint to remove, never an invariant.

**Binding outside any lifecycle phase** — a test binding a joint
directly, a script posing a tree — must still place the motion
innermost. `_place_operation` with no phase APPENDS, which would put the
joint's operations after the rest placement while their axis and anchor
were computed in the node's own frame: a body placed about the wrong
line, silently. So the joint does not go through the plain
`rotate()`/`translate()` path for placement; `base.py` gains the way to
place an operation as motion without a phase (a private sibling of
`_place_operation`, or a flag on it), used only here. Under a simulate
phase nothing changes: the operations are tagged and swept as before.
Outside one they are marked as motion but untagged, so no sweep touches
them and the re-binding rule above is what keeps them absolute.

### 3. Carrying the parent-frame axis and anchor into the node's own frame

At binding time the framework composes the node's REST operations —
those in `node.operations` without the `_motion` mark — in list order by
premultiplication, using each operation's own `matrix()`. That gives
`M_rest` with `p_parent = M_rest · p_local`. Then

    local_axis   = R_rest⁻¹ · axis          (normalized)
    local_anchor = M_rest⁻¹ · anchor        (as a point)

and the motion is, for a `Revolute`, `translate(-local_anchor)`,
`rotate(value, local_axis)`, `translate(local_anchor)` in that order —
which the motion placement keeps in that order at the head of the list —
and for a `Prismatic`, `translate(value * local_axis)`. Building the
framework's ordinary `Rotation`/`Translation` objects rather than a new
operation type is what keeps the wire format, the scad path, the mesh
path and the viewer untouched.

**Numeric hygiene.** The inversion produces residue: an axis comes back
as `(0, 1, 6e-17)` and an anchor as `(0, 0, 81.49999999999999)`, and
whatever comes back is what the document publishes. So components within
`1e-9` of `0`, `1` or `-1` are snapped to those exact values before use;
the two centring translations are omitted entirely when every component
of the local anchor is zero to that tolerance; and a `Prismatic` emits a
plain numeric `0` for a zero axis component instead of an expression
multiplied by zero, which would otherwise put `$t`-shaped noise in two
of the three slots of every slide.

On Thor's elbow this reproduces the project's hand-written constants
exactly: rest `rotate(90, [1, 0, 0])` then `translate([0, 241.5, 68])`,
parent-frame `axis=(0, 0, 1)`, `at=(0, 160, 68)` give
`local_axis = (0, 1, 0)` and `local_anchor = (0, 0, 81.5)` —
`ELBOW_PIVOT_AXIS` and `ELBOW_PIVOT` in `art2.py`. That identity is the
test the acceptance criterion rests on, and it is why the refactor can
be expected to leave every Thor pose unchanged.

**Why `matrix()` rather than re-deriving a rigid transform from the
operations' own angles and vectors:** `matrix()` is the framework's one
seam for an operation's 4×4 (ADR-028), it already resolves values
through `as_number()`, and a new operation type gets it for free.
`matrix()` costs a `trimesh` import, which is why the composition is
done at binding time inside a method, never at module import (decision
6).

**A non-numeric rest operation** — a legacy `render()` that placed the
node from a driver — makes `as_number()` raise. The framework catches it
and raises naming the node, the joint and the operation, because the
alternative is placing the body about a wrong line. That is a real
restriction on legacy models and it is stated in the spec rather than
discovered.

**Repeated children** need nothing special: `repeat()` realizes distinct
instances, each with its own `operations` list and its own resolved
joint arguments, and the inversion is read off the instance at binding
time. Identical geometry still shares one `uniq_id`, because joint
arguments are not identity (decision 5).

### 4. A wiring is a kwarg whose VALUE is a coordinate

`wheel = Arbor(index=index, turn=turn)`. The rule is decided on the
value, not the name: a keyword whose value is a `Port` or `Joint`
declaration is a wiring; every other keyword keeps today's meaning,
including the `TypeError` `resolve_parameters` raises for an unknown
one. Deciding on the value is what keeps the change to
`resolve_parameters` at zero: wirings are separated out in
`ChildDeclaration` before parameters are resolved, so the parameter path
never sees them.

**Validated at class definition**, in `ChildDeclaration.__set_name__`,
where both ends are known: the value must be a port or joint declared on
the owning class, and the keyword must name a port or joint of the child
class. This is the same moment the sideways-read error already fires, so
a wiring mistake reads like the other class-body mistakes.

**Bound at the end of the parent's simulate phase**, inside
`_lifecycle_render` after `self.simulate()` returns and before the phase
is popped: the author's own `simulate()` has had its chance to bind the
parent's coordinate, and the phase is still the parent's, so a wired
joint's motion is tagged with the parent. Every run rebinds, so the
wiring is as absolute as every other binding.

**No domain check.** A rotational coordinate wired into a translational
port is not refused, because `connect()` does not refuse it either and
consistency with the one binding path matters more than a rule the
framework would be inventing here. A conversion belongs to cycle 3's
`ratio=`/`law=`.

**One binder per coordinate.** Binding a wired child end by hand in the
declaring parent's `simulate()` is refused by name, because the wiring
bound at the end of that phase would otherwise overwrite it silently.
That is the same rule cycle 3 states for a coordinate two relations
reach, arriving one cycle early because the wiring creates the case.

**Downward only.** This cycle wires a parent's coordinate into a child's
declared port or joint. Reading a coordinate off a declaration
(`art3.elbow`), a relation by path, and any upward or sideways relation
are cycle 3.

### 5. Joint arguments resolve at realization, and are not identity

`axis`, `at` and `range` are resolved per instance right after the
instance's parameters are resolved and its `check()` has run, before its
children are realized — so a failure names the class, the joint and the
argument at the earliest point a value could be wrong, and a refused
instance has realized nothing.

Each component may be a number, a token, or a derived formula, resolved
by the same `evaluate(arg, values)` a child declaration's arguments use.
`axis`, `at` or `range` as a whole may instead be a **callable of one
argument**, called with the realized node and returning plain numbers.
The callable is the clock's case and nothing else: a bearing position
that comes out of `self.built`, which is a property over the instance's
parameters and not expressible as a formula in the dimension algebra. It
is deliberately the smallest opening that admits it — one call, one
argument, at realization, returning numbers — rather than a general
lazy-argument protocol.

**Alternative considered:** require the project to declare a derived
parameter per coordinate and pass tokens. Rejected on the evidence: the
value is a lookup into a built library object, so there is no formula to
declare, and forcing one would push a `Scalar` shim into every clock.

**Alternative considered:** resolve joint arguments lazily at first
binding. Rejected: the acceptance criterion is that a joint whose
arguments cannot resolve fails **at realization**, and a lazy resolution
would surface a typo in an axis only when something moved.

**Not identity (ADR-063).** `uniq_id` is derived from resolved declared
parameters, and a joint is not a parameter: it states where a body may
move, not what geometry is built. Two arbors that differ only in their
bearing position are the same printed part, which is exactly the
repeated-children case the identity rule exists for.

### 6. Module shape and imports

`solid_node/motion/joints.py` holds `Joint` (the shared base),
`Revolute`, `Prismatic`, `JointRangeError` and `declared_joints`. At
module scope it imports only from `solid_node.motion.ports` (`Port`
kinds, `bind`) — its coordinate is a port. Everything it needs from the
node package (the phase stack, `instance_path` for an error message, the
operation classes and the motion placement seam of decision 2) is
reached inside the methods that need it, exactly as `Time` reaches
`AssemblyNode` and `read_time` today.

This widens cycle 1's import-cost expectation and its test: `motion.joints`
now costs what `motion.ports` costs, because ports is imported at its
module scope. `motion.couplings` stays empty and stays free. No CAD
backend, no exact stack, and no `trimesh` at import time — the
`matrix()` calls that pull it happen at binding, inside a live render
where geometry is loaded anyway.

`declared_ports` must report a joint's coordinate, which means
`motion/ports.py` has to recognize a joint without importing
`motion/joints.py` (which imports it). The seam is a duck-typed marker
rather than an import: `declared_ports` collects any class attribute
that is a `Port`, or that carries a `coordinate` attribute which is a
`Port`. One attribute, no registry, no import edge, and a project
extending the joint kinds later inherits it.

### 7. Records

- `docs/adrs/NODE/ADR-088-a-joint-owns-one-coordinate.md` (086 is the
  highest in `docs/adrs/README.md` today and cycle 1 takes 087, so 088
  is free). It records: the joint as owner of one coordinate that is a
  port and why it is not a port subclass; axis and anchor in the parent
  frame, as MuJoCo and Modelica state them; motion composed onto the
  rest placement by inverting it, at the binding, under the phase that
  owns the tag; the downward wiring by token and its class-definition
  check. Written during apply, so it records what the code does. It
  extends ADR-056 (ports) and ADR-066 (render at rest, simulate per
  instant) without reversing either.
- New baseline capability `joints`; deltas to `ports`,
  `declarative-nodes`, `kinematics` and `cli-startup-cost`.
- `docs/architecture.md`: the Kinematics section gains the joint and the
  frame carry; the Node model section's declaration list gains it; the
  Map table's Motion row (added by cycle 1) gains `joints` and ADR-088.
- `docs/changelog.rst` "Unreleased" and the user documentation gain the
  joint, named as new API, not as a replacement for hand-written motion.
- `workflow/motion/roadmap.md` Progress table, row `2 joints`.

**Checked and needing no delta:** `simulation` — a `Driver` bound to a
joint is a value like any other, and the driver-range sentence already
says a range is presentation metadata and never a clamp, so the two
ranges coexist without a spec change. `node-model` — identity,
naming and the render lifecycle are unchanged by a declaration that is
not a parameter and not a child. `flexible-parts` — a flexible leaf's
ports are enumerated through `declared_ports`, which keeps its shape.

## Risks / Trade-offs

- **A joint on a node whose rest placement is symbolic cannot be
  carried into its frame** → refused by name, with the node, the joint
  and the operation. Only a legacy render that placed a node from a
  driver can produce it, and such a model keeps working exactly as long
  as it does not also declare a joint on that node.
- **Binding-time application means an author can observe a
  half-simulated tree** (bind one joint, measure, bind another) → that
  is what binding-time application is FOR, and it matches what
  `connect()` already does; the alternative hides the order instead of
  exposing it.
- **`declared_ports` recognizing a joint by a duck-typed `coordinate`
  attribute is looser than an `isinstance` check** → the alternative is
  an import cycle or a registry, both worse; the joints spec pins the
  behaviour and the test asserts a plain object carrying a `coordinate`
  is enumerated, so the seam is stated rather than accidental.
- **The callable form of a joint argument runs project code at
  realization**, with the instance's parameters resolved, its `check()`
  run, and its children not yet realized → documented as exactly that,
  and a callable that reaches for a parent or a child gets the ordinary
  `AttributeError`. It is the smallest opening that admits the clock's
  bearing positions.
- **Two ways to move a body now exist** (a joint, and a hand-written
  rotation in `simulate()`) → deliberate for at least this cycle and the
  next: nothing is deprecated, the two compose on one node, and thirty
  projects keep working untouched. Whether the hand-written form is ever
  deprecated is a question for after the projects have migrated.
- **A joint's placement is not published as a joint**, only as the
  operations it produces → an exporter has nothing to read from the
  document yet. Recorded as future work rather than half-built: the
  emission discussion the roadmap defers is where the document shape
  should be decided.

## Migration Plan

Additive. No existing declaration changes meaning, no import moves, and
no project has to do anything to keep working; a project adopts joints
by replacing its own frame arithmetic, one node at a time. Rollback is
`git revert` of the two cycle commits.

## Open Questions

None blocking. Recorded, not decided here:

- Whether a joint's coordinate should ever accept a `scale`. Today the
  answer is no, and cycle 3's `ratio=` is where a conversion belongs; if
  a project wants a scaled joint before then, a plain port beside the
  joint still does it.
- Whether the serialized document should carry a joints table, for an
  exporter and for a viewer that could offer a handle per joint. Tied to
  the MuJoCo/Modelica discussion the roadmap defers to the pilot.
- Whether hand-written `simulate()` motion is eventually deprecated in
  favour of joints. Not this cycle, and not cycle 3.
- Whether a `Prismatic`'s `at` should be required rather than defaulted,
  once an exporter actually reads it.
