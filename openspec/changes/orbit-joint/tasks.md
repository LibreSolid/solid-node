## 1. Red first: the orbit

All of this lands in `tests/test_joints.py`, in a new section for the
orbit placed after §1.6 (motion discipline), and uses the module's
existing helpers `serialized(node)`, `motions(node)` and `numbers(...)`.
**Every case below MUST be run and seen RED on the current tree before
task 2 begins, and the RED message recorded in `evidence.md`** — a case
that is green before the change is testing nothing. Most will be red with
`ImportError`/`NameError` on `Orbit`, which is a weak red: for each of
those, ALSO record what the case asserts that a hand-written equivalent
would fail, so the evidence says more than "the name does not exist yet".

Assert the composed MATRIX, not only the operations list, wherever a
frame or an order is at stake. Use
`solid_node.node.base._compose_world_matrix` against a hand-written NumPy
product.

**On tolerances.** Two different acceptances, and they must not be
confused:

- the ATTITUDE is exact. The rotation block of the composed matrix is the
  identity to a deviation of exactly `0.0`, at every angle, because the
  operation is a `Translation` and carries no rotation at all. Assert
  with `atol=0`.
- the POSITION is not. `cos(90°)` is `6.1e-17` in IEEE double, so
  `(cos θ − 1)·v` at θ=90 with `v=(10,0,0)` gives `-9.999999999999998`,
  not `-10.0` (measured; see `design.md` §6). Two different float
  expression trees for the same rotation differ by ~1e-15 mm. Assert
  positions with an explicit, stated tolerance — `atol=1e-9`, the
  module's own `_SNAP` — and say in the test why it is not zero. **Do not
  write `atol=0` on a trigonometric comparison and then loosen it when it
  fails.**

- [ ] 1.1 **Fixtures.** A `Carried` node class declaring
  `orbit = Orbit(axis=(0, 0, 1), unit='deg')` on a body its parent places
  by `translate([0, -2.5, 0])`, and a `CarriedAtAPoint` declaring
  `Orbit(axis=(0, 1, 0), carries=<a derived off-axis point>)` on a body
  placed by a `rotate` and a `translate` (so the rest placement has a
  non-trivial rotation part and the carry through it is exercised).
- [ ] 1.2 **The attitude is untouched.** Bind the orbit at θ ∈ {0, 17,
  90, 213.5, 360} and assert the composed matrix's rotation block equals
  the rest placement's rotation block with `atol=0`, on both fixtures.
  RED: `Orbit` does not exist.
