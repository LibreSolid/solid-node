## 1. Red first: the free joint

All of this lands in `tests/test_joints.py`, in a new section placed
after the orbit section, and uses the module's existing helpers
`serialized(node)`, `motions(node)` and `numbers(...)`. **Every case
below MUST be run and seen RED on the current tree before task 4 begins,
and the RED message recorded in `evidence.md`** — a case that is green
before the change is testing nothing. Most will be red with
`ImportError`/`NameError` on `Free`, which is a weak red: for each of
those, ALSO record what the case asserts that the hand-written four-call
equivalent (or the four-joint ADR-093 form) would fail, so the evidence
says more than "the name does not exist yet".

Assert the composed MATRIX, not only the operations list, wherever a
frame or an order is at stake. Use
`solid_node.node.base._compose_world_matrix` against a hand-written NumPy
product.

**On tolerances.** The composition is products of degree trigonometry
through one matrix inversion. `evidence/probe_matrix.py` measures the
hand-written equivalent against a NumPy product at
**1.11e-16** maximum over seven poses, with an identity rest placement.
Assert with `atol=1e-12` and RECORD the measured maximum for each
fixture; the fixture with a non-trivial rest placement will be looser and
its own measured number is what goes in the evidence. **Do not write
`atol=0` on a trigonometric comparison and then loosen it when it fails.**

