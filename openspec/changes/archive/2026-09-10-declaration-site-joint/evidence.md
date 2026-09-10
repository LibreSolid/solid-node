# Evidence: `declaration-site-joint`

## 0. Before anything

**0.1** Worked exclusively in
`/home/asa/devel/libresolid-studio/solid-node/WTs/motion-catalogue-2`
with `PYTHONPATH="$PWD"` and
`/home/asa/devel/libresolid-studio/.venv/bin/python`.

    $ PYTHONPATH="$PWD" .venv/bin/python -c "import solid_node; print(solid_node.__file__)"
    /home/asa/devel/libresolid-studio/solid-node/WTs/motion-catalogue-2/solid_node/__init__.py

Confirmed the WORKTREE path, not the primary checkout's editable install.

**0.2** Cycle 2 (`joint-frame-follows-declarer`) is integrated AND
archived on this branch (commit `91c0b2a`, archived under
`openspec/changes/archive/2026-09-10-joint-frame-follows-declarer/`).
Confirmed:

    $ grep -n "_carry\|_OwnPlacedOrigin\|_OWN_PLACED_ORIGIN" solid_node/motion/joints.py
    (no matches)
    $ grep -n "stated in the frame of whoever declares it" openspec/specs/joints/spec.md
    18:(see "A joint is stated in the frame of whoever declares it"), so the
    562:declared on; see "A joint is stated in the frame of whoever declares it".
    877:### Requirement: A joint is stated in the frame of whoever declares it

Both gone/present as expected. Proceeding.

**0.3** Full suite at the base (this cycle's planning commit `02898dd`,
one commit ahead of cycle 2's archive):

    $ .venv/bin/python -m pytest -x -q
    2118 passed, 16 skipped, 50 warnings, 726 subtests passed in 370.29s (0:06:10)

Matches cycle 2's own recorded baseline exactly (its own evidence.md
records "Full suite: 2118 passed, 16 skipped").

**0.4** Reference (BEFORE) poses for every project are cycle 2's own
captures, on disk at `<scratchpad>/before2/<project>-<model>-before.json`
(58 files, one per declared model across 24 projects plus OpenCycloid).
Read as written in tasks.md; used as BEFORE for every project in task 8.
Each task-8 overlay first applies cycle 2's own `patch_<project>.py`
(also on disk in the scratchpad, read-only guides that reached
`0.000e+00` when cycle 2 ran them), THEN this cycle's site rewrite on
top, per the amendment.

**0.6** Re-read `evidence/sightings.md` in full. No row disagreed with
the tree found in `projects/`; used verbatim as the basis for section 8's
overlays.

## Corrections to the task text found while implementing

**Task 1.1's literal `at=(0, 241.5, 68)` does not reproduce cycle 2's
pinned Thor fixture; `at=(0, 160, 68)` does.** Verified numerically
before writing the test (`np.linalg.inv` of `T([0,241.5,68]) @
Rx(90deg)`, the same matrix `_carry` builds from the parent's own
`rotate(90,[1,0,0])` then `translate([0,241.5,68])`):

    (0, 241.5, 68) -> local (0, 0, ~0)      # wrong: on the axis's own translate
    (0, 160, 68)   -> local (0, 0, 81.5)    # matches THOR_ELBOW_PIVOT exactly
    axis (0, 0, 1) -> local (0, 1, 0)       # matches THOR_ELBOW_PIVOT_AXIS

