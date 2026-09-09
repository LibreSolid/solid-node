## 1. Red first: the tests that fail on the current tree

- [ ] 1.1 Write `tests/joint_project/`, in the style of
  `tests/declarative_project/`: an `__init__.py`, a `parts.py` with two
  simple `Solid2Node` leaves (a link and a wheel), and an `arm.py`
  holding (a) `Forearm(AssemblyNode)` declaring
  `elbow = Revolute(axis=(0, 0, 1), at=(0, reach, 68), range=(-135, 135),
  unit='deg')` over a declared `reach = Length(160.0)`, placed by its
  parent with `rotate(90, [1, 0, 0])` then `translate([0, reach + 81.5,
  68])` — Thor's elbow, with the numbers Thor has; (b) an `Arm` root
  declaring a `Driver` and binding the elbow from it in `simulate()`;
  (c) `Arbor(AssemblyNode)` declaring `turn = Revolute(axis=(0, 0, 1),
  at=<callable reading a position off the instance>, unit='deg')` and
  two children wired `wheel = Wheel(turn=turn)`, `rod = Rod(turn=turn)`,
  each declaring its own `turn`; (d) a `Carriage` declaring
  `travel = Prismatic(axis=(1, 0, 0), range=(0, 200), unit='mm')`.
- [ ] 1.2 `tests/test_joints.py`, declaration: `Revolute` and
  `Prismatic` import from `solid_node.motion.joints`; a class carries
  its joints by name with axis, anchor, range and unit readable off the
  class without constructing it; `declared_joints` walks the MRO
  base-first and a subclass redeclaration wins; a class declaring a
  joint and a port of one name raises at class definition naming both.
- [ ] 1.3 The coordinate: reading a joint off an instance yields a
  `BoundPort` of the right domain and unit, unbound until something
  binds it; two instances read their own slots; assignment binds and a
  later read gives the bound value; `declared_ports` reports the joint's
  coordinate under the joint's name beside a plain port, with the
  joint's domain and unit; a joint's coordinate carries no scale and no
  `out`.
- [ ] 1.4 The frame carry, on Thor's numbers (assert the serialized
  components to a tolerance and, for the axis, that they are the exact
  snapped values): with the fixture's
  `Forearm` placed by `rotate(90, [1, 0, 0])` then
  `translate([0, 241.5, 68])` and the joint declared
  `axis=(0, 0, 1), at=(0, 160, 68)`, binding the elbow to `30` leaves
  the node's serialized operations equal to
  `['t', ['0', '0', '-81.5']]`, `['r', '30', [0, 1, 0]]`,
  `['t', ['0', '0', '81.5']]`, then the two rest operations — compared
  against the hand computation in the test's own docstring, and against
  `simulation/placing.py`'s `ELBOW_PIVOT` and `ELBOW_PIVOT_AXIS` quoted
  there. Assert the components to a tolerance, not by string equality of
  floats.
- [ ] 1.5 The degenerate case, the slide and numeric hygiene: a joint
  anchored at the node's placed origin produces one rotation and no
  centring translations; a `Prismatic` bound to `120` produces one
  translation along its local axis whose zero components are the plain
  number `0`, not an expression, and changing only its `at` changes
  nothing; a carried axis and anchor whose inversion leaves residue
  publish exactly `0`, `1` or `-1` where they are within `1e-9` of one
  (assert on the serialized strings, which is where residue would
  show).
- [ ] 1.6 Motion discipline: the joint motion is innermost (before the
  rest operations) and tagged with the assembly whose `simulate()` bound
  it; re-simulating at one instant leaves one motion; binding the same
  joint twice in one `simulate()` leaves the last, and binding again
  after a sweep has already dropped the previous operations succeeds; a
  joint bound with NO lifecycle phase running places its operations
  innermost, marked as motion and untagged, and survives an unrelated
  assembly's sweep; a joint bound by the node's own `simulate()` moves
  that node and is tagged with it; a
  hand-written `rotate()` and a joint motion on one node both survive,
  in application order; the rest placement is never swept.
- [ ] 1.7 Symbolic values: binding a joint from an expression in the
  animation time publishes that expression as the operation's angle;
  `set_keyframe` makes it numeric, `clear_keyframe` restores it; binding
  from a `Driver` read publishes the driver token.
- [ ] 1.8 Range: a numeric binding outside the range raises
  `JointRangeError` naming the node's path, the joint, the value, the
  range and the unit, and leaves the node unmoved; the bounds are
  inclusive; a symbolic binding is not checked; a joint with no range
  accepts anything.
- [ ] 1.9 Argument resolution: a joint anchored on a declared parameter
  follows that parameter per instance; a callable anchor is called once
  at realization with the realized node and its return used; a token the
  class does not declare, an axis that is not three numbers, a
  zero-length axis and a reversed range each raise `ParameterError` at
  realization naming the class, the joint and the argument, with no
  child of the refused instance realized; two instances differing only
  in a joint anchor share one `uniq_id`.