- [ ] 1.1 **Fixtures.** `FloatingChassis`, a node declaring
  `pose = Free(angle_unit='deg', length_unit='mm')` on a body its parent
  does NOT place (the hexapod's case, identity rest placement); and
  `AnchoredFloat`, declaring `Free(at=<an off-origin point>)` on a body
  its parent places by a `rotate` and a `translate`, so the rest
  placement has a non-trivial rotation part and both the anchor and the
  three directions are carried through it.
- [ ] 1.2 **The six coordinates enumerate under their dotted names.**
  `declared_ports(FloatingChassis)` has exactly the six keys
  `pose.roll`, `pose.pitch`, `pose.yaw`, `pose.x`, `pose.y`, `pose.z`,
  with the rotational/translational domains and the two declared units,
  and NO key `pose`. `declared_joints` reports ONE entry, `pose`. Two
  instances read their own six slots. RED.
- [ ] 1.3 **The composition is the hexapod's.** Bind the four the hexapod
  binds at the seven poses of `evidence/probe_matrix.py` — including
  `pitch=90` and `roll=90` — and assert the composed world matrix equals
  `T(x, y, z) · Rz(yaw) · Ry(pitch) · Rx(roll)` built in NumPy,
  `atol=1e-12`, recording the measured maximum. Do it on BOTH fixtures
  (the anchored one against the same product conjugated by its rest
  placement and its anchor). RED.
- [ ] 1.4 **The hexapod's own inverse round-trips.** Transcribe
  `Chassis._to_chassis` (`projects/Robots/hexapod_spiderbot_model/simulation/spiderbot.py:146-163`)
  into the test, unchanged, and assert that it returns a probe point
  carried by the `Free`'s composed matrix to within `1e-9` mm at every
  pose. This is the case that says the framework's composition is the one
  the project's leg solutions depend on. The hand-written equivalent
  measures **1.42e-14 mm**; record the `Free`'s. RED.
- [ ] 1.5 **Unbound coordinates are the identity and still read
  unbound.** Bind `roll`, `pitch`, `yaw`, `z`; assert `pose.x.value` and
  `pose.y.value` are `None`, that `declared_ports` still reports them,
  that the published translation's first two components are the plain
  string `'0'` (not an expression, not `'0.0'` built from a product), and
  that the composed matrix equals the same pose with `x` and `y` bound to
  `0.0`, `atol=0`. RED.
- [ ] 1.6 **All six unbound places nothing.** A realized
  `FloatingChassis` nothing binds carries NO motion operations at all.
  RED (weakly — record what it distinguishes).
- [ ] 1.7 **The binding order of the six does not matter.** Two benches
  binding the six in opposite orders: identical `serialized(node)` and
  identical composed matrices, `atol=0`. This is the whole point of the
  joint and the one thing four separate joints could not give before
  ADR-093. RED.
- [ ] 1.8 **Re-binding one coordinate re-places the whole joint.** Bind
  all six, then re-bind `roll` alone: the operations list has the same
  length and shape, the other five values survive, and the matrix is the
  new pose. Then re-bind `roll` to its old value and assert the matrix
  returns, `atol=0`. RED.
- [ ] 1.9 **The anchor.** `AnchoredFloat` bound in `yaw` alone turns
  about the line through its declared `at`; the same body declaring
  `Free()` with the default anchor does not; the centring pair appears in
  the run for the first and not for the second. Assert the operation
  KINDS as well as the matrix. RED.
- [ ] 1.10 **Assigning the joint as a whole is refused.**
  `chassis.pose = 12.0` raises naming the node, the joint and the six
  coordinates, and the node carries no motion afterwards. RED.
- [ ] 1.11 **`axis` and `range` are refused.** `Free(axis=(0, 0, 1))` and
  `Free(range=(-10, 10))` raise at the declaration (a `TypeError` from
  the signature is acceptable; assert the message names what a `Free`
  takes). RED.
- [ ] 1.12 **`at` resolves against the instance.** `at` from a declared
  parameter, from a derived formula, and from a callable of the realized
  node; and the three realization refusals `at` already has (two
  components, an undeclared token, a callable that raises), naming the
  class, the joint and `at`. Characterisation of the inherited path —
  say so in the method. RED on the name only.
- [ ] 1.13 **A symbolic binding publishes ordinary operations.** Bind the
  six from expressions in the animation time; assert the serialized
  operations are exactly `['r', …]`, `['r', …]`, `['r', …]`, `['t', […]]`
  carrying `$t`, that the document gains no key outside the set
  `JointDocumentTest` already asserts, that `set_keyframe` makes them
  numeric and `clear_keyframe` restores them. The measured shape to
  expect is in `design.md` §9. RED.
- [ ] 1.14 **The declaration is exported and costs no import.** `Free` is
  in `solid_node.motion.joints.__all__` and reachable from the module;
  extend `test_the_kinds_are_exported_from_the_joints_module` with the
  name rather than writing a second test; `JointImportCostTest` still
  passes with no new module pulled. RED on the name.

## 2. Red first: the relation, the refusals, and the wiring that is refused

These land in `tests/test_couplings.py` and `tests/test_ports.py`. The
three seams they exercise were each measured on the current tree; the
measurements are in `design.md` §3, §7 and §8 and in
`evidence/probe_multi_coordinate_seams.py`, with
`evidence/probe_wiring_keyword.py` as the evidence for the wiring
REFUSAL. Quote the measured message in the test's docstring so a later
reader can see what it replaced.

- [ ] 2.1 **A relation reaches one coordinate by path.**
  `tilt.drives(chassis.pose.pitch)` from a root driver, and
  `lift.drives(chassis.pose.z, ratio=2.0)`: the chassis is placed, the
  other four coordinates stay unbound, and the relation inverts (bind the
  driven end and read the driver's, the way the file already does for a
  `Revolute`). RED — today `read_through` raises
  `SidewaysReadError: cannot read 'pose' off the Chassis declaration …
  a sibling's parameter is not a value in a class body`.
- [ ] 2.2 **A relation stated in the joint's own class body.**
  `pose.roll.drives(<something>)` written on the class declaring the
  `Free`, resolved through `OwnRef`. RED.
- [ ] 2.3 **The path grammar over more segments.** A `Free` two levels
  down — `shoulder.chassis.pose.yaw` — resolves to the right coordinate
  on the right realized node. This is the case the `_walk` change exists
  for: it must pop TWO segments, not one. RED.
- [ ] 2.4 **The joint is not an end.** `tilt.drives(chassis.pose)` and
  `tilt.drives(chassis.pose.twist)` raise at CLASS DEFINITION, naming the
  joint and listing the six. RED — today the first raises the wrong
  refusal and the second raises *"that path already names a coordinate,
  and a coordinate has no parts"*.
- [ ] 2.5 **The node is not an end.** A child whose class declares one
  `Free` and nothing else, named as a relation end, raises at class
  definition listing the six. RED — and record that today
  `_the_one_joint` would return the `Free` itself (`len(joints) == 1`),
  giving a declaration with no coordinate rather than an error.
- [ ] 2.6 **A `Free` cannot be wired, in either role.**
  `Chassis(pose=pose)` and `Chassis(**{'pose.roll': roll})` both raise at
  class definition, naming the joint, listing the six and saying they are
  bound by assignment or by relation; NO wiring is recorded on the
  declaration in either case. RED — and record what today does instead:
  the first is silently taken for a PARAMETER and reaches the child's
  constructor, and the second raises the misleading *"Chassis cannot
  receive a coordinate as 'pose.roll', because it declares no port or
  joint of that name; it declares: "*, which would have become an
  ACCEPTANCE once `declared_ports` reported the six. That is the reason
  the refusal is explicit rather than incidental.
- [ ] 2.7 **A one-coordinate joint's wiring is untouched.** The existing
  wiring cases in `tests/test_ports.py` stay green with no edits, and a
  `Revolute` wired as `Arbor(turn=turn)` still binds and places. GREEN
  before and after — a characterisation guard, say so in the method.
- [ ] 2.8 **A name declared twice.** A class body declaring `pose` as
  both a `Free` and a `SignalPort` raises at class definition. RED — and
  record that today `_refuse_coordinate_clash` returns early and the last
  assignment silently wins.
- [ ] 2.9 **The dotted binding path.** After a RELATION has bound
  `pose.roll`, assert the node's `__dict__` has NO key `'pose.roll'` and
  the coordinate's slot holds the value. This is the direct guard on the
  measured `setattr` hole, and it is why `set_coordinate` is needed even
  though the wiring route is closed: `ResolvedEnd.bind` is the relation
  path. RED.

## 3. Red first: cycles 1 and 2, with a free joint in them

ADR-093's rule is stated over "the operations a joint's placement
produces", a contiguous run of any length. A `Free` is the first joint
that places up to SIX operations AND owns more than one coordinate, so it
is the hardest case the contract has. These are ADDITIONS to the cycle-1
and cycle-2 sections, not modifications of them.

- [ ] 3.1 Add a `Free` to the cycle-1 composition fixture — a class
  declaring `slide = Prismatic(...)`, `pose = Free()` and an off-origin
  `spin = Revolute(...)` — and assert that binding the coordinates in
  several scrambled orders gives the same operations list and the same
  composed matrix, with the free joint's run unbroken at its own slot.
  RED.
- [ ] 3.2 **Contiguity with a hand-written rotation in the middle.** The
  same fixture with a `rotate()` applied between two bindings: the
  hand-written operation sits outside the whole joint block and the free
  joint's run is still unbroken. RED.
- [ ] 3.3 **Re-binding one coordinate of the free joint** returns its
  whole run to its own slot, leaving the siblings where they were. RED.
- [ ] 3.4 **A `Free` beside an `Orbit`.** Cycle 2's `SpunAndCarried`
  shape with a `Free` declared first: the orbit's single translation
  stays outside it. RED.
- [ ] 3.5 The whole of the existing cycle-1 and cycle-2 sections stays
  green with NO edits. **If any of them needs an edit, stop and say why
  before making it** — an edit there means this cycle changed the
  composition contract, which it must not.

## 4. The implementation

- [ ] 4.1 `solid_node/motion/joints.py`: `Joint` grows an ordered
  `coordinates` mapping of full name to `Port`, built in `__init__` for
  the one-coordinate kinds as `{self.name: self.coordinate}` and named in
  `__set_name__` where the single coordinate is named today
  (lines 200-203). `coordinate` keeps its present meaning and stays
  ABSENT on a `Free`, so every "one coordinate" seam refuses rather than
  mis-handles.
- [ ] 4.2 `Joint` grows an `axes(node)` hook returning
  `(self.arguments(node)[0],)`, and `_carry(node, axes, points)` carries
  a TUPLE of axes through the one inversion it already computes,
  mirroring what cycle 2 did for points. `place` passes the carried axes
  and points to `placement` in that order, so `Revolute.placement`,
  `Prismatic.placement` and `Orbit.placement` keep their signatures
  unchanged.
- [ ] 4.3 `Free`: the declaration, the six ports, the bound-coordinates
  view its `__get__` returns, the `__set__` refusal, `resolve` (an `at`,
  no axis, no range), `axes` returning the three unit directions, and
  `placement` reading the six slots and emitting the run of `design.md`
  §4. Export it from `__all__`.
- [ ] 4.4 `solid_node/motion/ports.py`: `declared_ports` prefers the
  `coordinates` mapping and falls back to the singular `coordinate` for a
  derived coordinate; add `set_coordinate(node, name, value)`, splitting
  on the last dot.
- [ ] 4.5 `solid_node/motion/couplings.py`: `read_through` gains a branch
  for a joint owning several coordinates; `PathRef.__getattr__` steps
  into one and refuses an unknown part by name; `PathRef._walk` pops as
  many segments as the coordinate's name has parts; `PathRef.declaration`
  and `_the_one_joint` refuse a multi-coordinate joint by name;
  `ResolvedEnd.bind` and `Wiring.apply` bind through `set_coordinate`.
- [ ] 4.6 `solid_node/node/declarative.py`: its local `_coordinate_of`
  and `_is_joint` learn the `coordinates` seam, so a `Free` passed as a
  child keyword is refused as a wiring source; `_check_wiring` refuses a
  keyword that is a dotted coordinate name of the child by the same
  message rather than by "declares no port or joint of that name"; and
  `_refuse_coordinate_clash` sees a `Free`. A wiring keyword stays an
  identifier naming a port, a derived coordinate, or a joint that owns
  one coordinate.
- [ ] 4.7 Run the full suite. Nothing outside the new sections may
  change. Record the before and after counts.

## 5. Specs and decision record

- [ ] 5.1 Sync the three delta specs into
  `openspec/specs/{joints,ports,couplings}/spec.md`. The two RENAMEs land
  as renames: no requirement is lost and every baseline scenario heading
  survives verbatim.
- [ ] 5.2 ADR-095, `docs/adrs/NODE/ADR-095-a-free-joint-owns-six-coordinates.md`
  — Accepted, extends ADR-088, depends on ADR-093, related to ADR-094 —
  recording the naming rule, the fixed composition, the parent-frame
  reading of the three directions, unbound-is-identity, and the gimbal
  lock the design record accepted. Add its row to `docs/adrs/README.md`
  in chronological order.
- [ ] 5.3 `docs/architecture.md` §Joints: rewrite the "A joint OWNS one
  coordinate" passage to say one or more, state the naming rule once, and
  add the free joint's composition beside the revolute's, the prismatic's
  and the orbit's.
- [ ] 5.4 `docs/api-reference.rst`: `Free` beside `Orbit` under Joints,
  with the section's prose updated — it currently says "the
  one-coordinate joint declarations" and "two of the three".
- [ ] 5.5 `docs/driving.rst`: a passage "A body that floats", with the
  hexapod chassis as the example, the six names, the fixed composition
  and the four-of-six binding.
- [ ] 5.6 `docs/changelog.rst` `Unreleased`: the free joint entry, in the
  voice of the orbit entry above it.
- [ ] 5.7 `tests/test_docs_exports.py` passes unchanged — this cycle adds
  no `.. solid-node::` directive and no committed export. Confirm rather
  than assume.

## 6. The plan note and the findings

- [ ] 6.1 `workflow/docs/composed-joints.md`: mark §6 taken up by this
  change, as §4 and §5 are marked; close open question 7 (identity) and 8
  (no range) in §7 with the reasoning, and carry 9 (Euler versus
  quaternion) with the two new open questions this cycle raises — the
  export mapping and the frame `at` is read in.
- [ ] 6.2 `workflow/warts.md`: the hexapod's entry (lines 815-836)
  currently reads *"The `Free` joint it may still prefer is a separate,
  unbuilt primitive and stays open"*. Mark that half FIXED by this cycle,
  naming the change and the ADR, and leave the rest of the entry as it
  is.
- [ ] 6.3 Do NOT touch `libresolid-studio/docs/motion-general-refactor.md`
  or any project. The hexapod's stage B is its own cycle in its own
  repository.

## 7. Evidence

- [ ] 7.1 `evidence.md`, in the shape cycle 2's has: the full suite
  before and after; the red text of every case in tasks 1-3, weak reds
  separated from strong ones; the mechanism as implemented; the three
  measured seam holes with the messages they replaced; the hexapod
  fixture's measured maximum deviation at each of the seven poses;
  cycles 1 and 2 green unedited; the serialization probe re-run against
  the real `Free`; what was deliberately not done.
- [ ] 7.2 **Pixels.** `solid snapshot` on a small bench whose body is
  placed by a `Free` at three poses — level, rolled, and lifted — and one
  at `pitch=90` so the gimbal-lock pose is on the record as an image
  rather than only as a number. Keep them under `evidence/`.
- [ ] 7.3 **Nothing existing moved.** The framework's own before/after on
  the joint-carrying fixtures of the existing suite, by matrix
  comparison, not by "the tests pass".
- [ ] 7.4 Re-run `evidence/probe_serial.py` against a real `Free` and
  record the diff against the hand-written shape recorded in
  `design.md` §9. They must be identical.

## 8. Open questions to close or carry

- [ ] 8.1 Carry: a quaternion `Free`, and what a driver would bind for
  one.
- [ ] 8.2 Carry: the MuJoCo `free` / Modelica `FreeMotion` export
  mapping. `Free` is the joint where both targets have a native element,
  so it is the cheapest one to get wrong by guessing.
- [ ] 8.3 Carry: whether `at` is read in the parent's frame or the body's
  own. The hexapod cannot tell them apart; the rule chosen is the
  parent's frame, by consistency with ADR-088.
- [ ] 8.4 Close: wiring a `Free` coordinate downward is REFUSED BY NAME
  in this cycle, not left open. The dotted keyword works and is
  deliberately not offered; no project has asked. A project that later
  needs one is a new sighting, arriving with a real call site to judge
  the spelling against.
- [ ] 8.5 Close or carry: the cost of re-placing six operations on every
  one of six bindings. Nobody has measured it; if a bench is cheap to
  write, measure it here rather than carrying it.
