## 0. Before anything

- [x] 0.1 Work only in `solid-node/WTs/motion-catalogue-2` (branch
  `motion-catalogue-2`), with `PYTHONPATH="$PWD"` and the workspace venv
  `/home/asa/devel/libresolid-studio/.venv/bin/python`. Confirm
  `python -c "import solid_node; print(solid_node.__file__)"` prints the
  WORKTREE path: the venv's editable install points at the primary
  checkout and `PYTHONPATH` must shadow it. Never run a `git` write
  command anywhere, and never write inside
  `/home/asa/devel/libresolid-studio/projects/`.
- [x] 0.2 **Cycle 1 must be integrated first.** Confirm that
  `repeat-fan-out` has landed on this branch and that a `.repeat()` copy
  carries `index`: five migrations in task 7 read it. If it has not,
  STOP and report — do not implement around it.
- [x] 0.3 Record the FULL SUITE at the base: `.venv/bin/python -m pytest
  -x -q` from the worktree, exact counts, into `evidence.md`. Any failure
  here is pre-existing and must be shown to be so before task 6.
- [x] 0.4 **Capture the BASE poses of all 23 projects now**, before any
  source change, because this branch is where both captures run. Per
  project, from its own root, one at a time (the VM exhausts file
  descriptors):

      cd <project root>
      PYTHONPATH=.:<worktree> <venv>/bin/python \
        <shop>/docs/motion-general-refactor/capture_poses.py \
        capture <module:Class> <scratch>/<project>-<model>-before.json

  One capture per declared model (`pyproject.toml [tool.solid-node]`, or
  `solid models`), plus an `extra` pose file where the model has named
  instructions. The 23: 3DPrintedClocks, Thor, YouCanBuildDog,
  openflexure-microscope, Inmoov-sim, Prusa3-vanilla, OpenTorque-Actuator,
  openarm, pascaline, BCN3D-Moveo, Internal-Cycloidal-Actuator,
  hangprinter, openvmp, open_manipulator, poseidon, YouCanBuildBiPed,
  HACKberry, open_robot_actuator_hardware, snappy-reprap, Metamaquina2,
  hexapod_spiderbot_model, AlbertPro, science-jubilee. Record every
  capture's leaf and pose count in `evidence.md`. A capture that fails at
  the base is reported, not worked around.
- [x] 0.5 Re-read `evidence/survey.md`. It is the empirical basis of the
  whole change: if any row disagrees with the tree you find, STOP and
  report rather than adapting the design.

## 1. Red first: the rule

Lands in `tests/test_joints.py`. **Every case MUST be seen RED on the
current tree before task 5 begins, and the RED text recorded in
`evidence.md`.** A case red only with an `AssertionError` about numbers
must also record the numbers it read today, so the evidence says what was
there before.

- [x] 1.1 **A joint through the body's own origin needs no anchor.** A
  pinion class declaring `turn = Revolute(axis=(0, 0, 1), unit='deg')`,
  its parent placing it with `translate([40, 25, 0])`, bound to an angle:
  the node's motion is ONE rotation about `[0, 0, 1]` and no centring
  translations, and the pinion's own origin does not move. RED — today it
  emits `translate([-40, -25, 0])`, the rotation, `translate([40, 25, 0])`
  and swings the pinion about the parent's origin.
- [x] 1.2 **One class, several placements, one declaration.** Four copies
  of one class placed at four different points, all bound to the same
  angle: each spins about the line through its own placed origin, and all
  four resolve the same `_joint_arguments`. RED. This is the V8's four
  timing gears and Thor's thirteen.
- [x] 1.3 **The line turns with the body.** A body placed with
  `rotate(90, [1, 0, 0])` declaring `axis=(0, 0, 1)`: the published
  rotation's axis is `[0, 0, 1]` exactly. RED — today it publishes
  `[0, -1, 0]`.