- [ ] 1.10 Wiring: a coordinate wired into a child binds that child on
  every simulate, after the parent's own `simulate()` and before the
  child renders; two levels of wiring deliver the root's value to a
  grandchild in one enumeration; a wired child end declaring a scale
  converts; a repeated wired child is bound per instance; a wiring whose
  source is unbound raises naming parent, child and coordinate; a wiring
  whose child end is a joint moves the child's body; binding a wired
  child end by hand in the declaring parent's `simulate()` is refused
  naming parent, child and coordinate.
- [ ] 1.11 Wiring refusals: a keyword naming no port or joint of the
  child, and a value that is a coordinate of another class, each raise
  at class definition naming both classes and the keyword; an unknown
  plain keyword still raises the `TypeError` it raises today; a wired
  keyword is absent from the child's resolved parameters and from its
  identity.
- [ ] 1.12 The published document: build the fixture root, serialize it
  under `set_state` and under `set_keyframe`, and assert the joint's
  operations appear in the child's `operations` with the expected values
  and no new key anywhere in the document; take one snapshot of the
  fixture at two instants and assert the pose differs.
- [ ] 1.13 Import cost: `solid_node.motion.joints` imports the same
  `solid_node` modules as `solid_node.motion.ports` plus itself, and no
  `cadquery`, BRep kernel, STEP reader or `trimesh`, in a fresh
  interpreter; `solid_node.motion.couplings` still costs nothing. Widen
  the corresponding assertion in `tests/test_motion_package.py` (cycle
  1) rather than leaving two tests disagreeing.
- [ ] 1.14 Run the suite and record the failures: every test in 1.2–1.13
  fails on the tree as cycle 1 left it, for the right reason (the name
  is absent from `solid_node.motion.joints`, not a typo).

## 2. The joints module

