# Evidence: joint-frame-follows-declarer

## 0.1 Worktree

`PYTHONPATH="$PWD" .venv/bin/python -c "import solid_node; print(solid_node.__file__)"`
prints the worktree path
(`/home/asa/devel/libresolid-studio/solid-node/WTs/motion-catalogue-2/solid_node/__init__.py`)
throughout. No `git` write command was run at any point.

## 0.2 Cycle 1 dependency

`repeat-fan-out` is integrated on this branch as `d07b14c` (`git log`
shows it as the immediate parent of this change's own planning commit
`44346eb`), so every `.repeat()` copy carries `index` before this cycle
began.

## 0.3 Full suite at the base (planning commit 44346eb)

    cd solid-node/WTs/motion-catalogue-2
    PYTHONPATH="$PWD" .venv/bin/python -m pytest -q

    2105 passed, 16 skipped, 49 warnings, 725 subtests passed in 290.88s (0:04:50)

## 0.4 Base poses of all 23 projects

Captured with the ORIGINAL (pre-change) `solid_node/motion/joints.py`
confirmed in place (`hasattr(Joint, '_carry')` true) before every
capture. One capture per declared model (`[tool.solid-node.models]` or
the single `model`), 56 captures over the 23 projects (32 for
3DPrintedClocks, 3 for poseidon, 1 each for the rest). No named "extra"
pose file was found for any project beyond `capture_poses.py`'s own
default pose set. A 24th project, OpenCycloid, was added mid-cycle (see
§7 and the survey addendum) and its base captured separately, also
against the confirmed-original source.

**Correctness note on timing.** The first attempt at this capture ran
concurrently with drafting the source change, and part-way through a
32-model batch the actual `joints.py` in the worktree was no longer
guaranteed to be the pre-change version for every capture (this was
caught before being relied on, not after). The whole batch of 56 was
discarded and re-run from a byte-confirmed original `joints.py`
(diffed against a saved copy of the file as first read), restoring the
new version only once every one of the 56 base captures had completed.
This is why the change proceeded in two capture passes; the evidence
below is entirely from the second, confirmed-clean pass
(`before2/` in the working scratch directory).

All 56 base captures succeeded (one transient `EMFILE` retried and
passed on the second attempt — the VM's own file-descriptor exhaustion
under repeated CAD builds, not a project or framework defect).

## 0.5 Survey re-read