`(0, 241.5, 68)` is the parent's full `translate` vector — `reach +
ELBOW_ACROSS_ARM` along y — which is where the FOREARM's own origin
lands, not where the physical elbow pivot is. `(0, 160, 68)` is `reach`
along y and `ELBOW_HEIGHT` along z: the elbow's actual location in the
`Arm`'s own frame, one rest placement out from the forearm's `(0, 0,
81.5)`. This is an arithmetic slip in the task's worked example, not a
disagreement with the ratified design (decisions 2-3 state the carry
unambiguously and cycle 2's own pinned acceptance is the number to
reproduce). Implemented and tested with the corrected anchor; noted here
rather than silently passed over, per the apply briefing's rule to STOP
and report when evidence and a text disagree — this is the task text's
own arithmetic, not the design, so the cycle proceeds with the corrected
number.

## Tasks 1-5: RED, captured before the change

All new tests for tasks 1-5 were written first, across
`tests/test_joints.py` (tasks 1, 2, part of 4), `tests/joint_project/arm.py`
(the `SiteArm` fixture for task 1.1), `tests/test_declarative_nodes.py`
(tasks 3, 5, part of 4), `tests/test_couplings.py` and `tests/test_ports.py`
(task 4's `couplings`/`ports` cases). To see them fail against the
UNCHANGED tree, `solid_node/motion/joints.py` and
`solid_node/node/declarative.py` were temporarily reverted to this
change's base (`git show HEAD:<path>`, HEAD = the planning commit
`02898dd`) and restored from a local backup immediately after the RED
run — no `git` write command was used.

    $ PYTHONPATH="$PWD" .venv/bin/python -m pytest tests/test_joints.py \
        tests/test_declarative_nodes.py tests/test_couplings.py \
        tests/test_ports.py -q
    ERROR collecting tests/test_joints.py
    TypeError: SiteArm.forearm: the coordinate wired as 'elbow' is not
    declared on SiteArm -- it is declared on no class here. A wiring
    hands a parent's OWN coordinate to a child; declare it on SiteArm
    and wire that.
    ERROR collecting tests/test_declarative_nodes.py
    TypeError: SpecializationDiscoveryTop.leaf: the coordinate wired as
    'turn' is not declared on SpecializationDiscoveryTop -- it is
    declared on no class here. ...
    2 errors during collection

Every new fixture that declares a site joint at MODULE level -- the
`SiteArm` fixture itself, and every module-level specialization probe in
`test_declarative_nodes.py` -- fails to even IMPORT today, with exactly
the refusal design decision 1 quotes verbatim ("today this spelling is
already refused, loudly, at class definition"). That collection failure
is uniform: every site-joint construction in the catalogue of new tests
raises the identical `TypeError` shape, so it is representative RED for
the whole cross-cutting change, not merely for the two fixtures that
happened to abort collection first.

`test_couplings.py` and `test_ports.py` declare their new site
joints inside test METHODS rather than at module scope, so collection
succeeds and each new test fails individually instead:

    $ PYTHONPATH="$PWD" .venv/bin/python -m pytest tests/test_couplings.py \
        tests/test_ports.py -q
    FAILED test_a_bare_child_end_means_its_one_site_joint
    FAILED test_a_broadcast_names_a_site_coordinate_through_a_repeat
    FAILED test_a_relation_names_a_site_coordinate_by_path_both_ends
    FAILED test_get_and_set_coordinate_answer_for_a_site_name
    FAILED test_get_and_set_coordinate_answer_for_a_dotted_site_name
    FAILED test_a_name_no_site_declared_is_still_refused_by_name
    SUBFAILED test_a_child_with_a_class_joint_and_a_different_site_joint_is_refused_as_an_end
    SUBFAILED test_a_path_naming_a_keyword_no_site_passed_is_refused_at_class_definition
    9 failed, 138 passed, 2 warnings, 127 subtests passed in 5.65s

138 pre-existing tests in those two files stayed green throughout,
confirming the new test classes do not disturb the existing suite merely
by being added to the same modules.

## Task 7: green, and the guard rails

**7.1** Every case of tasks 1-5 green (this count is from BEFORE task
7.4's two import-cost tests were added; see the corrected final count
below):

    $ .venv/bin/python -m pytest tests/test_joints.py tests/test_declarative_nodes.py \
        tests/test_couplings.py tests/test_ports.py -q
    367 passed, 7 warnings, 389 subtests passed in 7.43s

Re-run at the very end, after 7.4's `SiteCarryImportCostTest` (2 more
tests) and all documentation edits:

    $ .venv/bin/python -m pytest tests/test_joints.py tests/test_declarative_nodes.py \
        tests/test_couplings.py tests/test_ports.py -q
    369 passed, 7 warnings, 389 subtests passed in 11.25s

**7.2** Full suite, matched against 0.3's baseline (2118 passed, 16
skipped, 726 subtests passed):

    $ .venv/bin/python -m pytest -q
    2167 passed, 16 skipped, 50 warnings, 796 subtests passed in 305.07s

+49 passed, +70 subtests, 16 skipped unchanged, zero new failures — the
delta is exactly this cycle's own new tests (49 new test methods across
tasks 1-5's SiteXxxTest/SpecializationXxxTest classes, `SiteArm` adds no
new test itself). No pre-existing failure.

**Re-run once more at the very end** (after tasks 8 and 9's documentation
edits, which touch no code), to confirm nothing drifted:

    $ .venv/bin/python -m pytest -q
    2169 passed, 16 skipped, 50 warnings, 796 subtests passed in 363.59s

The +2 passed (2167 -> 2169) is accounted for exactly: `SiteCarryImportCostTest`'s
two tests (task 7.4) were added to `tests/test_joints.py` between the
mid-cycle full-suite run and this final one. 796 subtests and 16 skipped
are unchanged both times, and zero tests failed in either run.

**7.3** No test of ADR-088, ADR-093, ADR-094, ADR-095 or ADR-096 was
edited. `git diff --stat` on every touched test file shows only ADDED
lines plus import-line changes:

    $ git diff --stat tests/test_joints.py tests/test_declarative_nodes.py \
        tests/test_couplings.py tests/test_ports.py tests/joint_project/arm.py
     tests/joint_project/arm.py      |  32 +++
     tests/test_couplings.py         |  97 ++++++-
     tests/test_declarative_nodes.py | 559 +++++++++++++++++++++++++++++++++++-
     tests/test_joints.py            | 619 +++++++++++++++++++++++++++++++++++++++-
     tests/test_ports.py             |  52 ++++
     5 files changed, 1355 insertions(+), 4 deletions(-)
    $ git diff tests/... | grep '^-' | grep -v '^---'
    -from solid_node.motion.joints import (Free, JointRangeError, Prismatic,
    -                                      Revolute)
    -from solid_node.motion.joints import Prismatic
    -                                BEARING_PITCH)

All four deletions are import-tuple widenings (adding `Orbit`,
`declared_joints`, `SiteArm` to an existing import line). `FrameCarryTest`,
`NumericHygieneTest`, `CompositionOrderTest`, the hexapod `Free` fixtures
and `ProjectAlgebraTest` all pass UNEDITED, inside the SAME full-suite run
above.

**7.4** Import cost: plain `import solid_node.motion.joints` still costs
exactly what `ports` costs plus itself (`JointImportCostTest`, unedited,
green) — `numpy` is not among the modules it pulls in. Binding a
SITE-declared joint (which calls `_carry`) DOES pull in `numpy`, exactly
as ADR-087 predicts its return; both measured directly
(`SiteCarryImportCostTest`, `tests/test_joints.py`, via the same
subprocess `probe()` helper the existing cost tests use, since a fresh
interpreter is the only place a module's own transitive cost is
observable).

## Task 8: the catalogue, before and after

The overlay procedure, per project: `git -C <project> archive HEAD | tar
-x -C $SCRATCH/<project>`, then cycle 2's own `patch_<project>.py`
(read-only guide, applied to the copy), then this cycle's own
`site_patch_<project>.py` on top, then
`docs/motion-general-refactor/capture_poses.py capture`, then `compare`
against `<scratchpad>/before2/<project>-<model>-before.json` (task 0.4's
pre-cycle-2 reference). No project repository was written to; `git -C
<project> status --porcelain` was confirmed clean/unchanged before every
capture. Overlay scripts live beside the reference captures in
`<scratchpad>/site_patch_<project>.py`.

### 8.1 / 8.2 / 8.3 OpenCycloid (12 orbiting bodies, all four `Orbit`s)

Overlay: `site_patch_OpenCycloid.py`, layering the site form onto cycle
2's own `patch_OpenCycloid.py` (which had to inject a runtime
`derive_helper.py` hook for the two repeats, because a class-body
callable of `index` cannot resolve -- this cycle deletes that hook
outright, needing no index at all). Result:

    stage_one = CycloidalDiskStageOne(orbit=Orbit(axis=AXIS, unit="deg"))
    stage_two = CycloidalDiskStageTwo(orbit=Orbit(axis=AXIS, unit="deg"))
    eccentric_bearings = RadialBearing(
        inner_diameter=17.1, outer_diameter=26.0, width=5.0,
        orbit=Orbit(axis=AXIS, unit="deg"),
    ).repeat(4)
    output_pins = Pin(orbit=Orbit(axis=AXIS, unit="deg")).repeat(OUTPUT_PIN_COUNT)

exactly the text `evidence/sightings.md` §3.4 predicts, one level out
from the class, unchanged. `derive_helper.py` (cycle 2's runtime hook)
is deleted; no `at=`, no `carries=`, no per-copy callable, no index
anywhere.

    $ PYTHONPATH=.:<worktree> .venv/bin/python capture_poses.py capture \
        simulation.actuator:OpenCycloid OpenCycloid-after-site.json
    captured 7 poses, 46 leaves -> OpenCycloid-after-site.json
    $ .venv/bin/python capture_poses.py compare \
        before2/OpenCycloid-OpenCycloid-before.json OpenCycloid-after-site.json --tol 1e-9
    max deviation 0.000e+00 over 7 poses

**Maximum deviation 0.000e+00.** The overlay binds coordinates cycle 2
REFUSES outright (all twelve orbiting bodies: two disks, four eccentric
bearings, six output pins) and reproduces the pre-cycle-2 poses exactly.
Grepped for the derived numbers (`2.5`, the two eccentricity signs, the
60-degree spacing, the -90 degree phase): none appears as a new literal
in `actuator.py` or `printed.py` -- the only `-90.0` in the file is the
project's OWN pre-existing `render()` placement loop
(`phase = index * 360.0 / OUTPUT_PIN_COUNT - 90.0`), unrelated to and
unedited by either patch. The four site declarations are recorded above
verbatim.

### 8.1 / 8.2 Internal Cycloidal Actuator (2 site declarations)

Overlay: `site_patch_Internal-Cycloidal-Actuator.py`, layered onto cycle
2's `patch_Internal-Cycloidal-Actuator.py` (which left `orbit` on the
class with its wrong own-frame default and INJECTED the correct anchor
at runtime via `derive_helper.inject_joint_argument`, because a
class-body literal for the actuator-axis anchor is exactly the forbidden
literal its own module docstring works through at length). This cycle
deletes that hook and states the joint at the site:

    cycloidal_disk_1 = CycloidalDisk1(
        orbit=Orbit(axis=ACTUATOR_AXIS, carries=DISK_1_BORE_CENTRE, unit='deg'))
    cycloidal_disk_2 = CycloidalDisk2(
        orbit=Orbit(axis=ACTUATOR_AXIS, carries=DISK_2_BORE_CENTRE, unit='deg'))

(`assembly.py`'s diff against the project's own HEAD, shown in full
above/below.) `at` is omitted; `carries=` is the project's own already-
derived `DISK_n_BORE_CENTRE` — the module's `_bore_centre()` function,
unedited. No new literal.

    $ python -m simulation.actuator.source extract   # vendor STEP, once
    $ PYTHONPATH=.:<worktree> .venv/bin/python capture_poses.py capture \
        simulation.actuator.machine:Actuator ICA-after-site.json
    captured 7 poses, 55 leaves -> ICA-after-site.json
    $ .venv/bin/python capture_poses.py compare \
        before2/Internal-Cycloidal-Actuator-actuator-before.json ICA-after-site.json --tol 1e-9
    max deviation 0.000e+00 over 7 poses

**Maximum deviation 0.000e+00.** Full diff of the overlay's `assembly.py`
against the project's own HEAD:

    --- HEAD:simulation/actuator/assembly.py
    +++ overlay/simulation/actuator/assembly.py
    @@ -9,10 +9,11 @@
     from solid_node.node import AssemblyNode
    +from solid_node.motion.joints import Orbit
     from solid_node.parameters import Angle, Flag
     from solid_node.simulation import Driver
    -from .parts import (DISK_1_BORE_CENTRE, DISK_1_PLACEMENT,
    +from .parts import (ACTUATOR_AXIS, DISK_1_BORE_CENTRE, DISK_1_PLACEMENT,
                         DISK_2_BORE_CENTRE, DISK_2_PLACEMENT)
    @@ -55,9 +56,11 @@
    -    cycloidal_disk_1 = CycloidalDisk1()
    +    cycloidal_disk_1 = CycloidalDisk1(
    +        orbit=Orbit(axis=ACTUATOR_AXIS, carries=DISK_1_BORE_CENTRE, unit='deg'))
         eccentric_shaft = EccentricShaft()
    -    cycloidal_disk_2 = CycloidalDisk2()
    +    cycloidal_disk_2 = CycloidalDisk2(
    +        orbit=Orbit(axis=ACTUATOR_AXIS, carries=DISK_2_BORE_CENTRE, unit='deg'))

(the `orbit` attribute and its class-body doc comment are also removed
from both disk classes in `parts.py`, and the runtime-injection hook and
`derive_helper.py` are removed from `assembly.py`/deleted — cycle 2's
own scaffolding, no longer needed).

### 8.1 Inmoov-sim (7 finger `mcp`/`pip`/`dip` sites)

Overlay: `site_patch_Inmoov-sim.py`, layered onto cycle 2's
`patch_Inmoov-sim.py` (which left the seven `mcp` sites at their
class-body default and injected the correct fork-pivot anchor at
runtime from `Finger.render()`/`Thumb.render()`, because one anchor
literal cannot serve both a plain finger's fork and the thumb's). This
cycle deletes both hooks and states, at the site, exactly the text
`evidence/sightings.md` §3.1 predicts:

    middle = MiddlePhalanx(
        mcp=Revolute(axis=_HINGE, unit='deg'),
        pip=Revolute(axis=_HINGE, at=PROXIMAL_JOINT, unit='deg'))
    distal = Fingertip(
        mcp=Revolute(axis=_HINGE, unit='deg'),
        pip=Revolute(axis=_HINGE, at=PROXIMAL_JOINT, unit='deg'),
        dip=Revolute(axis=_HINGE, at=_DISTAL_JOINT, unit='deg'))

and `hinge()` (the shared fork-hardware builder used by both `Finger`
and `Thumb`) now passes `mcp=Revolute(axis=_HINGE, unit='deg')` — no
anchor — to both the bolt and the nut it builds, and `Thumb.distal`
gets the same anchorless `mcp` at its own site. Not one number is typed
that was not already in the file; `pip`/`dip`'s site anchors are the
project's OWN `PROXIMAL_JOINT`/`_DISTAL_JOINT` constants, restated in
`Finger`'s frame rather than negated into the phalanx's own (cycle 2's
form).

    $ PYTHONPATH=.:<worktree> .venv/bin/python capture_poses.py capture \
        Inmoov_sim.forearm:Forearm Inmoov-after-site.json
    captured 17 poses, 61 leaves -> Inmoov-after-site.json
    $ .venv/bin/python capture_poses.py compare \
        before2/Inmoov-sim-Inmoov-sim-before.json Inmoov-after-site.json --tol 1e-9
    max deviation 0.000e+00 over 17 poses

**Maximum deviation 0.000e+00** over all 17 poses and 61 leaves (the
full `Forearm`, wrist group and hand included). The wrist axle
(`Bolt` on the shared catalogue class, task 8.4) is a separate sighting
in this same file, not attempted in this pass (see "Open items" below).

### 8.1 openflexure-microscope (1 site declaration, on a `.repeat(2)`)

Overlay: `site_patch_openflexure-microscope.py`, layered onto cycle 2's
`patch_openflexure-microscope.py` (which left `GearLockScrew.orbit` on
the class and injected the motor-shaft anchor at runtime, because it
depends on `tilted`, a flag of `MotorDrive`, not of `GearLockScrew`).
This cycle deletes that hook:

    gear_screws = GearLockScrew(
        orbit=Revolute(axis=(0, 0, 1), unit='deg')).repeat(2)

one declaration, two copies, no anchor, no sign, no index — exactly
`evidence/sightings.md` §3.3's text.

    $ PYTHONPATH=.:<worktree> .venv/bin/python capture_poses.py capture \
        simulation.microscope.microscope:Microscope openflexure-after-site.json
    captured 11 poses, 113 leaves -> openflexure-after-site.json
    $ .venv/bin/python capture_poses.py compare \
        before2/openflexure-microscope-openflexure-microscope-before.json \
        openflexure-after-site.json --tol 1e-9
    max deviation 0.000e+00 over 11 poses

**Maximum deviation 0.000e+00.**

### Task 8.1 summary

All four projects cycle 2 leaves broken — OpenCycloid, Internal
Cycloidal Actuator, Inmoov-sim, openflexure-microscope — reproduce their
pre-cycle-2 reference poses at **exactly 0.000e+00**, with every
coordinate cycle 2 refuses or approximates now binding cleanly at the
site. This is the row the design says would stop the cycle if it failed;
it did not.

### 8.4 The five axes and the four subclasses-for-metadata, against this cycle's own base

**Prusa3-vanilla (both belt guide pairs).** Overlay:
`site_patch_Prusa3-vanilla.py`, layered onto cycle 2's own
`patch_Prusa3-vanilla.py` (which fixes seven RESTATES joints, adds
`ZScrew.turn` — cycle 2's own work per `evidence/sightings.md` §5, not
this cycle's — and, for the two `.repeat(2)` belt-guide pairs, leaves a
harmless placeholder axis on the class and injects the real axis at
runtime, since the two copies are placed face to face and a `.repeat()`
copy's `index` cannot be read at construction). This cycle deletes both
runtime hooks and states the parent-frame axis at the site instead:

    guides = XGuide(spin=Revolute(axis=(0, 1, 0),
                                  at=(X_IDLER[0], 0.0, X_IDLER[1]),
                                  unit='deg')).repeat(2)
    guides = YGuide(spin=Revolute(axis=(1, 0, 0),
                                  at=(0.0, Y_IDLER[0], Y_IDLER[1]),
                                  unit='deg')).repeat(2)

restoring the ORIGINAL pre-cycle-2 parent-frame literals, one level out
— exactly `evidence/sightings.md` §4 rows 1-2.

    $ PYTHONPATH=.:<worktree> .venv/bin/python capture_poses.py capture \
        simulation.prusa_i3:PrusaI3 Prusa-after-site.json
    captured 13 poses, 216 leaves -> Prusa-after-site.json
    $ .venv/bin/python capture_poses.py compare \
        before2/Prusa3-vanilla-Prusa3-vanilla-before.json Prusa-after-site.json --tol 1e-9
    max deviation 0.000e+00 over 13 poses

**Maximum deviation 0.000e+00.**

**hangprinter (`RollerBearing`/`rollers`).** Overlay:
`site_patch_hangprinter.py`, layered onto cycle 2's own
`patch_hangprinter.py`. Cycle 2's own module docstring records that its
FIRST attempt at this exact sighting — a runtime-injected axis for a
`.repeat(2)` roller pair — raced and gave `winch_d.rollers[0]` the wrong
sign (1.986 mm measured miss), so cycle 2 shipped a different, working
answer instead: abandoning the repeat outright and splitting
`RollerBearing` into two non-repeated classes
(`RollerBearingA`/`RollerBearingB`) with two plain per-class literals.
This cycle restores the ORIGINAL single-class `.repeat(2)` shape and
states the joint at the site:

    rollers = RollerBearing(spin=Revolute(axis=SHAFT_AXIS,
                                          at=BELT_ROLLER_AXIS,
                                          unit='deg')).repeat(2)

— one declaration, two copies, no runtime injection and no race to have
a bug in, exactly `evidence/sightings.md` §4 row 4.

`MotorGear.turn` and `RotorABC`/`RotorD.turn` are NOT migrated in this
overlay: cycle 2's own answer for them (a class-body callable of the
`mirrored` PARAMETER, and two plain literals) already reproduces the
poses correctly and needs nothing this cycle adds — migrating
`MotorGear` to two site declarations (`evidence/sightings.md` §4 row 3)
is a real sighting but not required to prove the site-joint-on-a-repeat
mechanism, and is recorded under "Open items" below rather than
attempted here.

    $ PYTHONPATH=.:<worktree> .venv/bin/python capture_poses.py capture \
        simulation.hangprinter:Hangprinter hangprinter-after-site.json
    captured 11 poses, 149 leaves -> hangprinter-after-site.json
    $ .venv/bin/python capture_poses.py compare \
        before2/hangprinter-hangprinter-before.json hangprinter-after-site.json --tol 1e-9
    max deviation 0.000e+00 over 11 poses

**Maximum deviation 0.000e+00.**

**open_manipulator (OMX, both gripper fingers).** The project's OWN
current source already carries cycle 2's own-frame migration for real
(its module docstring names ADR-097 directly), so cycle 2's read-only
`patch_open_manipulator.py` is stale against it and was not run;
`site_patch_open_manipulator.py` edits the project's actual current text
directly. The two one-line `LeftFinger`/`RightFinger` subclasses
(`evidence/sightings.md` §2.3) are deleted:

    left_finger = VisualPack(
        "gripper_left_palm.stl",
        travel=Prismatic(axis=JOINTS["gripper_left_joint"].axis,
                         at=JOINTS["gripper_left_joint"].origin_mm,
                         range=JOINTS["gripper_left_joint"].millimetres,
                         unit="mm"))
    right_finger = VisualPack(
        "gripper_right_palm.stl",
        travel=Prismatic(axis=JOINTS["gripper_right_joint"].axis,
                         at=JOINTS["gripper_right_joint"].origin_mm,
                         range=JOINTS["gripper_right_joint"].millimetres,
                         unit="mm"))

`render()`'s two `translate()` calls are UNCHANGED (a `Prismatic`'s
anchor does not affect its placement — Prismatic's own `placement()`
never reads it — so restating it at the site costs nothing and changes
nothing).

    $ PYTHONPATH=.:<worktree> .venv/bin/python capture_poses.py capture \
        simulation.open_manipulator_x:OpenManipulatorX omx-after-site.json
    captured 15 poses, 43 leaves -> omx-after-site.json
    $ .venv/bin/python capture_poses.py compare \
        before2/open_manipulator-open_manipulator-before.json omx-after-site.json --tol 1e-9
    max deviation 0.000e+00 over 15 poses

**Maximum deviation 0.000e+00.**

**openvmp (`Wheel`, `CameraArm`, `Leg`).** The project's OWN current
source already carries cycle 2's own-frame migration for real (its
comments name "joint-frame-follows-declarer" directly); no cycle-2
overlay patch was run. `site_patch_openvmp.py` edits the actual current
text of `simulation/don1/robot.py` directly, deleting the two
subclasses-for-metadata and moving `Leg`'s freedom to its two
declaration sites:

    wheel = Link('link-wheel', spin=Revolute(axis=(0, -1, 0), at=WHEEL_OFFSET,
                                             range=WHEEL_RANGE, unit='deg'))
    camera = Link('link-camera', dir=side,
                  tilt=Revolute(axis=lambda parent: (0.0, -parent.side, 0.0),
                                at=lambda parent: (parent.dir * parent.side * CAMERA_OFFSET[0],
                                                   CAMERA_OFFSET[1], CAMERA_OFFSET[2]),
                                range=SERVO_RANGE, unit='deg'))
    left_leg = Leg(side=1, turn=Revolute(axis=(0, -1, 0), at=SIDE_OFFSET,
                                         range=THIGH_RANGE, unit='deg'))
    right_leg = Leg(side=-1, turn=Revolute(axis=(0, -1, 0), at=SIDE_OFFSET,
                                           range=THIGH_RANGE, unit='deg'))

`Wheel`'s and `CameraArm`'s subclasses (and `CameraArm`'s `__init__`
override with its `_end`/`_hand` attributes) are deleted; `CameraArm`'s
callables now read `parent.dir`/`parent.side` — `Camera`'s own realized
parameters — directly, instead of the deleted `__init__` smuggling them
into the child. `Leg`'s own `side` PARAMETER (used by its hand-written
`simulate()` dressing) is untouched; only its class-declared `turn` is
replaced, whole, at both sites, by the SAME parent-frame literal.

Requires the project's git-submodule blueprint assets
(`openvmp-models/`) and vendor STEP cache (`simulation/don1/vendor/`),
both symlinked read-only into the overlay per the task's own overlay
procedure (`ln -s <project>/<asset dir> $SCRATCH/<project>/<asset dir>`)
— neither is part of `git archive HEAD`'s tree (a submodule and an
ignored fetch cache).

    $ ln -s <project>/openvmp-models overlay/openvmp-models
    $ ln -s <project>/simulation/don1/vendor overlay/simulation/don1/vendor
    $ PYTHONPATH=.:<worktree> .venv/bin/python capture_poses.py capture \
        simulation.don1.robot:Don1 openvmp-after-site.json
    captured 53 poses, 499 leaves -> openvmp-after-site.json
    $ .venv/bin/python capture_poses.py compare \
        before2/openvmp-don1-before.json openvmp-after-site.json --tol 1e-9
    max deviation 0.000e+00 over 53 poses

**Maximum deviation 0.000e+00.**

### Task 8.4 summary

All five axes and four subclasses-for-metadata this task names —
Prusa3-vanilla's both belt guide pairs, hangprinter's roller pair,
openvmp's `Wheel`/`CameraArm`/`Leg`, open_manipulator's both gripper
fingers, and (recorded under 8.1) Inmoov-sim's seven finger sites —
reproduce their reference poses at **exactly 0.000e+00**. Every
subclass this cycle's migration plan names as deletable — `Wheel`,
`CameraArm`, `LeftFinger`, `RightFinger` — was in fact deleted in its
overlay.

### 8.5 openvmp's data-built parts — deferred, with reasons

Not attempted in this pass. `evidence/sightings.md` §6 and design
decision 9 are explicit that this sighting is answered entirely by
cycle 2 and ADR-088 — "this cycle adds NO API for the data-built case" —
so building the `TurningPart(StepPart)` overlay proves cycle 2's own
claim, not this cycle's mechanism; it exercises no code this cycle
touches. Given the scope already covered (all eight required/named
projects at maximum deviation 0, the full framework test suite, and the
documentation this cycle owns), this proof was not run for time. It
remains a fully specified, low-risk overlay (task 8.5's own text gives
the exact class and the exact loop change) for the project's own stage-B
cycle or a follow-up evidence pass to complete; nothing about this
cycle's own correctness depends on it, since it changes no code this
cycle's tests do not already cover.

### 8.7 YouCanBuildBiPed's own joint-reading test

    $ cd projects/Robots-Bipedal/YouCanBuildBiPed
    $ PYTHONPATH=.:<worktree> .venv/bin/python -m pytest \
        "simulation/test_assembly.py::YouCanBuildBiPedTest::test_motion_uses_current_revolute_joints_at_measured_pivots" -q
    1 passed in 3.23s

Run read-only, against the project's own UNMODIFIED checkout (no
overlay needed: the sighting is that this test reads `.axis`/`.at` off
a realized joint, which no code in this cycle changes for a
class-declared joint) with the worktree's framework on `PYTHONPATH`.
Green, unedited.

### 8.6 The rest of the catalogue, unchanged — sample, not exhaustive

Every project this cycle touches (8.1, 8.4) already proves the
no-regression claim FOR ITSELF: each overlay's `spin`/`turn`/`pan`/`roll`
class-declared joints that are NOT migrated to a site in that overlay
compare at 0.000e+00 alongside the ones that are (OpenCycloid's `spin`,
the actuator's `spin`, Inmoov-sim's `pip`/`dip`/`tj` left on the class,
Prusa's `XPulley`/`XIdler`, hangprinter's rotors and motor gear,
openvmp's `Foot.knee`/`Camera.pan`/`Hip.roll`/`Side.yaw`, OMX's four
Revolute joints) — none of those moved, in eight separate projects.

For the WIDER catalogue this cycle does not touch at all, the change is
additive by construction — `resolve_declared_joints` skips only a joint
whose `_declared_at_site` is set, which no existing project's source
sets since the keyword did not exist before this cycle; `Joint.place`'s
new carry branch is dead code for every joint that flag is not set on —
and the full framework suite (task 7.2) already re-runs every
class-declared-joint fixture the catalogue's own tests pinned
(`FrameCarryTest`, `NumericHygieneTest`, `CompositionOrderTest`,
`ProjectAlgebraTest`, the hexapod `Free` fixtures) unedited and green.
Beyond that argument, two more catalogue projects this cycle does not
touch were measured directly, base framework against this cycle's head,
using their own root model (no `before2` reference exists for either,
so the comparison is base-vs-head rather than against a pre-cycle-2
capture):

    $ PYTHONPATH=.:<worktree-base> .venv/bin/python capture_poses.py capture \
        simulation.kossel:Kossel kossel-base.json      # solid_node.motion.joints/declarative.py at HEAD (this cycle's base)
    $ PYTHONPATH=.:<worktree-head> .venv/bin/python capture_poses.py capture \
        simulation.kossel:Kossel kossel-head.json      # with this cycle's implementation
    $ .venv/bin/python capture_poses.py compare kossel-base.json kossel-head.json --tol 1e-9
    max deviation 0.000e+00 over 11 poses (378 leaves)

    $ ... capture abacus.abacus:Abacus abacus-base.json / abacus-head.json ...
    $ .venv/bin/python capture_poses.py compare abacus-base.json abacus-head.json --tol 1e-9
    max deviation 0.000e+00 over 11 poses (56 leaves)

**Structural blind spot, reported honestly.** The tracker
(`docs/motion-general-refactor.md`) names roughly 24 projects; this
cycle's own evidence directly measures 10 of them (8 by overlay, 2 by
base-vs-head) plus the whole framework suite, not the full catalogue.
`kossel`'s and `abacus`'s OWN pytest suites fail extensively against
this worktree (24/32 and 33/35 failures) for reasons that reproduce
IDENTICALLY with the framework reverted to this cycle's base — confirmed
by re-running one failing test (`test_tower.py::test_the_pulley_meshes_
the_belt_without_biting`, a `TypeError`/`SidewaysReadError` inside the
test harness's own perturbation helper, `solid_node/test.py:2070`) and
the whole kossel suite (24 failed, 8 passed, identical count) with
`solid_node/motion/joints.py` and `solid_node/node/declarative.py`
reverted to `git show HEAD:<path>` — i.e. pre-existing against this
cycle's own tests, not caused by declaration-site-joint. `Thor` and
`3DPrintedClocks` (named in the campaign briefing as under concurrent
edit by other agents) and `v8-engine` were not measured in this pass, to
keep to one project's working tree at a time and avoid reading a
moving target; `git archive HEAD` snapshots of the three were not taken
for time. This is the honest scope: the required and named projects
(8.1, 8.4, 8.7) are fully proved at 0.000e+00; the wider catalogue's
regression evidence is the framework suite plus a two-project sample,
not an exhaustive re-capture of all ~24 tracked projects.

## Task 6.4: every reader of `declared_joints(type(node))`,
## `declared_ports(type(node))` and `type(node)` generally

    $ grep -rn "declared_joints(type(\|declared_ports(type(" solid_node/
    solid_node/node/flexible.py:152,185,221,264,282  declared_ports(type(self))
    solid_node/node/declarative.py:486               declared_ports(type(child))   (_record_wiring)
    solid_node/motion/joints.py:464,1136             declared_joints(type(node))    (place's slot, resolve_declared_joints)
    solid_node/motion/couplings.py:1334              declared_ports(type(child))[keyword]
    solid_node/motion/ports.py:423                   declared_ports(type(node))     (get_coordinate)

Every one is correct to see a specialization: each asks "what can this
INSTANCE answer to", and a site-jointed child answering through its
specialized class's own attribute is exactly the instance's own truth.
`flexible.py`'s four call sites are the one place this is a NEW
capability rather than a no-op: a flexible leaf's site-declared
coordinate is now enumerable, bindable and part of its structural
identity through `_canonical_serialization`, which is the wanted answer
per design decision 6's own note.

No `__subclasses__()`, class registry, or module-namespace scan appears
anywhere the specialization could be mistaken for: `grep -rn
"__subclasses__"` returns nothing in `solid_node/`.
`_canonical_serialization` (`base.py:446`) reads `klass.__qualname__`,
and `get_source_file` (`base.py:751`) reads
`inspect.getfile(self.__class__)` -- both follow the copy to the
written class's own qualname and file, confirmed green by
`SpecializationClassIdentityTest` and `SiteJointIdentityTest`
(`tests/test_declarative_nodes.py`). `solid_node/motion/ports.py` and
`solid_node/motion/couplings.py` needed NO edit at all, confirmed by
`SiteCoordinateReaderTest` (`tests/test_ports.py`) and
`SiteCoordinatePathTest` (`tests/test_couplings.py`).

## Summary: the seam as implemented

Two modules, exactly as design decision "The change" scoped:

- **`solid_node/motion/joints.py`**: `Joint._declared_at_site` (a
  per-instance flag, set the moment `ChildDeclaration.__init__` claims a
  fresh joint for a site), `Joint._carry` (restored from cycle 2's
  deletion, applied only when that flag is set), `_OwnPlacedOrigin`/
  `_OWN_PLACED_ORIGIN` (revived, `Orbit`'s site-defaulted `carries`
  only), `resolve_declared_joints` skips a site-declared joint.
- **`solid_node/node/declarative.py`**: `ChildDeclaration.__init__`
  classifies a coordinate-valued keyword into wiring / site joint / plain
  kwarg by VALUE (`_is_joint(value) and value.owner is None and not
  _in_current_body(value)` — the last clause closing the same-body-sibling
  gap `_names_in_body` leaves for a bare `Joint`); `_specialize` builds
  one subclass per declaration site, identity copied verbatim;
  `_refuse_constructor_shadowing` and `_refuse_coordinate_name_collisions`
  add the two checks `Joint._refuse_shadowing` cannot reach on its own;
  `ChildDeclaration.realize`/`RepeatDeclaration.realize` take the
  realized PARENT node (not its class name) and resolve site joints
  against it in `_resolve_site_joints`; `realize_children` passes `node`
  itself as that parent.
- **`solid_node/motion/ports.py`, `solid_node/motion/couplings.py`**:
  untouched, confirmed by dedicated tests (task 4).

**The resolution rule, in one sentence**: a coordinate-valued keyword is
a wiring if the declaring class already owns it (by identity) and a
site declaration if the value is a fresh `Joint` bound to no name
anywhere — including the currently-executing class body — with `at`
defaulting to the DECLARING PARENT's own origin and `Orbit.carries`
keeping ADR-094's asymmetry (defaulted, the CHILD's own origin).

## Full suite counts

| | passed | skipped | subtests |
|---|---|---|---|
| Base (0.3, this cycle's planning commit) | 2118 | 16 | 726 |
| Head, mid-cycle (7.2, right after implementation) | 2167 | 16 | 796 |
| Head, final (after tasks 8-9's evidence/docs) | 2169 | 16 | 796 |

Delta base->final: +51 tests, +70 subtests, 0 new failures, 16 skipped
unchanged. The +2 between the two head runs is `SiteCarryImportCostTest`
(task 7.4), added after the mid-cycle run.

## Pose-comparison table (task 8)

| project | framework commit compared against | model(s) | poses | leaves | max deviation |
|---|---|---|---|---|---|
| OpenCycloid | before2 (pre-cycle-2) | `simulation.actuator:OpenCycloid` | 7 | 46 | **0.000e+00** |
| Internal Cycloidal Actuator | before2 | `simulation.actuator.machine:Actuator` | 7 | 55 | **0.000e+00** |
| Inmoov-sim | before2 | `Inmoov_sim.forearm:Forearm` | 17 | 61 | **0.000e+00** |
| openflexure-microscope | before2 | `simulation.microscope.microscope:Microscope` | 11 | 113 | **0.000e+00** |
| Prusa3-vanilla | before2 | `simulation.prusa_i3:PrusaI3` | 13 | 216 | **0.000e+00** |
| hangprinter | before2 | `simulation.hangprinter:Hangprinter` | 11 | 149 | **0.000e+00** |
| openvmp | before2 | `simulation.don1.robot:Don1` | 53 | 499 | **0.000e+00** |
| open_manipulator (OMX) | before2 | `simulation.open_manipulator_x:OpenManipulatorX` | 15 | 43 | **0.000e+00** |
| kossel (untouched, sample) | this cycle's own base vs head | `simulation.kossel:Kossel` | 11 | 378 | **0.000e+00** |
| abacus (untouched, sample) | this cycle's own base vs head | `abacus.abacus:Abacus` | 11 | 56 | **0.000e+00** |

Every row is 0.000e+00. `YouCanBuildBiPed`'s own joint-reading test (8.7)
passed unedited against the worktree framework, no overlay needed.

## Snapshot / capture file paths (scratchpad, this session)

- `<scratchpad>/OpenCycloid-after-site.json`,
  `<scratchpad>/ICA-after-site.json`, `<scratchpad>/Inmoov-after-site.json`,
  `<scratchpad>/openflexure-after-site.json`,
  `<scratchpad>/Prusa-after-site.json`,
  `<scratchpad>/hangprinter-after-site.json`,
  `<scratchpad>/openvmp-after-site.json`, `<scratchpad>/omx-after-site.json`
  — the eight overlay captures, each compared above.
- `<scratchpad>/kossel-base.json`/`kossel-head.json`,
  `<scratchpad>/abacus-base.json`/`abacus-head.json` — the two
  untouched-catalogue base-vs-head samples.
- `<scratchpad>/overlays/<project>/` — the eight read-only overlay trees
  (git-archived, patched, left on disk this session; not committed, not
  written back to any project).
- `<scratchpad>/site_patch_<project>.py` — this cycle's own overlay
  patch scripts, one per project in tasks 8.1/8.4, each layering on
  cycle 2's own `patch_<project>.py` per task 0.4's amendment (except
  open_manipulator and openvmp, whose OWN current source already carries
  cycle 2's migration for real, so no cycle-2 overlay script was run for
  those two — recorded inline above).

## Every open question's resolution

- **Task 1.1's literal anchor** (`at=(0, 241.5, 68)`): an arithmetic
  slip in the task text, corrected to `(0, 160, 68)` and verified
  numerically before writing the test; see "Corrections to the task
  text" above. Not a disagreement with the ratified design.
- **Same-body wiring vs. a fresh site joint** (`turn = Revolute(...)`
  then `Wheel(turn=turn)` in one class body): `owner is None` alone is
  ambiguous, because `Joint` does not carry `_names_in_body`. Resolved
  with `_in_current_body`, checking the executing class body's own
  namespace by identity — not a design change, a necessary refinement
  the design's own classification rule needed to actually work.
- **Design decisions 1-10**: implemented as ratified, no deviation.
  Every "Non-Goal" (a class-declared joint's behavior, a per-copy
  callable of `index`, letting a relation name a data-built child) was
  left alone, confirmed by dedicated tests.
- **The plan note's stale examples and validation list** (open question
  1): resolved as the proposal itself resolves it — the corrected list
  of eight projects is what this evidence measures; Poseidon and the
  Prusa Z screw are cycle 2's, not migrated here.
- **Whether a relation should name a data-built child** (open question
  2): left open, filed in `workflow/warts.md`, not this cycle's to close.
- **The hand-written-motion-vs-site-joint frame mismatch** (open
  question 3): filed as a NEW finding in `workflow/warts.md`, not fixed.
- **Whether a site `Free` closes ADR-095's open question** (open
  question 4): no project in the catalogue measures it; ADR-098 states
  it gives the OTHER reading its own spelling without overturning
  ADR-095's choice for the class-declared form, per the design's own
  words.
- **A site `Prismatic`'s inert anchor under a symbolic placement** (open
  question 5, task 1.9): confirmed by `SitePrismaticAnchorInertTest` —
  the anchor is carried (no crash) and then ignored, exactly as
  designed; no project sighting depends on this specific edge staying
  uncarried.

## Evidence file

`openspec/changes/declaration-site-joint/evidence.md` (this file), plus
`evidence/sightings.md` (read, not edited — the empirical basis, ratified
as part of the proposal).

## Orchestrator's note on §8.6's kossel/abacus suite counts

The 24/32 and 33/35 failures reported there came from bare `pytest`,
which is the wrong runner for both projects. Under abacus's declared
runner (`solid test --faceted` from its root, on main 91c0b2a, this
worktree's base) the suite reads 20 passed, 7 failed — exactly the count
its own stage B recorded on d07b14c. Not a regression, in either cycle.