- [ ] 2.1 `solid_node/motion/joints.py`: SPDX header, module docstring
  saying what a joint is (a pair that places a body, declared on the
  node it moves, owning one coordinate that is a port, with axis and
  anchor in the parent's frame), replacing cycle 1's placeholder text.
  Module-scope imports: `solid_node.motion.ports` only.
- [ ] 2.2 `JointRangeError(ValueError)`.
- [ ] 2.3 `Joint`: `__init__(axis, at=(0, 0, 0), range=None, unit=None)`
  storing the declaration and building `self.coordinate` as the port
  kind the subclass names, with the joint's unit; `__set_name__` naming
  itself and its coordinate, and refusing a name already declared as a
  port or a driver on a base (the `DriverDeclaration.__set_name__`
  shape); `__get__` returning the coordinate's slot; `__set__` doing the
  range check, the bind and the motion; `__repr__`.
- [ ] 2.4 `Revolute` and `Prismatic`: the port kind, the default unit
  (`'deg'` / `'mm'`), and the placement each produces.
- [ ] 2.5 `declared_joints(node_class)`: MRO base-first, per-class cache
  like `declared_drivers_of`.
- [ ] 2.6 Argument resolution: one function taking the declaration and
  the realized node, resolving `axis`, `at` and `range` — numbers,
  tokens and derived formulas through `evaluate`, or a callable of the
  node — validating three components, non-zero axis and ordered range,
  and raising `ParameterError` naming class, joint and argument. Store
  the resolved values in a private per-instance map.
- [ ] 2.7 The frame carry: compose the node's non-motion operations in
  list order by premultiplication through each operation's `matrix()`,
  invert, and carry the axis (rotation part, normalized) and the anchor
  (full transform, as a point). Raise by name when an operation's value
  is not numeric. `numpy` and the operations are imported inside this
  function.
- [ ] 2.8 Placement: `solid_node/node/base.py` gains the way to place an
  operation as motion — innermost, after existing motion, before rest,
  marked `_motion` — with no lifecycle phase current (a private sibling
  of `_place_operation`, or a flag on it), used by joints only; under a
  simulate phase the existing tagging and sweep registration are
  unchanged. A joint never uses the plain `rotate()`/`translate()` path
  for placement, because that appends outside a phase.
- [ ] 2.9 Numeric hygiene: snap carried components within `1e-9` of `0`,
  `1` or `-1`; omit the centring translations when every anchor
  component is zero to that tolerance; emit a plain `0` for a zero
  component of a `Prismatic`'s translation.
- [ ] 2.10 Application: `translate(-anchor)`, `rotate(value, axis)`,
  `translate(anchor)` for a `Revolute` and `translate(value * axis)` for
  a `Prismatic`, as the framework's ordinary `Rotation` and `Translation`
  operations placed through the motion seam of 2.8 (never through the
  plain `rotate()`/`translate()` path, which appends outside a phase),
  tagged under a simulate phase exactly as `_place_operation` tags;
  record the applied operations per joint on the
  instance and remove a previous binding's operations before applying,
  tolerating operations a sweep or a checkpoint restore already removed
  from the list.

## 3. The coordinate in the ports module

- [ ] 3.1 `solid_node/motion/ports.py`: `declared_ports` also collects a
  class attribute whose `coordinate` is a `Port`, under the attribute's
  name, base-first as today. No import of `motion.joints`; document the
  duck-typed seam in the function's docstring and why it is not an
  `isinstance` check.
- [ ] 3.2 Confirm `bind` needs no change: a joint's coordinate is an
  ordinary port slot with no scale, so binding goes through the existing
  path unchanged.

## 4. Realization and wiring

- [ ] 4.1 `solid_node/node/declarative.py`, `ChildDeclaration.__init__`:
  split the keyword arguments whose value is a port or joint declaration
  out of `kwargs` into `self.wiring`.
- [ ] 4.2 `ChildDeclaration.__set_name__`: validate each wiring against
  the owner's declared ports and joints and the child class's declared
  ports and joints, raising at class definition naming the declaring
  class, the child class, the keyword and what the child does declare.
  `RepeatDeclaration` delegates to the declaration it holds.
- [ ] 4.3 `ChildDeclaration.realize`: unchanged for parameters (wirings
  never reach `resolve_parameters`, so identity is untouched); record on
  each realized child the wirings that feed it, so the parent can bind
  them without re-deriving the mapping.
- [ ] 4.4 Joint arguments resolved at realization: call the resolver
  from the declarative realization path, after parameters are resolved
  and `check()` has run and before `realize_children`, so a refused
  instance has realized no child. Confirm the same happens for a joint
  declared on a class realized as a root.
- [ ] 4.5 `solid_node/node/assembly.py`, `_lifecycle_render`: after
  `self.simulate()` returns and before the phase is popped, bind every
  wiring this instance's declarations recorded, source to sink, through
  `bind`, wrapping an unbound-source failure to name parent, child and
  coordinate.
- [ ] 4.6 Refuse a hand binding of a wired child end from the declaring
  parent's `simulate()`, naming parent, child and coordinate: record the
  wiring on the child's slot at realization and check it in the bind
  path, so the wiring is the coordinate's one binder.
- [ ] 4.7 Run the suite green:
  `PYTHONPATH=$PWD /home/asa/devel/libresolid-studio/.venv/bin/python -m
  pytest tests -x -q`, from the worktree root. Record the command and
  the result.

## 5. Documentation

- [ ] 5.1 The user documentation gains the joint: what a joint declares,
  that its axis and anchor are in the parent's frame, that reading it
  gives its coordinate and binding it moves the body, the range, and
  passing a coordinate down to a child. Put it where ports are already
  taught (`docs/driving.rst` and its neighbours), with a worked example
  of an axis off the moving part's origin.
- [ ] 5.2 `docs/api-reference.rst`: autodoc entries for
  `solid_node.motion.joints.Revolute`, `.Prismatic`, `.JointRangeError`
  and `.declared_joints`, beside the Ports section.
- [ ] 5.3 `docs/changelog.rst`, "Unreleased": joints, the wiring by
  token, the range refusal, and that nothing is deprecated — a project
  keeps its hand-written motion until it chooses to move. Name this
  change and ADR-088.
- [ ] 5.4 Docs evidence: the import check from cycle 1's task 5.6 shape
  — every autodoc target resolves — plus a sphinx build only if the venv
  provides one. Say which was used.

## 6. Records

- [ ] 6.1 `docs/adrs/NODE/ADR-088-a-joint-owns-one-coordinate.md`,
  written after the implementation is green: the joint as owner of one
  coordinate that is a port and why it is not a `Port` subclass; axis
  and anchor in the parent frame; motion composed onto the rest
  placement by inverting it, applied at the binding, tagged by the phase
  that owns it; the downward wiring by token, validated at class
  definition; joint arguments resolved at realization and outside
  identity. Status Accepted; extends ADR-056 and ADR-066, reversing
  neither. Confirm 088 is still free when writing it.
- [ ] 6.2 `docs/adrs/README.md`: the ADR-088 row in the NODE table in
  number order, and the extends notes on the ADR-056 and ADR-066 rows.
- [ ] 6.3 `docs/architecture.md`: the Kinematics section gains the joint
  and the frame carry; the Node model section's list of what a class
  body declares gains it; the Map table's Motion row gains the `joints`
  spec and ADR-088.
- [ ] 6.4 `openspec validate joints --strict` passes, and every MODIFIED
  requirement still matches the baseline text it replaces after cycle 1
  synced its own deltas.

## 7. Roadmap

- [ ] 7.1 `workflow/motion/roadmap.md`, Progress table, row `2 joints`:
  fill "Applied" with the date and the implementation commit. Touch that
  row only.