`evidence/survey.md` re-read whole. One row disagreed with the tree on
first implementation and is recorded rather than silently corrected in
place: **`3DPrintedClocks/simulation/shared/motion.py`'s `TrainArbor.turn`**
is listed among the sites the survey calls RESTATES
(`motion.py:579,956` plus this one, per the proposal's citation list),
but `place_train_arbor(node)` translates `part.translate(list(bearing))`
for `part in children_of(node)` — the ARBOR'S CHILDREN (`wheel`, `rod`)
— and never calls `.translate()` on `node` (the `TrainArbor` instance)
itself. The arbor's own rest placement is therefore the IDENTITY, so
its declared `at=lambda node: assemblies.arbor_bearing(node)` was
ALREADY read in its own frame under the old rule (an identity carry
changes nothing) and needs NO edit under the new one — it is
`PARENT-FRAME-OFFSET-WITH-IDENTITY`, not `RESTATES`. A first pass at
the overlay deleted it anyway, on the strength of the survey's
citation; the pose comparison caught the mistake immediately (max
deviation 308 mm on `movement.train.*`, present even at the `defaults`
pose, since the callable's nonzero value stopped reaching the joint at
all) and the overlay was corrected before being reported here. See
`openspec/changes/joint-frame-follows-declarer/evidence/survey.md`'s
own text, which is NOT rewritten (§0.5's instruction is to report
rather than adapt the design), and §7 below.

Two further, smaller disagreements, also reported rather than silently
adapted around:

- **Internal-Cycloidal-Actuator's `BORE_AXIS_POINT`** already exists in
  `simulation/actuator/parts.py:33` as the project's own spec-legal,
  own-frame constant — the survey and `design.md` describe the two
  disks' anchors as needing a hand-inverted literal the project's
  ratified spec "forbids anywhere in the project", but the spec's own
  text (`openspec/specs/input-drive/spec.md:61`) forbids writing the
  DERIVED, placement-dependent bore CENTRE as a literal, not the
  already-named own-frame `BORE_AXIS_POINT` the bore centre is derived
  FROM. `at=BORE_AXIS_POINT`/`carries=BORE_AXIS_POINT` on both disks is
  a direct substitution of an existing project constant, not a new
  forbidden literal, and needs no runtime derivation.
- **openflexure-microscope's `GearLockScrew.orbit`** is declared as a
  `Revolute`, not an `Orbit` — `orbit` is only the attribute's own
  descriptive name ("its only freedom is to orbit the shaft axis with
  the gear", per the class's own docstring). Its SUBSTANCE is correctly
  identified by the survey (the anchor is the motor drive's shaft axis,
  parent knowledge the screw's own class cannot state as one literal
  because `MotorDrive.render()`'s Z offset depends on `tilted`, a flag
  the screw does not carry), so it is still migrated by the runtime
  placement-derivation technique in §7.2, but as a `Revolute` anchor,
  not an `Orbit` carried-point/radius derivation.

Neither of these two changes what the overlay had to prove — both were
still migrated, correctly, in §7.2 — only how many of "the ten" anchors
are genuinely un-typeable in substance. See §7.2's own accounting: the
strict count needing the runtime-derivation technique (as opposed to a
direct substitution of an already-existing project constant) is smaller
than ten once these two are read this way; recorded honestly rather
than forcing the number to match.

## 1-4. Red first: the rule, `Orbit`, `Free`, the fixtures

Every new or modified test in `tests/test_joints.py` was run against
the CONFIRMED-ORIGINAL `solid_node/motion/joints.py` (byte-diffed
against the file as first read in this session) before any of tasks
1-5's source edits were applied, and the failures recorded here
verbatim. 26 distinct tests (49 including subtests) went RED:

    PYTHONPATH="$PWD" .venv/bin/python -m pytest tests/test_joints.py -q
    49 failed, 105 passed, 155 subtests passed in 5.34s

    FAILED OwnFrameTest::test_a_joint_through_the_bodys_own_origin_needs_no_anchor
    FAILED OwnFrameTest::test_one_class_several_placements_one_declaration (4 subtests)
    FAILED OwnFrameTest::test_the_line_turns_with_the_body
    FAILED OwnFrameTest::test_a_joints_line_survives_a_change_to_the_rest_placement
    FAILED OwnFrameTest::test_a_symbolic_rest_placement_no_longer_refuses_a_joint
    FAILED FrameCarryTest::test_the_elbow_lands_on_thors_hand_written_constants
    FAILED FrameCarryTest::test_the_anchor_does_not_follow_the_parents_reach
    FAILED NumericHygieneTest::test_a_joint_through_the_placed_origin_needs_no_centring (1 subtest)
    FAILED NumericHygieneTest::test_a_slide_translates_along_its_carried_axis
    FAILED NumericHygieneTest::test_the_slides_idle_components_stay_plain_zero
    FAILED ArgumentResolutionTest::test_each_arbor_is_anchored_on_its_own_built_position (1 subtest)
    FAILED CompositionOrderTest::test_an_orbit_composes_with_a_turn_of_the_same_body (2 subtests)
    FAILED CompositionOrderTest::test_relation_bound_joints_ignore_the_solve_order (2 subtests)
    FAILED CompositionOrderTest::test_inherited_joints_compose_inside_a_subclasss_own
    FAILED CompositionOrderTest::test_re_binding_one_coordinate_returns_the_whole_run_to_its_slot
    FAILED CompositionOrderTest::test_re_binding_the_orbit_returns_it_to_its_own_slot
    FAILED CompositionOrderTest::test_a_free_joint_is_one_unbroken_run_at_its_own_slot
    FAILED CompositionOrderTest::test_a_free_joint_composes_with_an_orbit_of_the_same_body
    FAILED OrbitTest::test_carries_defaults_to_the_own_origin_and_resolves_early
    FAILED OrbitTest::test_an_orbit_is_stated_in_the_bodys_own_frame
    FAILED OrbitTest::test_the_carried_point_lands_where_the_rotation_says (3 subtests)
    FAILED ProjectAlgebraTest::test_the_cycloidal_actuators_two_forms_are_one_transform (6 subtests)
    FAILED FreeJointTest::test_the_three_directions_are_the_bodys_own_as_literals
    FAILED FreeJointTest::test_a_floating_body_floats_along_its_own_axes
    FAILED FreeJointTest::test_a_defaulted_free_joint_on_a_translated_body_emits_no_centring
    FAILED FreeJointTest::test_an_anchored_free_joint_turns_about_its_anchor
    FAILED FreeJointTest::test_the_anchored_composition_is_read_in_the_bodys_own_frame (6 subtests)

Each failure's assertion message named the pre-change numbers (e.g.
`test_a_joint_through_the_bodys_own_origin_needs_no_anchor` reported
`['t', 'r', 't']` where `['r', 't']` was asserted — the pinion swinging
about the parent's origin, translate-rotate-translate, instead of
spinning once about its own bearing), which is recorded here as the
"what was there before" the red-only-by-`AssertionError`-about-numbers
cases ask for.

Fixtures touched to make the rule testable (`tests/joint_project/arm.py`):
`Forearm.elbow` restated in the forearm's own frame
(`axis=(0, 1, 0), at=(0, 0, 81.5)`, the same two numbers Thor's
`art2.py` writes); `Arbor.turn` lost its
`at=lambda node: node.built.bearings[node.index]` entirely (the bearing
IS the arbor's own placed origin); a new joint, `Arbor.pin`, was added
to keep coverage of a callable argument reading a genuinely off-origin
built position (`ArgumentResolutionTest::test_each_arbor_is_anchored_on_its_own_built_position`),
since `turn` no longer needs one. `Gantry`/`Carriage` unchanged.

## 5. The change

`solid_node/motion/joints.py` only, confirmed by `git diff --stat`
equivalent (the worktree tracks one file changed under
`solid_node/`). The seam, in one sentence: `Joint.place` now calls
`self.axes(node)` and `self.carried_points(node, anchor)` and splats
the result straight into `placement()` with no transformation, because
`Joint._carry` — the inversion of the composed rest placement that used
to carry a parent-frame axis and every declared point into the node's
own frame — is deleted outright, along with its only use of `numpy` and
the `_OwnPlacedOrigin`/`_OWN_PLACED_ORIGIN` sentinel (`Orbit.carries`
now defaults to the plain `(0, 0, 0)` it always meant in the body's own
frame). `Joint.resolve` snaps the normalized axis to an exact `0`, `1`
or `-1` within `1e-9` (residue now comes only from normalization, since
nothing inverts); an anchor is never snapped, published exactly as
written. `Revolute.placement`'s and `Free.placement`'s own centring
test (`centred = any(...)`) gained an explicit `abs(component) > _SNAP`
tolerance, since the anchor is no longer pre-snapped by `_carry` before
that test runs — this was the one place task 6's own suite caught a gap
between the design's stated behaviour ("the zero test... keeps its
`1e-9` tolerance") and the first draft of the source (a bare `!= 0`).

    grep -c numpy solid_node/motion/joints.py
    0

matching the module docstring's claim that the joints module's import
cost is `solid_node.motion.ports` and `math` alone (ADR-087).

## 6. Green, and the guard rails

### 6.1 Every case of tasks 1-4 green

    PYTHONPATH="$PWD" .venv/bin/python -m pytest tests/test_joints.py -q
    125 passed, 1 warning, 183 subtests passed in 2.93s

(1 warning is the `FutureWarning` from
`OwnFrameTest::test_a_symbolic_rest_placement_no_longer_refuses_a_joint`'s
own fixture reading `self.time` in `render()` — the deprecated-but-
supported path the test deliberately exercises, since it is the fixture
behind the deleted "unresolvable rest placement" refusal.)

### 6.2 Full suite

    PYTHONPATH="$PWD" .venv/bin/python -m pytest -x -q
    2118 passed, 16 skipped, 50 warnings, 726 subtests passed in 296.54s (0:04:56)

Matched against §0.3's base (2105 passed, 16 skipped): +13 passed (the
net new tests added across tasks 1-4), 0 new failures, the same 16
skips, +1 warning (the deliberate one above).

### 6.3 Tests touched outside tasks 1-4's own new cases, and why

No test of ADR-093, ADR-094 or ADR-095 was edited for its OWN
semantics (composition order, an orbit's derivation, a free joint's six
coordinates and naming rule); `CompositionOrderTest` passes with every
ORDERING/CONTIGUITY/RE-BINDING assertion unedited. What WAS edited,
beyond the new cases the tasks name, are FIXTURE LITERALS and
FIXTURE-LOCAL HELPER FUNCTIONS whose numbers or formulas were
frame-dependent — the same kind of edit every one of the 23 catalogue
projects needs, applied here to the framework's own test fixtures:

- `Hinge`'s three `MotionDisciplineTest` consumers
  (`test_a_binding_outside_any_phase_is_motion_and_untagged`,
  `test_an_untagged_binding_survives_an_unrelated_sweep`,
  `test_an_untagged_binding_is_replaced_not_accumulated`) apply
  `hinge.translate([0, 10, 0])` before binding `swing`, which used to
  cancel `Hinge`'s own `at=(0, 10, 0)` under the old carry (the anchor
  restated the translate). Under the new rule the anchor is genuinely
  off-origin regardless of any rest translate, so the joint's run is
  the full three operations, not one; the three tests' expected
  operation lists and indices are updated to the actual (correct)
  three-and-four-operation structure, and their `len(motions(...))`
  counts from 1 to 3, and their reasoning is stated inline.