- [x] 1.4 **Thor's elbow, in the forearm's own frame.** With the fixture
  rewritten (task 4), `axis=(0, 1, 0), at=(0, 0, 81.5)` and the parent
  placing `rotate(90, [1, 0, 0])` then `translate([0, 241.5, 68])`
  produces `translate([0, 0, -81.5])`, `rotate(30, [0, 1, 0])`,
  `translate([0, 0, 81.5])`, then the two rest operations. Keep
  `THOR_ELBOW_PIVOT_AXIS` / `THOR_ELBOW_PIVOT` as the module constants
  they are: this test's whole point is that the two numbers Thor writes
  by hand are now the two numbers the declaration writes.
- [x] 1.5 **A slide runs along the body's own axis.** The gantry's
  `rotate(90, [0, 0, 1])` on its carriage: `travel = Prismatic(axis=(1, 0, 0))`
  bound to 120 publishes `['120', '0', '0']`. RED — today `['0', '-120', '0']`.
  Add a SEPARATE case for what the old test really protected: the two idle
  components are the plain number `0`, not an expression multiplied by
  zero.
- [x] 1.6 **Two instances placed differently resolve identical
  arguments.** Two instances of one class, two different rotations and
  translations, same bound value: identical joint operations. RED.
- [x] 1.7 **A joint's line survives a change to the rest placement.** The
  same instance, placed, bound, re-placed differently, bound again: the
  joint's own operations are the same both times.
- [x] 1.8 **A symbolic rest placement no longer refuses a joint.** The
  fixture behind the existing "An unresolvable rest placement is refused"
  case: the body is now placed about the line its own frame states and
  nothing raises. RED — today it raises `ValueError`.
- [x] 1.9 **The normalized axis is snapped.** `axis=(0, 0, 3)` publishes
  `[0, 0, 1]` exactly, and an axis whose normalization leaves residue
  publishes no `e-` in any component. Replaces
  `test_residue_never_reaches_the_document`'s three-quarter-turn fixture,
  whose residue source is deleted; keep the heading and re-body it.
- [x] 1.10 **An anchor is published as written.** An anchor the project
  computes as `3e-17` still omits the centring pair (the `1e-9` test), and
  an anchor of `81.49999999999999` is published unchanged rather than
  rounded.

## 2. Red first: `Orbit`

- [x] 2.1 **`carries` defaults to `(0, 0, 0)` and resolves at
  realization.** `Orbit(axis=(0, 0, 1))` on a realized node has resolved
  carried point `(0, 0, 0)` before the node is placed. RED — today it
  resolves to the `_OWN_PLACED_ORIGIN` sentinel.
- [x] 2.2 **A defaulted carried point still refuses at binding when it
  lies on the line.** `Orbit(axis=(1, 0, 0))` with no `carries` on a body
  whose own origin is therefore on its own line: refused at the first
  binding, naming node, joint, axis, anchor, carried point and the radius
  of zero. Green today by a different route; assert it stays.
- [x] 2.3 **An orbit is stated in the body's own frame.** A disk
  declaring `Orbit(axis=(0, 0, 1), at=(0, 2.5, 0))` with no `carries`,
  placed by its parent anywhere: the disk's own origin travels the circle
  of radius 2.5 about the line its OWN frame states, attitude unchanged
  at every angle. RED where the parent places it.
- [x] 2.4 **The Internal Cycloidal Actuator's algebra still holds.**
  `ProjectAlgebraTest` is the one measurement over a real machine the
  orbit has. Restate its fixture in the disk's own frame — `spin` and
  `orbit` both at `at=BORE_AXIS_POINT`-shaped own-frame values from
  `evidence/survey.md` §2.3 — and keep the acceptance exactly as ADR-094
  set it: rotation-block deviation `atol=0`, position `atol=1e-9`. If it
  cannot be restated at that acceptance, STOP and report.