- [ ] 1.3 **The carried point lands where the rotation says.** At the
  same angles, assert the carried point's world position equals
  `R(θ, axis, about at) · p` computed by hand in NumPy, `atol=1e-9`. Do
  it for the DEFAULT carried point (the body's own placed origin) and for
  the STATED one. RED.
- [ ] 1.4 **One operation, and it is a translation.** `serialized(node)`
  is exactly one `['t', [...]]` per binding; re-binding replaces it and
  leaves one. RED.
- [ ] 1.5 **The default carried point is the placed origin, exactly.**
  Two bodies placed identically, one declaring `Orbit(...)` with no
  `carries` and one declaring it with `carries=<the same point written
  out>`: identical composed matrices, `atol=0` for the rotation block and
  `atol=1e-12` for the position (the default takes one derivation fewer,
  so the two need not be bit-identical — record which is which). Prove it
  for a body placed by a `translate` and for one placed by a
  `rotate`+`translate` pair. RED.
- [ ] 1.6 **The anchor may be any point of the line.** Same axis, two
  different `at` on it, same carried point: identical placement,
  `atol=1e-9`. This is the projection of the along-axis component. RED.
- [ ] 1.7 **A carried point on the axis is refused by name.** A body
  placed at the parent's origin declaring `Orbit(axis=(1, 0, 0))` — the
  V8's connecting rod case. Assert the refusal is raised AT BINDING, that
  its message names the node (through `_where`), the joint, the axis, the
  anchor, the carried point and the derived radius, and that the node
  carries NO motion afterwards. RED.
- [ ] 1.8 **The argument refusals are realization-time.** `carries` of
  two components, `carries` naming an undeclared token, `carries` a
  callable that raises: `ParameterError` at realization naming the class,
  the joint and `carries`, before any child is realized — the same path
  `at` takes. RED.
- [ ] 1.9 **A symbolic binding publishes the trigonometry.** Bind the
  orbit from an expression in the animation time; assert the serialized
  translation carries `cos(` and `sin(` and `$t`, that the component the
  circle does not reach is the plain string `'0'` and not an expression,
  that `set_keyframe` makes all three numeric and `clear_keyframe`
  restores them, and that the document gains no new key. RED.
  The measured shape to expect is in `design.md` §6.
- [ ] 1.10 **A relation drives an orbit.** `shaft.turn.drives(disk.orbit)`
  and a second with a `ratio`; assert the body is placed as 1.3 says and
  that the relation inverts (bind the driven end and read the driver's,
  the way `tests/test_couplings.py` does for a `Revolute`). RED.
- [ ] 1.11 **A range on an orbit.** `range=(-90, 90)`: `170` raises
  `JointRangeError` naming the node's path, the joint, the value, the
  range and `deg`; `-90` and `90` are accepted. Inherited behaviour, so
  this is a *characterisation* test — say so in the method. RED only on
  the name.
- [ ] 1.12 **The declaration is exported and enumerable.** `Orbit` is in
  `solid_node.motion.joints.__all__` and reachable from the module;
  `declared_joints` reports it; `declared_ports` reports its coordinate
  as rotational with its unit; the import-cost test
  (`JointImportCostTest`) still passes with no new module pulled. Extend
  `test_the_kinds_are_exported_from_the_joints_module` with the name
  rather than writing a second test. RED on the name.

## 2. Red first: cycle 1's contract, with an orbit in it

ADR-093's rule is stated over "the operations a joint's placement
produces", a contiguous run of any length. An `Orbit` is the first joint
whose run is exactly one operation AND whose kind differs from the joint
next to it. These cases prove the contract holds over it; they are
additions to the cycle-1 section, not modifications of it.

- [ ] 2.1 Add an `Orbit` to the cycle-1 composition fixture — a class
  declaring `spin = Revolute(...)` at an off-origin anchor (three
  operations) then `orbit = Orbit(...)` (one operation) — and assert both
  binding orders give the same operations list `['t','r','t','t']` and
  the same composed matrix. RED.
- [ ] 2.2 **Contiguity with an orbit in the middle.** A `Prismatic`, then
  an off-origin `Revolute`, then an `Orbit`, plus a hand-written
  rotation: assert the four runs sit at their own slots in declaration
  order, the `Revolute`'s three operations unbroken, and the hand-written
  rotation outside all of them. This is the case task 1.8 of cycle 1
  wrote the guard for; make it real. RED.
- [ ] 2.3 **Re-binding the orbit of several joints** returns it to its
  own slot, leaving one operation. RED.
- [ ] 2.4 The whole of the existing cycle-1 section stays green with no
  edits. **If any cycle-1 test needs an edit, stop and say why before
  making it** — an edit there means this cycle changed the composition
  contract, which it must not.

## 3. The implementation

- [ ] 3.1 `solid_node/motion/joints.py`: generalize
  `Joint._carry(node, axis, anchor)` to `_carry(node, axis, *points)`,
  returning the carried axis and a tuple of carried points from the one
  inversion it already computes. A point given as the module's
  own-placed-origin sentinel returns exactly `(0.0, 0.0, 0.0)` WITHOUT
  touching the inverse (`design.md` §3) — do not round-trip the placed
  origin through it and then snap, which would put residue in the
  common case for no reason.
- [ ] 3.2 `solid_node/motion/joints.py`: add
  `Joint.carried_points(node, anchor)` returning `(anchor,)`, and have
  `Joint.place` call it, pass the result through `_carry`, and splat the
  carried points into `placement`. `Revolute.placement` and
  `Prismatic.placement` keep their signatures and their bodies unchanged.
- [ ] 3.3 `solid_node/motion/joints.py`: `Joint.resolve` resolves a
  fourth argument where the subclass declares one, and `Joint.place`
  unpacks `[:3]` so `_refuse_out_of_range`'s index 2 keeps meaning the
  range. Keep ONE resolution path — `_vector` — for `carries`, so its
  refusals read like `at`'s by construction rather than by imitation.
- [ ] 3.4 `solid_node/motion/joints.py`: the `Orbit` class.
  `coordinate_kind = RotationalPort`, `default_unit = 'deg'`,
  `__init__(axis, at=(0, 0, 0), carries=None, range=None, unit=None)`,
  `carried_points` returning the anchor and the carried point or the
  sentinel, and a `placement` that builds `v`, `b` and `r`, makes the
  on-axis refusal, and returns one `Translation`. Import `cos` and `sin`
  from `solid_node.math` INSIDE the method, as the module's other
  placements import their operations, so the module's import cost does
  not move (`JointImportCostTest` pins it).
- [ ] 3.5 `solid_node/motion/joints.py`: `__all__` gains `'Orbit'`. The
  module docstring gains a short passage on the carried body — what it is
  for, and that the radius and the phase are derived — beside the
  existing one on `Revolute` and `Prismatic`.
- [ ] 3.6 The on-axis refusal's error class: raise the module's existing
  `ValueError` shape the non-numeric rest placement uses, or a named
  class if the message reads better for one. Decide on the evidence of
  the test in 1.7 and state the choice in `evidence.md`; do NOT export a
  new error name unless a test needs to catch it specifically.
- [ ] 3.7 Run tasks 1 and 2. Everything green. Then the whole suite:
  `.venv/bin/python -m pytest` from the worktree with `PYTHONPATH="$PWD"`.
  `tests/test_couplings.py`, `tests/test_animator_tag.py`,
  `tests/test_simulate_split.py` and `tests/test_ports.py` must be green
  **without edits**; an unexpected edit there is a finding, not a chore.

## 4. Specs and decision record

- [ ] 4.1 `docs/adrs/NODE/ADR-094-<slug>.md`: "An orbit carries a point,
  and derives its radius". Status **Accepted**, **Extends** ADR-088,
  **Depends on** ADR-093 (the contiguous run at one slot) and ADR-022
  (degree-trigonometry parity), related to ADR-028. Record in its Context
  the four sightings and the two irreconcilable spellings the projects
  asked for; in its Decision the `carries` keyword, the own-placed-origin
  default, the derived radius and the refusals; in its Consequences the
  rotational coordinate that emits a translation, the bind-time refusal,
  and that `Revolute`'s own-placed-origin `at` stays OPEN.
- [ ] 4.2 `docs/adrs/README.md`: the ADR-094 row in the NODE section in
  chronological order, and "extended by 094" on ADR-088's row.
- [ ] 4.3 `docs/architecture.md` §Joints (the passage beginning "**Joints**
  (spec `joints`) are the two one-coordinate lower pairs"): it says
  **two** pairs and lists the two placements. Rewrite it for three —
  including the orbit's single translation, the carried point and its
  default — rather than appending a note.
- [ ] 4.4 `docs/api-reference.rst`, the Joints section: an
  `.. autoclass:: solid_node.motion.joints.Orbit` beside `Revolute` and
  `Prismatic`, and a sentence in the section's prose that one of the
  three carries a body without turning it. The class docstring is the
  published API text, so it must state the carried point, the default and
  the refusal in its own words.
- [ ] 4.5 `docs/driving.rst`, the joints passage (around lines 191-230):
  a SHORT passage introducing `Orbit`, with the cycloidal disk as the
  example — the disk carried at the eccentric radius while spinning on
  its own centre, `spin` declared before `orbit` so the spin is inside.
  Say that the radius and the phase are never typed and why that matters,
  and keep it to a paragraph and one code block: this page is a tour, not
  a reference.
- [ ] 4.6 `docs/changelog.rst`, `Unreleased`: one entry at the top, in
  the form the existing entries use — what a carried body cost before,
  the declaration, what a project now writes (use OpenCycloid, whose
  `-1.0` ratio term disappears), and what does NOT change (no document
  format, no viewer, no operation kind, nothing deprecated, no existing
  pose moves). Close with "(OpenSpec change ``orbit-joint``; ADR-094,
  extending ADR-088.)".
- [ ] 4.7 Sync the delta into `openspec/specs/joints/spec.md`.
  **NOT to be done by the implementer:** report first; the orchestrator
  syncs and archives after review. Note for whoever does: `openspec
  archive` refuses a MODIFIED requirement block that DROPS or RENAMES a
  scenario heading present in the baseline, so the four modified blocks in
  this change carry every existing heading verbatim and only ADD.

## 5. The plan note and the findings

- [ ] 5.1 `workflow/docs/composed-joints.md`: mark §5 taken up by this
  cycle and note that the OpenSpec change is now the authority for it;
  close open question 5 (the spelling) in §7 with the decision and the
  four projects it was checked against; leave §6 and the `free-joint`
  questions provisional, and leave question 6 (the export target) open,
  now carried by `design.md`'s open questions. Record in §8 that the
  disagreement is now RESOLVED-BY-DECISION rather than by evidence: no
  project wrote the ratified spelling, and what changed is that the cost
  to each of the four has been read off its own axis line and found to be
  one renamed keyword or one derived point.
- [ ] 5.2 `workflow/warts.md`: mark the carried-body sightings fixed by
  cycle `orbit-joint` (ADR-094), in place, each keeping its evidence —
  OpenCycloid's "a carried body whose attitude the orbit leaves alone",
  YouCanBuildDog's "A carried body: the orbit primitive, second
  sighting", the V8's rod, and the Internal Cycloidal Actuator's "`Orbit`
  preference remains an open want". Do **not** mark as fixed: the
  own-placed-origin anchor for `Revolute`'s `at`, the `.repeat()`
  relation fan-out, the multi-source relation, the declaration-site
  joint. Say beside each project which of those it still waits on
  (OpenCycloid: the fan-out; YouCanBuildDog: nothing else — it becomes
  refactorable; the V8: the own-placed-origin for its four timing gears).
- [ ] 5.3 `libresolid-studio/docs/motion-general-refactor.md` is SHOP
  material in a different repository. Do not edit it. Report what it
  needs and let the pilot place it: the `deferred` rows for OpenCycloid,
  YouCanBuildDog and v8-engine should record that the orbit blocker is
  lifted by ADR-094, and which further primitive each still waits on.

## 6. Evidence

- [ ] 6.1 **The Internal Cycloidal Actuator's algebraic identity, as a
  framework fixture.** Its proposal records the identity in full: writing
  `rest = T_t R_r`, `B = BORE_AXIS_POINT`, `c0 = R_r B + t` the rest bore
  centre and `sigma = -theta/8 + mesh_phase`, today's three hand-written
  operations give `T_t R_r T_carry R_sigma T_(-B) = T_c(theta) R_(r+sigma) T_(-B)`
  and the orbit-plus-spin form gives
  `T_Delta . T_c0 R_sigma T_(-c0) . T_t R_r = T_c(theta) R_(r+sigma) T_(-B)`.
  Build a fixture in `tests/test_joints.py` reproducing BOTH sides with
  the project's own numbers — `BORE_AXIS_POINT = (0.0, 0.0, -2.000)`,
  `DISK_1_BORE_CENTRE = (0.378316, -5.25, 1.963896)`,
  `REDUCTION = 8`, the project's `_rotate_y` helper written out — and
  assert the two composed world matrices agree over a sweep of input
  angles and at least two `mesh_phase` values.

  **Acceptance, in two parts, and do not merge them:**
  - the ROTATION blocks agree to `atol=0` — the orbit adds no rotation,
    so both sides carry exactly `R_(r+sigma)`;
  - the POSITIONS agree to `atol=1e-9` mm. Not zero: the two sides are
    different float expression trees over the same trigonometry
    (`design.md` §6). Record the MEASURED maximum deviation in
    `evidence.md`. If it exceeds 1e-9 mm, that is a finding — report it,
    do not raise the tolerance.
  - separately, assert `sqrt(0.378316² + 1.963896²)` — the radius the
    framework derives — is `2.0000` mm to 1e-4, the `_axis_distance` the
    project's proposal records, and that the derived phase is the
    −79.095935297° it records. **This is the number that proves the
    derivation replaces what the project may not type.**
- [ ] 6.2 **YouCanBuildDog's `swung_offset`, as a second fixture.** Its
  `R(θ)·s − s` written out with the two measured spans
  (`(22.9431, -32.7661)` and the short back-left `(22.8404, -32.7450)`)
  against an `Orbit` with `at` at the chassis pivot and `carries` at the
  chassis pivot plus the span. Assert the framework's derived radii are
  `40.0000` and `39.9239` mm to 1e-4 and the derived phases `-55.000°`
  and `-55.104°` to 1e-3 — the numbers its proposal typed as `radius=`
  and `phase=`, now derived. **This is the evidence for the acceptance
  sentence in `design.md` §7 that the ratified spelling costs the dog
  nothing.**
- [ ] 6.3 **No pose comparison of the catalogue is required.** Nothing
  existing changes: `Orbit` is additive, `Revolute` and `Prismatic` are
  untouched, and `_carry`'s generalization returns the same carried axis
  and anchor it returns today. Instead: (a) the whole suite green,
  (b) the cycle-1 composition tests green **with an Orbit in the
  fixture** (task 2), and (c) `git diff` on
  `solid_node/motion/joints.py` showing `Revolute.placement` and
  `Prismatic.placement` byte-identical. Record (c) in `evidence.md`.
  Say honestly in `evidence.md` that this cycle therefore has NO
  measurement over real machines — the four projects' adoption at stage B
  is where that evidence comes from, and it is not this cycle's.
- [ ] 6.4 **Pixels.** `solid snapshot` on a fixture carrying an orbit and
  a spin on one body, at several angles, and look at them: a body that
  travels a circle without turning is a thing the eye checks in one
  glance and a matrix assertion can be right about for the wrong reason.
  A green suite does not replace snapshot inspection.
- [ ] 6.5 **Re-run the design's serialization probe against the real
  `Orbit`** rather than the hand-built prototype, and record the actual
  published translation for a symbolic binding, the keyframed values, and
  the cleared values, in `evidence.md`. If the real output differs in any
  way from `design.md` §6, that difference is a finding to report before
  the cycle closes.

## 7. Open questions to close or carry

- [ ] 7.1 **The declaration order the four projects wrote.** Three of the
  four proposals list `orbit` BEFORE `spin`/`swing` while their pose
  needs the rotation innermost — they were written before ADR-093 fixed
  first-declared-innermost. `design.md` §7 states them in the corrected
  order. Confirm, without editing any project, that the corrected order
  is what each project's algebra needs, and report the three sites so the
  stage-B refactors do not transcribe the pre-ADR-093 listing.
- [ ] 7.2 **The V8's `at`.** Its proposal writes
  `Orbit(axis=(1, 0, 0), at=(0, 0, CRANK_RADIUS))` and its own prose says
  that point is the CARRIED point, not a point on the line. Under the
  ratified spelling it becomes `carries=`. Confirm the crank axis passes
  through the cylinder unit's origin (so `at` may keep its default) and
  report it; if it does not, the acceptance sentence in `design.md` §7 is
  wrong and must be corrected before the cycle closes.
- [ ] 7.3 **The export target** (question 6 of the plan note) stays open
  and is recorded in `design.md`, not designed. Do not close it.
