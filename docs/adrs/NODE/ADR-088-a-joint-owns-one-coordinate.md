# ADR-088: A Joint Owns One Coordinate

**Status:** Accepted (frame decision superseded in part by [ADR-097](./ADR-097-a-joint-is-stated-in-the-frame-of-whoever-declares-it.md): a class-body joint reads its OWN rest frame, not the parent's; everything else below stands)
**Date:** 2026-09-09
**Extends:**
- [ADR-056: Signals, drivers, ports, and stepped simulation](./ADR-056-signals-drivers-ports-and-stepped-simulation.md)
- [ADR-066: render() builds the machine at rest, simulate() moves it](./ADR-066-render-at-rest-simulate-per-instant.md)
**Depends on:**
- [ADR-023: Kinematic operations and driver-tagged idempotent renders](./ADR-023-kinematic-operations-and-driver-tagged-idempotent-renders.md)
- [ADR-028: Cached base meshes, single-matrix world composition](./ADR-028-cached-base-meshes-and-single-matrix-world-composition.md)
- [ADR-061: A call in a node class body is a declaration](./ADR-061-a-call-in-a-class-body-is-a-declaration.md)
- [ADR-063: Identity from resolved declared values](./ADR-063-identity-from-resolved-declared-values.md)
- [ADR-087: One module, one question](./ADR-087-one-module-one-question.md)
**OpenSpec change:** `joints`

## Context and Problem Statement

A revolute joint existed in every project in the catalogue and in no
line of the framework. It was, in the words of the 2026-09-06 viability
research, "an emergent property of the author having written
`self.rotate(self.angle, [0, 0, 1])`" — and, when the axis does not run
through the moving part's own origin, of the author having written the
frame arithmetic that carries a pivot into that part's frame as well.

Thor is the evidence. `projects/Robotic-Arms/Thor/simulation/placing.py`
is 150 lines of framework work living in a project: `rotate_about` (bring
the line to the origin, turn, carry it back), `into_local` (undo a rest
placement to state a parent-frame pivot in the part's own coordinates),
`turn_about` (the two composed), `axis_sign`. The elbow axis is 81.5 mm
from the forearm's origin and the wrist axis 111.5 mm up the forearm, so
none of it is avoidable by choosing better origins. AlbertPro,
YouCanBuildDog, BCN3D-Moveo, open_manipulator, openarm,
hexapod_spiderbot and openvmp have each written some subset of it.
3DPrintedClocks writes the degenerate case instead: `TrainArbor.simulate()`
loops over the parts on one arbor and rotates each about z, because the
framework had no way to say "these parts are one body turning at this
bearing".

The value that moves such a body was already a framework concept — a
port carries it (ADR-056), a `Driver` supplies it, an expression keeps
it symbolic through to the viewer. What was missing was the statement of
WHERE the body may move, next to the body, once: the pair, in Reuleaux's
sense, that MuJoCo writes as a `hinge` with an `axis` and a `pos` and
Modelica as a `Joints.Revolute` between two frames.

## Decision Drivers

- One declaration that says where a body may move, next to the body, in
  the frame the parent places it in — the frame both target formats use.
- The frame arithmetic in `placing.py` becomes framework code, with a
  test that pins Thor's own numbers rather than a synthetic case.
- A joint's value must be a port for every existing purpose: enumeration,
  per-instance slot, causal binding, symbolic expressions, drivers.
- Nothing new on the wire. A joint must lower to operations the viewer
  already evaluates, so no schema version, no serializer edit, no viewer
  change (ADR-076).
- Every failure fails by name: an unresolvable argument at realization,
  an out-of-range binding at the binding, a wiring the child cannot
  receive at class definition.
- Nothing existing breaks: thirty projects go on turning their parts by
  hand, and both forms may sit on one node.

## Considered Options

1. `Joint` as a data descriptor OWNING one `Port` as its `coordinate`,
   with axis and anchor in the parent's frame, motion composed onto the
   rest placement by inverting it, applied at the binding, and a downward
   wiring by token validated at class definition.
2. `Joint` as a `Port` SUBCLASS, so one enumerator reports everything.
3. Motion applied at the END of the owning `simulate()`, collecting
   bindings and placing bodies once per run.
4. Axis and anchor stated in the moving node's OWN frame, so no carry is
   needed.
5. Joint arguments resolved lazily at first binding, or restricted to
   declared-parameter tokens with no callable form.

## Decision Outcome

Chosen option 1.

**A joint owns one coordinate, and that coordinate is a port.**
`Joint` holds a `Port` instance as `self.coordinate` — a
`RotationalPort` for a `Revolute`, a `TranslationalPort` for a
`Prismatic` — created in `__init__` and named with the joint's own name
in `__set_name__`. `Joint.__get__` returns that port's per-instance slot,
so reading a joint yields exactly the `BoundPort` a declared port yields,
out of the same `_port_values` dict; `Joint.__set__` range-checks, binds
through the one `bind` path `connect()` uses, and then places the body.
`declared_ports(cls)` reports the coordinate under the joint's name, so
every existing consumer sees a uniform map and never has to know about
joints; `declared_joints(cls)`, exported beside the kinds, is the sibling
for the code that needs the axis and the anchor.

`Joint` is deliberately **not** a `Port` subclass (option 2, rejected).
A port carries a value between nodes; a joint additionally places a body
and carries an axis, an anchor and a range. Subclassing would put `axis`
on every port and let `connect(source, some_joint)` be typed as a
port-to-port wire while meaning "move this body". Composition keeps the
two questions apart and still gives the uniform map, which is the only
thing subclassing bought. For the same reason a joint's coordinate
declares no `scale` and no `out`: what a joint's value means is stated by
its `unit`, a conversion between two coordinates is a relation, and a
joint has no direction to declare because it is not a node's output — it
is the node's own freedom.

**`declared_ports` recognizes a joint by a duck-typed `coordinate`
attribute, not an `isinstance` check.** `solid_node.motion.joints`
imports `solid_node.motion.ports` at module scope, because a joint owns
a port; ports importing joints back would close the cycle. One attribute
is the whole seam — no registry, no import edge — and a project adding a
joint kind of its own inherits it. `solid_node/node/declarative.py`
recognizes a coordinate the same way, and for the same reason: it is
imported while the node package is still initializing.

**Axis and anchor are stated in the PARENT's frame**, the frame the
parent's `render()` places the declaring node in, which is where MuJoCo
and Modelica state them (option 4, rejected: it would make the
declaration depend on where the part's own origin happens to be, which
is the accident joints exist to remove, and it is not what an exporter
would read). Motion composes innermost — in the node's own frame, before
the placement its parent applied (ADR-066) — so the framework carries
them: it composes the node's non-motion operations in list order by
premultiplication through each operation's own `matrix()` (ADR-028's one
seam for a 4×4, which resolves values through `as_number()` at access
time), inverts that, and takes `local_axis = R_rest⁻¹ · axis` normalized
and `local_anchor = M_rest⁻¹ · anchor` as a point.

On Thor's elbow this reproduces the project's hand-written constants
exactly: rest `rotate(90, [1, 0, 0])` then `translate([0, 241.5, 68])`,
parent-frame `axis=(0, 0, 1)`, `at=(0, 160, 68)` give
`local_axis = (0, 1, 0)` and `local_anchor = (0, 0, 81.5)` —
`ELBOW_PIVOT_AXIS` and `ELBOW_PIVOT` in `art2.py`. That identity is what
`tests/test_joints.py` pins, and it is why the refactor can be expected
to leave every Thor pose unchanged.

**The placement is ordinary operations, cleaned.** A `Revolute` applies
`translate(-anchor)`, `rotate(value, axis)`, `translate(anchor)`, the two
centring translations omitted entirely when every anchor component is
zero within `1e-9`; a `Prismatic` applies one `translate(value * axis)`,
each component a plain numeric `0` where the axis component is zero
rather than an expression multiplied by zero. Carried components within
`1e-9` of `0`, `1` or `-1` are snapped to those exact values, because the
inversion's residue is otherwise what the document publishes — an axis of
`(0, 1, 6e-17)`, an anchor of `81.49999999999999`. The bound value itself
is carried in unresolved, so a symbolic binding publishes a symbolic
angle and the viewer evaluates it with the expression math it already
has. Nothing new travels on the wire.

**Motion is applied AT THE BINDING** (option 3, rejected: applying at the
end of the owning `simulate()` makes the answer to "where is this child
now?" depend on where in `simulate()` the question is asked, and needs a
second mechanism to decide whose `simulate()` end is the right one for a
joint bound by a wiring two levels down). One rule — a joint's motion is
a consequence of its binding, applied where the binding happens — and the
phase stack does the rest for free: the operations are tagged with
whatever assembly's `simulate()` is running and swept before its next
run, exactly as a hand-written rotation there is. Binding one joint twice
leaves one motion, the last: the joint records the operations it applied
on the instance and removes them before applying new ones, tolerating
operations a sweep or a checkpoint restore already dropped.

**A joint's operations are placed as motion whatever phase is current.**
`_place_operation` APPENDS when no lifecycle phase is running, which is
right for a placement stated in the parent's frame and wrong for a joint:
the axis and anchor were carried into the node's own frame, so an
operation appended after the rest placement would be read in the parent's
frame — a body turned about the wrong line, silently. `solid_node/node/base.py`
therefore gains `apply_motion`, a sibling of `_place_operation` used by
joints only, which inserts innermost and marks the operation as motion
always, and tags it only when a phase is current. A joint never uses the
plain `rotate()`/`translate()` path.

**A rest placement the framework cannot invert numerically is refused by
name**, with the node, the joint and the operation, because the
alternative is placing the body about a wrong line. Only a legacy
`render()` that placed a node from a driver can produce it.

**A wiring is a keyword whose VALUE is a coordinate.**
`wheel = Arbor(index=index, turn=turn)`. The rule is decided on the
value, not the name, which keeps the change to `resolve_parameters` at
zero: wirings are split out in `ChildDeclaration.__init__` before
parameters are resolved, so the parameter path never sees them and every
other keyword keeps today's meaning, `TypeError` included. It is
validated in `ChildDeclaration.__set_name__`, where both ends are known
and where the sideways-read error already fires; it is bound at the end
of the parent's simulate phase, inside `_lifecycle_render` after
`self.simulate()` returns and before the phase is popped, so a wired
joint's motion is tagged with the assembly that stated the wiring. A
wired coordinate has exactly one binder: binding the child's end by hand
is refused by name, because the wiring bound at the end of that same
phase would otherwise overwrite it silently. There is no domain check —
`connect()` does not refuse a rotational source into a translational
sink either, and consistency with the one binding path matters more than
a rule the framework would be inventing here.

**Joint arguments resolve at realization and are not identity.** `axis`,
`at` and `range` are resolved per instance right after the instance's
parameters are resolved and its `check()` has run, and before its
children are realized, so a failure names the class, the joint and the
argument at the earliest point a value could be wrong and a refused
instance has realized nothing (option 5's lazy variant rejected: it would
surface a typo in an axis only when something moved). Each component may
be a number, a token, or a derived formula, resolved by the same
`evaluate` a child declaration's arguments use; the whole argument may
instead be a **callable of one argument**, called with the realized node.
That callable is the clock's case and nothing else — a bearing position
that comes out of `self.built`, a library movement built from the
instance's parameters and not expressible in the dimension algebra — and
it is deliberately the smallest opening that admits it rather than a
general lazy-argument protocol (option 5's restricted variant rejected on
that evidence: there is no formula to declare, and forcing one would push
a `Scalar` shim into every clock). Resolved arguments do not enter
`uniq_id` (ADR-063): a joint states where a body may move, not what
geometry is built, so two arbors differing only in their bearing position
are the same printed part.

## Consequences

- New `solid_node/motion/joints.py`: `Joint`, `Revolute`, `Prismatic`,
  `JointRangeError`, `declared_joints`, `resolve_declared_joints`. Module
  scope imports `solid_node.motion.ports` and `math` and nothing else;
  `numpy`, the operations and the node tree are reached inside the
  methods that need them, so importing it pulls no CAD backend, no exact
  stack and no `trimesh`. It costs exactly what importing
  `solid_node.motion.ports` costs, which widens the ceiling ADR-087's
  cycle set for the then-empty module; `motion.couplings` stays free.
- `solid_node/motion/ports.py`: `declared_ports` also collects an
  attribute whose `coordinate` is a `Port`; `Port` records its `owner`;
  `BoundPort` gains `wired_from` and `bind` refuses a hand binding of a
  wired slot, outside the `wiring_binding()` context the wiring itself
  uses.
- `solid_node/node/base.py`: `apply_motion` beside `_place_operation`
  (sharing `_insert_motion` and `_tag_operation`), and the constructor
  resolves declared joint arguments after `check()` and before
  `realize_children`.
- `solid_node/node/declarative.py`: the duck-typed coordinate predicate,
  the wiring split and its class-definition validation on
  `ChildDeclaration` (delegated to by `RepeatDeclaration`), the wiring
  recorded on each realized child, and a joint/port name clash refused
  while the class body runs — the only place it is visible, since the
  second assignment would simply replace the first in the namespace.
- `solid_node/node/assembly.py`: `_bind_wirings` at the end of the
  simulate phase, refusing an unbound source by name.
- No new operation type, no serializer change, no schema version, no
  viewer change.
- Two ways to move a body now exist — a joint, and a hand-written
  rotation in `simulate()`. Deliberate for at least this cycle and the
  next: nothing is deprecated, the two compose on one node, and thirty
  projects keep working untouched. Whether the hand-written form is ever
  deprecated is a question for after the projects have migrated.
- A joint's placement is published only as the operations it produces,
  not as a joint, so an exporter has nothing to read from the document
  yet. Recorded as future work rather than half-built: the
  MuJoCo/Modelica emission discussion `workflow/motion/roadmap.md` defers
  is where the document shape should be decided.
- Thor and 3DPrintedClocks are the originating projects and are NOT
  refactored here. They are refactored in their own repositories after
  cycle 3 (`couplings`), which is when derived coordinates and relations
  by path complete what their motion code needs.