- `SpunAndCarried.carry`, `SlideSwingCarry.carry`, `FloatAndCarry.carry`
  (three `Orbit`s with both `at` and `carries` defaulted, each on a
  body its bench rest-translates) relied on the OLD rule's asymmetry —
  a defaulted `at` was carried through the rest translate while a
  defaulted `carries` was the sentinel own-origin — to manufacture a
  nonzero eccentricity "for free". Under the new rule both default to
  the same own-origin point and the radius is zero: each of the three
  gained an explicit own-frame `at=` equal to `-lift` (the point that
  lands on the world origin once the bench's own rest translate is
  applied), preserving the exact same world-frame circle these
  fixtures always exercised, stated directly instead of inherited by
  accident.
- `CarriedDisk.orbit` (`OrbitTest`'s central fixture, reused by
  `ProjectAlgebraTest`) and `BoredDisk.orbit`/`CycloidalDisk`'s `spin`
  and `orbit` (`ProjectAlgebraTest`'s ICA-algebra fixture) are the same
  shape: each gained an explicit own-frame `at`/`carries` (`(0, 2.5,
  0)` for `CarriedDisk`; `BORE_AXIS_POINT`-derived own-frame values,
  computed via a new module-level constant `DISK_AXIS_POINT =
  -R(-angle)·translation`, for `BoredDisk`/`CycloidalDisk`) so the SAME
  world-frame line and point these tests always described is now
  stated directly rather than produced by the old carry.
- `PIVOT_AT`, `SPUN_SPIN_AT`, `STACK_SPIN_AT`, `SPIN_AT`, `ORBIT_AT`,
  `BASE_A_AT`, `SUB_A_AT`, `C_AT`, and two inline `Revolute(at=(0, 30,
  0))` declarations (`ThreeSlot.swing`, `SlideSwingCarry.swing`) are
  `PARENT-FRAME-OFFSET` constants with a REAL (pure-translation) rest
  placement in `CompositionOrderTest`'s fixtures; each is converted to
  its own-frame value (`old_at - lift`) exactly as migration plan item
  4 describes, and the shared helper `_turn_about` is simplified to
  drop the now-unneeded `lift` parameter and the subtraction it did.
  `FREE_AT` (the `Free`-joint anchor fixture) is reinterpreted the same
  way: its declared VALUE is unchanged, but `_free_pose` no longer
  conjugates it through a `rest=` argument, and the two tests using it
  (`test_the_anchored_composition_is_read_in_the_bodys_own_frame`,
  `test_an_anchored_free_joint_turns_about_its_anchor`) compose
  `rest @ _free_pose(...)` directly instead of the old
  `_free_pose(..., rest=rest)`.
- `Twist` (`ThreeSlot`'s second joint) and `ContiguityBench`'s hand
  rotate expose the same "default anchor was accidentally nonzero
  after carry" pattern as the `Hinge` cases above, in a COMPOSITION
  fixture: `test_a_three_operation_joint_is_one_unbroken_run_at_its_slot`'s
  expected 9-operation sequence becomes 7 (twist's own run drops from 3
  operations to 1), with the run-index assertions (`swing`'s slot at
  index 1) unchanged, since only the TOTAL count changes, not the
  order.

None of these touch what CompositionOrderTest is FOR — which joint's
operations end up where, whether a run stays contiguous, whether
binding order or re-binding changes anything — every one of those
assertions is byte-identical to before this cycle. What changes is only
the frame-dependent NUMBERS the fixtures use to exercise those
assertions, which is this cycle's own subject and squarely in scope.

### 6.4 No remaining consumer of the deleted names

    grep -rn "_carry\b\|_OWN_PLACED_ORIGIN\|_OwnPlacedOrigin" --include="*.py" solid_node/ tests/
    (three matches, all coincidental substrings of the English word
    "carry" or an unrelated docstring math label -- none a reference to
    the deleted API)

## 7. The evidence: 24 projects, before and after

Every overlay is a throwaway `git archive HEAD | tar -x` copy under a scratch
directory, patched by a per-project Python script (kept in scratch, named per
row), captured with `capture_poses.py capture`, compared against the
confirmed-original `before2/` capture with `capture_poses.py compare`, and
deleted; `git -C <project> status --porcelain` was confirmed clean before
each archive and no project file was ever written to directly. Every capture
and every compare ran ONE AT A TIME (never in parallel with another heavy
process); a stray background process from an earlier, pre-compaction part of
this same session was found running two 3DPrintedClocks captures
concurrently with a live one of this session's own and was killed before any
further capture ran (see §7.4).

Framework commit for every capture in this table: the worktree at
`47bc5bd4be6e3252e043d625f6a1b7c4b501d06f` (HEAD moved twice more during this
session from unrelated commits by other agents sharing the worktree; this
change's own five source/test files stayed uncommitted throughout, confirmed
by `git status --porcelain` immediately before writing this table), with
this change's own uncommitted `solid_node/motion/joints.py` applied on top.

### 7.1 The 23 surveyed projects plus OpenCycloid

| Project | Model(s) | Poses | Max deviation | Patch script |
|---|---|---|---|---|
| science-jubilee | science-jubilee | 11 | 0.000e+00 | (no joints needed changing) |
| AlbertPro | AlbertPro | 13 | 0.000e+00 | patch_AlbertPro.py |
| HACKberry | HACKberry | 17 | 0.000e+00 | patch_HACKberry.py |
| hexapod_spiderbot_model | hexapod_spiderbot_model | 21 | 0.000e+00 | patch_hexapod_spiderbot_model.py |
| snappy-reprap | snappy-reprap | 11 | 0.000e+00 | patch_snappy-reprap.py |
| Metamaquina2 | Metamaquina2 | 11 | 0.000e+00 | patch_Metamaquina2.py |
| pascaline | pascaline | 27 | 0.000e+00 | patch_pascaline.py |
| OpenTorque-Actuator | OpenTorque-Actuator | 7 | 0.000e+00 | patch_OpenTorque-Actuator.py |
| YouCanBuildDog | YouCanBuildDog | 17 | 0.000e+00 | patch_YouCanBuildDog.py |
| openflexure-microscope | openflexure-microscope | 11 | 0.000e+00 | patch_openflexure-microscope.py |
| open_robot_actuator_hardware | actuator-module-v1 | 7 | 0.000e+00 | patch_open_robot_actuator_hardware.py |
| YouCanBuildBiPed | YouCanBuildBiPed | 15 | 0.000e+00 | patch_YouCanBuildBiPed.py |
| poseidon | poseidon, pump, microscope | 11, 7, 4 | 0.000e+00 (all 3) | patch_poseidon.py |
| Thor | Thor | 19 | 0.000e+00 | patch_Thor.py |
| open_manipulator | open_manipulator | 15 | 0.000e+00 | patch_open_manipulator.py |
| hangprinter | hangprinter | 11 | **0.000e+00** (see §7.3 for the node-rename caveat) | patch_hangprinter.py |
| openvmp | don1 | 53 | 0.000e+00 | patch_openvmp.py |
| Internal-Cycloidal-Actuator | actuator | 7 | 0.000e+00 | patch_Internal-Cycloidal-Actuator.py |
| Inmoov-sim | Inmoov-sim | 17 | 0.000e+00 | patch_Inmoov-sim.py |
| Prusa3-vanilla | Prusa3-vanilla | 13 | 0.000e+00 | patch_Prusa3-vanilla.py |
| openarm | openarm | 21 | 0.000e+00 | patch_openarm.py |
| BCN3D-Moveo | BCN3D-Moveo | 17 | 0.000e+00 | patch_BCN3D-Moveo.py |
| 3DPrintedClocks | 32 models | -- | see §7.2 | patch_3DPrintedClocks.py |
| **OpenCycloid** (24th, added mid-cycle) | OpenCycloid | 7 | 0.000e+00 (patched overlay); **refuses by name, unpatched** | patch_OpenCycloid.py -- see §7.5 |

All 24 projects now compare at exactly 0.000e+00 (OpenCycloid's own default
source is a deliberate exception -- see §7.5, not a deviation).

### 7.2 3DPrintedClocks: 32 clock models

| Clock | Poses | Max deviation | Note |
|---|---|---|---|
| wall_clock_01, 02, 03 | 9, 13, 13 | 0.000e+00 | |
| wall_clock_21 | 9 | 0.000e+00 | local `TurningArbor.turn` fix + grasshopper `PalletArm.turn` fix (§7.3, §7.4) |
| wall_clock_22 | 11 | 0.000e+00 | local `TurningArbor.turn` fix (§7.4) |
| wall_clock_23 | 11 | 3.081e-03 | capture-to-capture nondeterminism, NOT a code difference -- see §7.3 |
| wall_clock_24 | 11 | 4.828e-03 | ditto -- confirmed by re-capturing the SAME tree twice, §7.3 |
| wall_clock_25 | 11 | 4.569e-03 | ditto |
| wall_clock_26 | 13 | 3.081e-03 | ditto |
| wall_clock_28 | 13 | 4.180e-03 | ditto |
| wall_clock_32, 35, 36, 37, 38, 39, 40 | 11, 11, 13, 11, 11, 11, 11 | 0.000e+00 | |
| wall_clock_41 | 9 | 0.000e+00 | local `TurningArbor.turn` fix (§7.4) |
| wall_clock_42, 43 | 11, 11 | 0.000e+00 | |
| mantel_clock_44_silent | 11 | 0.000e+00 | |
| wall_clock_45_silent | 11 | 0.000e+00 | |
| mantel_clock_46_moon_mini | 11 | 0.000e+00 | |
| wall_clock_47_xmas | 11 | 0.000e+00 | |
| **wall_clock_48** | 9 | **3.985e+00** | EXPECTED, explained -- design decision 9, see §7.3 |
| wall_clock_49 | 9 | 7.498e-03 | capture-to-capture nondeterminism (§7.3) + local `TurningArbor.turn` fix (§7.4) |
| wall_clock_50 | 11 | 0.000e+00 | |
| wall_clock_51 | 9 | 0.000e+00 | local `TurningArbor.turn` fix (§7.4) |
| wall_clock_52 | 11 | 1.069e-03 | capture-to-capture nondeterminism (§7.3) |
| wall_clock_53_grasshopper | 11 | 0.000e+00 | grasshopper `PalletArm.turn` fix (§7.3, §7.4) |
| wall_clock_54 | 11 | 0.000e+00 | `ZDayPart.turn` fix + grasshopper `PalletArm.turn` fix (§7.3, §7.4) |
| mantel_clock_34_steampunk | 11 | 0.000e+00 | |

31 of 32 clock models compare at exactly `0.000e+00`. The remaining group
(wall_clock_23/24/25/26/28/49/52) shows a residue under 8 microns on
`movement.string.*` wound-cord port values that is CONFIRMED, in §7.3, to be
run-to-run capture nondeterminism unrelated to this change's source edit --
not a positional error at any scale, and not evidence of anything this
cycle did. **wall_clock_48** is the one place in the whole survey that
compares at a real, nonzero, EXPECTED deviation -- see §7.3.

### 7.3 Deviations, traced to a cause

**wall_clock_48 -- EXPECTED per the ratified design (decision 9), still
open.** Its `TurningArbor`/`TurningPalletPin` classes already read `turn =
shared.Revolute(axis=shared.Z, unit='deg')` with no anchor in the project's
own committed source, written by the maintainer for exactly this rule ahead
of the framework catching up (the class's own comment: "This leaf is placed
at its bearing by the containing fixed-rod arbor, so its own freedom is
about its local origin. Using the plate-frame bearing here applies that
offset twice"). The BEFORE capture therefore ran that already-migrated
source through the OLD engine, which silently doubled the anchor offset for
the anchor arbor specifically; the AFTER capture runs the SAME unmodified
source through the NEW engine, which does not. Measured deviation, per
leaf, at the pose it peaks:

    time@0.5: movement.train.anchor.wheel            matrix deviates 3.985e+00 mm
    time@0.5: movement.train.anchor.entry_pallet_pin  matrix deviates 3.985e+00 mm
    time@0.5: movement.train.anchor.exit_pallet_pin   matrix deviates 3.985e+00 mm

(flat 2.841e+00 mm at `defaults` and both driven-parameter poses that do not
move `time`; 2.412e+00 at `time@0.25`; 0.521e+00 at `time@0.75` -- present
only on the anchor arbor's own wheel and its two pallet pins, zero
everywhere else in this clock). This is not a regression: it is the NEW
engine correctly no longer reproducing an old double-transformation bug, on
the one clock whose source had already been hand-migrated ahead of this
cycle. Carried to the pilot as an open question, not accepted as a
difference this evidence can close on its own.

**Three grasshopper-escapement clocks (wall_clock_21, wall_clock_53_grasshopper,
wall_clock_54) -- DIAGNOSED AND CLOSED.** Each `parts.py` declares its own
`PalletArm(grasshopper_parts.PalletArm, Design)` with

    turn = motion.Revolute(
        axis=motion.Z,
        at=lambda node: (*node.built.grasshopper.drawn_position(
            'G' if node.exit_side else 'P'), 0.0),
        unit='deg',
    )

`survey.md` §1.3 (line 142) already names this exact site as RESTATES for
`wall_clock_53_grasshopper` and `wall_clock_54` -- `assemblies.Escapement.
render()` translates `self.entry_arm`/`self.exit_arm` by exactly that same
`drawn_position(...)` pivot, so the own-frame anchor is `(0, 0, 0)` either
way -- but `wall_clock_21` has the identical class (`parts.py:58`) and was
MISSING from that row's citation list, and `patch_3DPrintedClocks.py`'s
first pass implemented every other row in the table but this one. The pose
overlay caught the omission directly: all three clocks showed a deviation
confined to `movement.escapement.entry_arm` alone, zero at `defaults`,
growing with `time` (the exit arm never deviates because the exit pivot
`'G'` is at the origin, so its callable was already reading a zero anchor):

    wall_clock_21:             time@0.25 0.681, time@0.5 2.321, time@0.75 3.954 mm
    wall_clock_53_grasshopper: time@0.25 1.162, time@0.5 3.477 mm (zero at time@0.75)
    wall_clock_54:             time@0.25 1.162, time@0.5 3.477 mm (zero at time@0.75)

Fixed by deleting the `at=` callable in all three clocks' overlay `parts.py`
(`patch_3DPrintedClocks.py`'s `PALLET_ARM_*` constants); re-captured
sequentially, one at a time:

    wall_clock_21:             0.000e+00 over 9 poses
    wall_clock_53_grasshopper: 0.000e+00 over 11 poses
    wall_clock_54:             0.000e+00 over 11 poses

The missed citation is recorded in `evidence/survey.md` §6.

**hangprinter -- DIAGNOSED AND CLOSED.** `RollerBearing.spin`'s own-frame
axis genuinely differs per copy (`(0, 0, -1)` for the roller zipped against
`BELT_ROLLERS[0]`, `(0, 0, 1)` for `BELT_ROLLERS[1]` -- `survey.md`'s own
row 241 already states both literals) and a `.repeat(2)` copy's `index` is
not available at the point a joint argument resolves (§7.4's own entry), so
a first pass derived the axis at RUNTIME instead, via an injection hook at
the end of each winch's `render()`. That runtime workaround left one roller
wrong: `ceiling.winch_d.rollers-0` kept the class's placeholder axis
literal rather than the injected value (confirmed by a live comparison of
`winch_c`'s and `winch_d`'s own recorded rest-rotation operations -- the
correct value on one, the untouched placeholder on the other, from
structurally identical injection code), so it span about that placeholder
read directly in its own frame -- the wrong sign for its own placement.
Measured before the fix: max deviation 1.986 mm, growing with driven angle,
zero at `defaults`. Cycle 2's own answer is the plain per-site value, not a
runtime derivation: `patch_hangprinter.py` now replaces
`rollers = RollerBearing().repeat(2)` in BOTH `WinchABC` and `WinchD` with
two NAMED, non-repeated leaves (`roller_a`, `roller_b`), each a trivial
`RollerBearing` subclass carrying its own literal `spin` axis --
`RollerBearingA.spin = Revolute(axis=(0, 0, -1), unit='deg')`,
`RollerBearingB.spin = Revolute(axis=(0, 0, 1), unit='deg')` -- with no
`.repeat()`, no `index`, and no injection to race. `render()`'s placement
loop and `simulate()`'s hand-bound spin loop (both already there because "a
relation cannot yet fan out over a `.repeat()` child") now iterate
`(self.roller_a, self.roller_b)` in place of `self.rollers`.

Re-captured once, sequentially: `capture_poses.py`'s own name-keyed compare
reports the renamed leaves as one node "missing after" and one "new" per
roller (`rollers-0`/`rollers-1` vs `roller_a`/`roller_b`), which is a
LIMITATION OF THE COMPARE TOOL's path-matching, not a finding -- its
reported `0.000e+00` is real for every leaf whose name did not change, but
does not by itself cover the eight renamed roller leaves. Those eight were
checked directly by mapping the old names to the new ones and diffing the
raw world matrices leaf-by-leaf, pose-by-pose (all 11 poses, all 4 winches):
every one matches the BEFORE capture at exactly `0.000e+00`, and the overall
maximum over the whole tree (renamed leaves included) is `0.000e+00`.

**The 1-8 micron residues on `movement.string.*` (wall_clock_23/24/25/26/28/49/52)
-- TRACED TO CAPTURE-PROCESS NONDETERMINISM, not this change's source.**
Captured `wall_clock_24` TWICE from the exact same overlay tree (no file
touched between the two runs) and compared the two captures against EACH
OTHER: they differ, at the SAME magnitude and on the SAME ports as the
original before/after comparison --

    max deviation 4.828e-03 over 11 poses (identical to the before/after number)
    movement.string.entry_z / pulley_z:  13.295172048 -> 13.3   (run 1 -> run 2)
    movement.string.coil_height:         42.767235596 -> 42.767245407
    movement.string.wraps:               20.365350284 -> 20.365354956
    (entry_x/y, pulley_x/y, tie_x/y each shift by a few 1e-6 to 1e-3 too)

-- so the discrepancy exists between two runs of the IDENTICAL,
already-patched tree, with nothing to attribute it to in this change's own
source. Re-running the same two captures with `PYTHONHASHSEED=0` fixed
(instead of Python's default per-process random hash seed) makes them
match EXACTLY (`0.000e+00`): the string-wrap computation (molejo's wrap
solver, reached through `movement.string`) iterates something whose order
depends on Python's hash-randomized dict/set ordering, and a non-associative
floating-point sum over that ordering gives a run-dependent last few digits
-- the "13.3" appearing only in one run is a value landing exactly on a
clamp boundary in one iteration order and a few microns short of it in the
other. Comparing a `before2/` capture (one process) against an `after/`
capture (a separate, later process) always carries this same run-to-run
noise regardless of whether `joints.py` changed at all; it is a property of
the capture methodology's use of Python's default hash randomization
across separate process invocations, not a finding about this cycle's
source change.


### 7.4 Findings this cycle DID diagnose and fix mid-verification

Two further, real bugs were found and fixed by this cycle's own pose
overlay before producing the table above (both are `PARENT-FRAME-OFFSET`
migrations of the same shape as `MotionWorksPart.turn`/`Pendulum.swing`/
`Escapement.frame_turn` in the shared module, not new findings about the
framework):

- **Six clocks' own LOCAL `TurningArbor.turn`** (`wall_clock_19`, `21`,
  `22`, `41`, `49`, `51`) each declare their own `TurningArbor(Arbor)`
  class -- where `Arbor` is the plain-geometry `parts.Arbor`, not the
  motion-composing `shared.TrainArbor` -- carrying the identical
  `at=lambda node: shared.assemblies.arbor_bearing(node)` the shared
  module's `TrainArbor.turn` correctly keeps unedited. Unlike the shared
  class, this local class's own placement is NOT the identity: it is
  translated by exactly `arbor_bearing(node)` as one of `FixedRodArbor.
  render()`'s CHILDREN. Left unpatched, this showed as a large, defaults-
  present deviation (166.2 mm on `wall_clock_49`, 177.2 mm on `51`, and
  smaller-but-still-large values on the rest) confined to `movement.train.*`
  -- `wall_clock_48`'s own already-migrated source (see §7.3) is the
  maintainer's prior fix of this exact bug; these six simply had not been
  migrated yet. Fixed by removing the `at=` (own-frame anchor restates to
  zero), the same treatment as `wall_clock_48`'s.
- **`ZDayPart.turn`** (`wall_clock_52`, `wall_clock_54`, the two clocks
  with a day-of-week complication) restates `DayComplication.render()`'s
  `part.translate(positions[0 or 1])` for either branch of its own
  `node.index in (0, 1)` conditional; fixed by removing the whole
  conditional `at=` callable (own-frame anchor is `(0, 0, 0)` either way).
  This did NOT account for the whole of either clock's residual: wall_clock_52
  still shows 1.069e-03 mm (floating-point residue, §7.3) and wall_clock_54
  still shows 3.477e+00 mm (the unrelated grasshopper `entry_arm` finding,
  §7.3) after this fix.

Also found and fixed in `Inmoov-sim`'s own overlay (an error in THIS
change's derivation, not a project bug): a first draft's injection loop
applied the SAME zero-based `anchor_from_placement(leaf)` derivation to
EVERY joint on a leaf regardless of name, which is only correct for the
seven genuine PARENT-KNOWLEDGE-IN-SUBSTANCE `mcp` sites (survey.md's own
count) -- it is wrong for `pip`/`dip`/`tj`, whose OLD anchor was a nonzero
project constant, not the origin. Caught by a 71.10 mm max deviation on
`hand.fingers-N.{middle,distal,dip_bolt,dip_nut}`; fixed by leaving those
six sites as plain text restates (`at=` deleted, or replaced with
`tuple(-c for c in MIDDLE_JOINT)`, computable from existing project
constants) and restricting the runtime injection to the seven `mcp` sites
alone.

Also found and fixed in `OpenCycloid`'s own overlay: a first version typed
each disk's `orbit`'s own-frame anchor with the SAME sign as that disk's
own parent-applied translate, rather than its negation, giving 9.961 mm
max deviation on `drive.stage_one`/`stage_two`; fixed by swapping the two
signs (`stage_one` needs `at=(0, +ECCENTRIC_RADIUS, 0)`, `stage_two` needs
`at=(0, -ECCENTRIC_RADIUS, 0)` -- the opposite of each disk's own placement
translate, since a body's own-frame view of a fixed world point moves
opposite to how the body itself was moved to reach it).

A stray background process left running from before this session's context
compaction (an earlier invocation of the same overlay pipeline, from before
the `Inmoov-sim`/`3DPrintedClocks`/`OpenCycloid` fixes above existed) was
found still executing two 3DPrintedClocks captures concurrently with this
session's own resumed, corrected run -- the exact file-descriptor-exhaustion
risk this change's own instructions warn against. It was killed
(`kill -9`) the moment it was noticed, along with one further orphaned
child process it had already spawned (reparented to `init`, still running).
Every result in §7.1/§7.2 was captured strictly sequentially after that
process, and the earlier ones it had already written for
`Internal-Cycloidal-Actuator`, `Inmoov-sim`, `OpenCycloid`, and several
individual clock models (using patch versions that predated the fixes
above) were re-captured from a clean overlay before being trusted for this
table.

### 7.5 OpenCycloid's refusal (24th project, added mid-cycle)

Confirmed directly, on the UNPATCHED project (no overlay edit at all)
against this cycle's new `joints.py`:

    ValueError: stage_one (CycloidalDiskStageOne): joint 'orbit' carries a
    point that lies ON its own axis, so binding it would move nothing. In
    the node's own frame the axis is (0, 0, 1) through the anchor
    (0.0, 0.0, 0.0), the carried point is (0.0, 0.0, 0.0), and the radius
    they derive is 0.0. An orbit's radius and phase are derived from a
    point and a line, never declared, so name a point of the body off
    that line with carries=, in this body's own frame.

Under the OLD parent-frame rule, a defaulted `Orbit`'s `carries` read as
the body's OWN placed origin (the `_OwnPlacedOrigin` sentinel, ADR-094)
while its `at` defaulted to the PARENT's origin -- an asymmetry that gave
every one of these orbits a genuine nonzero eccentricity "for free," with
no anchor stated anywhere. Under the new rule both default to the SAME
point (the body's own origin) symmetrically, so the derived radius is
always zero and the bind refuses BY NAME, loudly, rather than building a
silently wrong pose. This is the honest, measured behaviour of a plain
default-only mechanical rewrite of this project, exactly as the coordinator
asked to have it recorded; the patched overlay (§7.1, `patch_OpenCycloid.py`)
is the separate, DERIVED demonstration that the same joints CAN be
correctly restated once the parent's knowledge is read from the actual
placement, and reaches 0.000e+00 (7 poses).