- [x] 2.5 `test_the_dogs_swung_offset_is_what_an_orbit_publishes` still
  passes untouched (YouCanBuildDog's bodies have identity placements).

## 3. Red first: `Free`

- [x] 3.1 **The three directions are the body's own, as literals.** A
  `Free` on a body its parent rotates: the published rotations carry
  `[1,0,0]`, `[0,1,0]`, `[0,0,1]` exactly. RED.
- [x] 3.2 **A floating body floats along its own axes.** With a bound `x`
  and a rotated rest placement, the published translation is
  `['x', '0', '0']`. RED. This is the reading ADR-095 left open; the test
  is what closes it.
- [x] 3.3 **An anchored `Free` turns about a point of its OWN frame**,
  and a defaulted `Free` on a placed body turns about the body's own
  origin and emits no centring pair. RED for the second half.
- [x] 3.4 The hexapod's fixtures — `test_the_composition_is_the_one_the_hexapod_hand_inverts`,
  `test_the_hexapods_own_inverse_round_trips`,
  `test_the_binding_order_of_the_six_does_not_matter` — pass UNEDITED
  (identity rest placement, so the two readings coincide). If any needs
  an edit, stop and report: that would mean the change reaches further
  than the design says.

## 4. Red first: the fixtures

- [x] 4.1 `tests/joint_project/arm.py`: `Forearm.elbow` becomes
  `Revolute(axis=(0, 1, 0), at=(0, 0, ELBOW_ACROSS_ARM), range=…,
  unit='deg')`, and the module docstring says the numbers are now the
  ones `art2.py` writes. The `reach` parameter no longer enters the
  anchor; `test_the_anchor_follows_the_parameter_per_instance` becomes a
  test that the anchor does NOT follow the parent's `reach`, which is the
  point — keep the heading, change the body.
- [x] 4.2 `tests/joint_project/arm.py`: `Arbor.turn` loses its
  `at=lambda node: node.built.bearings[node.index]` entirely and becomes
  `Revolute(axis=(0, 0, 1), unit='deg')`. Keep `_Movement` and `built`:
  `ArgumentResolutionTest.test_each_arbor_is_anchored_on_its_own_built_position`
  still needs a callable argument somewhere, so move it onto a joint that
  genuinely has an off-origin anchor rather than deleting the coverage.
- [x] 4.3 `Gantry`/`Carriage` keeps its quarter turn: it is now the
  fixture for 1.3 and 1.5 rather than for the carry.

## 5. The change

`solid_node/motion/joints.py` only. No other framework module is edited.

- [x] 5.1 `Joint.place` uses `self.axes(node)` and
  `self.carried_points(node, anchor)` directly, with no transformation,
  and splats them into `placement` in the same order. Update the
  docstring: the arguments are already in the node's own frame.
- [x] 5.2 Delete `Joint._carry`, `_OwnPlacedOrigin`, `_OWN_PLACED_ORIGIN`
  and the `numpy` import inside `_carry`. Confirm by grep that
  `solid_node/motion/joints.py` no longer mentions `numpy`, and record it
  in `evidence.md`: the joints module's import cost is now
  `solid_node.motion.ports` and `math` alone (ADR-087).
- [x] 5.3 Rename the two hooks' meaning in their docstrings without
  changing their signatures: `axes(node)` is "the DIRECTIONS this joint's
  placement takes, in the node's own frame"; `carried_points(node, anchor)`
  is "the POINTS", anchor first. They are the seam ADR-094 built and they
  survive intact.
- [x] 5.4 `Joint.resolve` normalizes the axis and SNAPS each component
  through `_snapped` before returning it. Anchors are not snapped.
- [x] 5.5 `Orbit.__init__` takes `carries=(0, 0, 0)`; `Orbit.resolve`
  resolves it through `_vector` like any other vector, with no sentinel
  branch. Its docstring states the own-frame reading and that the default
  is the body's own origin, directly.
- [x] 5.6 `Free.axes` returns `((1, 0, 0), (0, 1, 0), (0, 0, 1))` — the
  same tuple it returns today, now as a statement about the body's own
  frame rather than the parent's; update the docstring.
- [x] 5.7 The module docstring of `joints.py` is rewritten around the new
  rule. The paragraph beginning "`axis` and `at` are read in the PARENT's
  frame" is where the change is most visible to a reader; it must now say
  the frame follows the declarer, and name cycle 3 as the other half.

## 6. Green, and the guard rails

- [x] 6.1 Every case of tasks 1–4 green.
- [x] 6.2 FULL SUITE: `.venv/bin/python -m pytest -x -q` from the
  worktree, exact counts in `evidence.md`, matched against 0.3. Any new
  failure stops the cycle.
- [x] 6.3 **No test of ADR-093, ADR-094 or ADR-095 was edited except the
  fixtures named in tasks 2.4, 3.x and 4.x.** List in `evidence.md` every
  test file and test name touched, with the reason. `CompositionOrderTest`
  in particular must pass unedited: composition is not in this cycle's
  scope, and an edit there is evidence the change reached further than the
  design says.
- [x] 6.4 Grep the framework for any remaining consumer of the deleted
  names; there should be none outside `joints.py` (verified at proposal
  time).

## 7. The evidence: 23 projects, before and after

The implementer MUST NOT edit any project repository. The overlay is a
throwaway copy, made read-only from the project:

    SCRATCH=<a scratch dir outside every repository>
    git -C <project> archive HEAD | tar -x -C $SCRATCH/<project>
    # symlink any ignored asset directory the project needs, e.g. vendor
    # STEP caches, so the copy resolves them without being written to:
    ln -s <project>/<asset dir> $SCRATCH/<project>/<asset dir>

Then apply that project's joint rewrites, from `evidence/survey.md`, to
the copy's `.py` files ONLY, and capture:

    cd $SCRATCH/<project>
    PYTHONPATH=.:<worktree> <venv>/bin/python \
      <shop>/docs/motion-general-refactor/capture_poses.py \
      capture <module:Class> $SCRATCH/<project>-<model>-after.json
    ... compare <before.json> <after.json>

One project at a time; delete each copy after its comparison. Confirm
before every capture that `git -C <project> status --porcelain` is
unchanged from what 0.4 recorded.

- [x] 7.1 Rewrite and compare the **20 projects the survey says need no
  pose change beyond a mechanical rewrite**: 3DPrintedClocks (every clock
  but 48), Thor, YouCanBuildDog, Prusa3-vanilla, OpenTorque-Actuator,
  openarm, pascaline, BCN3D-Moveo, hangprinter, openvmp,
  open_manipulator, poseidon, YouCanBuildBiPed, HACKberry,
  open_robot_actuator_hardware, snappy-reprap, Metamaquina2,
  hexapod_spiderbot_model, AlbertPro, science-jubilee. **Required result:
  maximum deviation 0** on every model of every one. A non-zero
  deviation is a defect in the change or in the survey row and stops the
  cycle; it is never explained away.
- [x] 7.2 Rewrite and compare the **three projects whose pose-changing
  `ZERO-BUT-PLACED` rows are `PARENT-KNOWLEDGE-IN-SUBSTANCE`**:
  Inmoov-sim (7 sites), Internal-Cycloidal-Actuator (2),
  openflexure-microscope (1). **Required result: maximum deviation 0.**
  These are the rows that prove the rule is not silently lossy; if any of
  them cannot be brought to 0, the design is wrong and the cycle stops.

  **Do NOT type the anchor as a literal in the overlay.** The value that
  makes these ten poses come out right is the parent's knowledge frozen
  into the child (design §4, §8), and for the Internal Cycloidal Actuator
  it is a literal that project's ratified spec forbids anywhere in the
  project — an overlay carrying it would read as a proposal to commit it.
  DERIVE it instead, in the overlay, from the placement the framework no
  longer inverts: compose the node's non-motion operations by
  premultiplication through each operation's `matrix()`, invert, and take
  the translation column — the point the OLD rule's defaulted anchor
  named, the parent's origin, expressed in this body's rest frame:

      def anchor_from_placement(node):
          import numpy as np
          matrix = np.eye(4)
          for operation in node.operations:
              if getattr(operation, '_motion', False):
                  continue
              matrix = operation.matrix() @ matrix
          return tuple(np.linalg.inv(matrix)[:3, 3])

  Record in `evidence.md` that this helper is `_carry`'s own arithmetic,
  living in the overlay for one run: it exists to MEASURE that nothing
  moved, it is not the migration, and it dies with the overlay. The
  migration for all ten is cycle 3's site keyword; until then the three
  projects keep exactly what they have today.

  One consequence to record rather than route around: a joint argument
  callable resolves at REALIZATION, before the body is placed, so this
  helper cannot be an `at=` callable as it stands. Bind the joint in the
  overlay from the project's own `simulate()`, where the body is placed,
  after computing the anchor there; or, failing that, compute the ten
  anchors OFFLINE and record them in `evidence.md` as derived numbers
  beside the placement each came from. Never as a project edit, and never
  transcribed into the project.
- [x] 7.3 **3DPrintedClocks wall clock 48 is the named exception.** Its
  `TurningArbor` at index 5 and its `TurningPalletPin` are expected to
  MOVE, because that clock is written for the new reading and says so in
  a source comment (design §9). Record the deviation, in millimetres, per
  leaf; run that clock's own suite against the overlay and record whether
  the anchor wheel and its pallet pins now agree; and carry the result to
  the pilot as an OPEN QUESTION. Do not accept it as a difference and do
  not adjust the clock to hide it.
- [x] 7.4 Run
  `Robots-Bipedal/YouCanBuildBiPed/simulation/test_assembly.py::test_motion_uses_current_revolute_joints_at_measured_pivots`
  against the overlay: it is the only test in the catalogue that reads
  `.axis` and `.at` off realized joints. It must stay green unedited.
- [x] 7.5 Record in `evidence.md`, per project: the model list, the pose
  and leaf counts, the maximum deviation, and the exact diff of the joint
  rewrite (which `at`s were deleted, which added, which axes rewritten,
  which became callables). That diff is the migration guide the projects'
  own stage-B cycles will follow.

## 8. Documentation and the record

- [x] 8.1 `docs/driving.rst`, the joints section: rewrite around the new
  rule. The sentence at :208-211 — "`at` defaults to that frame's origin,
  which is the case of a wheel turning on its own bearing" — becomes true
  rather than aspirational; the worked elbow example is restated in the
  forearm's own frame; the paragraph about inverting the rest placement
  goes; a paragraph is added about what happens to a joint on a body its
  parent rotates, and about which of the two frames cycle 3 will offer.
- [x] 8.2 `docs/changelog.rst`, Unreleased: the entry, addressed to the
  catalogue (joints are unreleased; there is no 0.6.0 user with a joint).
  It must state the win, the one silent case, the twelve sites the
  catalogue had, and the five axes that now need a callable.
- [x] 8.3 The ADR: a new NODE ADR, "A joint is stated in the frame of
  whoever declares it". It supersedes ADR-088's frame decision in part
  (quote the rejected option 4 and answer it with the survey's numbers),
  revises ADR-094 (the `carries` sentinel becomes redundant; the
  "`Revolute`'s own-placed-origin `at` stays OPEN" consequence is now
  closed), and closes ADR-095's stated open question. Consequences must
  include: the five axes and their two bridges; the twelve
  `ZERO-BUT-PLACED` sites, of which ten are
  `PARENT-KNOWLEDGE-IN-SUBSTANCE` and belong to cycle 3 — say that the
  strict count of anchors needing the parent's frame is 0 and the count
  in substance is 10, and why the distinction matters, the Internal
  Cycloidal Actuator's ratified spec forbidding the very literal the
  strict reading would have it write; the precise frame (the body's REST
  frame, and a `Free`'s translation along it rather than along the
  rotated body); wall clock 48; the deleted refusal; and the fact that
  the inversion returns in cycle 3.
- [x] 8.4 Update `docs/adrs/README.md` (new row, and ADR-088's status
  line) and `docs/architecture.md` where it describes the joint's frame.
- [x] 8.5 `openspec validate --strict joint-frame-follows-declarer`;
  `openspec archive` when the pilot says so. **Note for the archiver:**
  this delta DROPS the scenario "An unresolvable rest placement is
  refused" from a MODIFIED requirement and adds "A rest placement the
  framework cannot evaluate no longer prevents a joint" in its place. If
  archive refuses the drop, state the old scenario under `## REMOVED
  Requirements` rather than renaming it.
- [x] 8.6 File in `workflow/warts.md`: close the own-placed-origin
  finding with this cycle's name and the survey's numbers; correct the
  Prusa i3 entry, which says no recorded candidate fix reaches the Z
  screws (it does); and file two NEW findings — the five axes that lose
  their literal (a declaration-site joint on a `.repeat()`, which cycle 3
  as planned does not cover), and the 3DPrintedClocks clock-48
  disagreement with its four siblings.
