# `orbit-joint`: implementation evidence

Worktree `solid-node/WTs/composed-joints`, branch `composed-joints`,
planning commit `3cdff9e` on base `19730ac` (cycle 1, ADR-093).
Everything below was run from the worktree with `PYTHONPATH="$PWD"` and
`/home/asa/devel/libresolid-studio/.venv/bin/python`, which reports the
worktree's own `solid_node/__init__.py`.

## 1. The full suite, before and after

    before (planning commit, clean tree)
      2013 passed, 16 skipped, 49 warnings, 513 subtests passed in 278.11s
    after (this implementation)
      2031 passed, 16 skipped, 49 warnings, 592 subtests passed in 283.71s

18 new tests and 79 new subtests, no failure, no skip added, no
pre-existing failure to explain. `tests/test_couplings.py`,
`tests/test_animator_tag.py`, `tests/test_simulate_split.py` and
`tests/test_ports.py` are green **with no edit**: `git status` shows two
modified files in the whole tree, `solid_node/motion/joints.py` and
`tests/test_joints.py`.

## 2. Red first

### 2.1 The weak red: the name does not exist

    $ pytest tests/test_joints.py -q
    ImportError while importing test module 'tests/test_joints.py'.
    E   ImportError: cannot import name 'Orbit' from
        'solid_node.motion.joints'
    1 error in 0.34s

That is the whole file failing to collect, which says nothing about what
any one case asserts. Two things were done about it.

### 2.2 The strong red: a stub whose name exists and whose behaviour does not

A temporary `Orbit(Joint)` was added with `coordinate_kind =
RotationalPort`, a `carries` keyword it stores and ignores, a
`_orbit_frame` returning zeros, and `placement()` returning `[]`. Every
case then fails on its own assertion:

    53 failed, 83 passed, 70 subtests passed in 3.61s

| Case | Task | RED message (verbatim) |
|---|---|---|
| `test_the_attitude_is_exactly_untouched` | 1.2 | `AssertionError: np.float64(0.0) not greater than 0.1` — the attitude half passes trivially for a joint that does nothing, so the case also asserts the body MOVED; that is the half that fails |
| `test_the_carried_point_lands_where_the_rotation_says` | 1.3 | `Not equal to tolerance rtol=0, atol=1e-09 ... ACTUAL array([0., -2.5, 0.]) DESIRED array([1.606969, 0.584889, 0.])` (default point, 17°); `ACTUAL array([0.378316, -5.25, 1.963896]) DESIRED array([1.963896, -5.25, -0.378316])` (stated bore centre, 90°) |
| `test_one_operation_and_it_is_a_translation` | 1.4 | `AssertionError: Lists differ: ['t'] != ['t', 't']` |
| `test_the_default_carried_point_is_the_placed_origin` | 1.5 | `AssertionError: np.float64(0.0) not greater than 0.1` |
| `test_the_anchor_may_be_any_point_of_the_line` | 1.6 | `AssertionError: np.float64(0.0) not greater than 0.1` |
| `test_a_carried_point_on_the_axis_is_refused_by_name` | 1.7 | `AssertionError: ValueError not raised` |
| `test_a_malformed_carries_fails_at_realization` | 1.8 | `AssertionError: ParameterError not raised` (three subtests: two components, an undeclared token, a callable that raises) |
| `test_a_symbolic_binding_publishes_the_trigonometry` | 1.9 | `AssertionError: 'sin(' not found in '0.0'` |
| `test_a_relation_drives_an_orbit_and_inverts` | 1.10 | `Not equal to tolerance rtol=0, atol=1e-09 ... ACTUAL array([0., -2.5, 0.]) DESIRED array([1.606969, 0.584889, 0.])` |
| `test_a_range_on_an_orbit_is_the_inherited_refusal` | 1.11 | green under the stub — a CHARACTERISATION test, red only on the name (2.1), and the method says so |
| `test_the_orbit_is_enumerable_as_a_joint_and_as_a_port` | 1.12 | green under the stub — red only on the name (2.1), as the task states |
| `test_an_orbit_composes_with_a_turn_of_the_same_body` | 2.1 | `AssertionError: Lists differ: ['t', 'r', 't', 't'] != ['t', 'r', 't', 't', 't']` |
| `test_an_orbit_in_the_middle_keeps_every_run_contiguous` | 2.2 | `AssertionError: Lists differ: ['t', 't', 'r', 't', 'r', 't'] != ['t', 't', 'r', 't', 't', 'r', 't']` |
| `test_re_binding_the_orbit_returns_it_to_its_own_slot` | 2.3 | `AssertionError: Lists differ: ['t', 'r', 't', 't'] != ['t', 'r', 't', 't', 't']` |
| `test_the_cycloidal_actuators_two_forms_are_one_transform` | 6.1 | `ACTUAL array([0.825422, -5.25, 3.913278]) DESIRED array([1.383079, -5.25, 3.716856])` at θ=17, `mesh_phase=0` |
| `test_the_actuators_radius_and_phase_are_derived_not_typed` | 6.1 | `AssertionError: 0.0 != 2.0 within 4 places (2.0 difference)` |
| `test_the_dogs_swung_offset_is_what_an_orbit_publishes` | 6.2 | `ACTUAL array([0., 12., -30.]) DESIRED array([0., 8.577376, 8.139636])` at 17° |

`test_the_two_joints_of_the_orbit_fixture_do_not_commute` is a fixture
guard, like cycle 1's own, and is green by construction: it fails only if
the fixture stops exercising the question.

### 2.3 What the hand-written equivalents fail

The tasks ask, for every case whose red is only the missing name, what a
hand-written equivalent fails. Probe:
`evidence/hand_equivalent.py` beside this file, run from the worktree with `PYTHONPATH="$PWD"`.

    1. The attitude, with the orbit written as a Revolute
       (what OpenCycloid and the Internal Cycloidal Actuator write today)
       theta=     0: max |R - R_rest| = 0.000000
       theta=    17: max |R - R_rest| = 0.292372
       theta=    90: max |R - R_rest| = 1.000000
       theta= 213.5: max |R - R_rest| = 1.833886
       theta=   360: max |R - R_rest| = 0.000000
       -- the acceptance is atol=0. A Revolute fails it at every angle
          but the identity.

    2. The operations a hand-written equivalent produces
       (YouCanBuildDog's two Prismatics, at 40 degrees)
       [['t', ['0', '-0.584888892202555', '0']],
        ['t', ['1.6069690242163481', '0', '0']]]
       -- an orbit is ONE operation; this is two, in two slots, and each
          carries a number the project computed rather than the angle it
          means.

    3. The inverse
       a trigonometric law= callable is a plain function, and the
       couplings solver refuses it backwards
       (test_couplings::test_a_non_invertible_law_needed_backwards_is_refused).
       So the dog's 40 Prismatics cannot be driven from the foot.

    4. The cycloidal identity, with the orbit written as a Revolute
       theta=17.0: max |R_got - R_want| = 0.275205,
                   max |p_got - p_want| = 0.550408 mm
       theta=90.0: max |R_got - R_want| = 1.063951,
                   max |p_got - p_want| = 2.127913 mm
       -- off in BOTH blocks; the project pays for it with a
          ratio=-(1 + 1/REDUCTION).

## 3. The mechanism, as implemented

All of it in `solid_node/motion/joints.py`.

- `Joint._carry(node, axis, *points)` — one inversion of the rest
  placement, as before; returns the carried axis and a TUPLE of carried
  points, one per argument. A point that is the module sentinel
  `_OWN_PLACED_ORIGIN` comes back as exactly `(0.0, 0.0, 0.0)` without
  touching the inverse.
- `Joint.carried_points(node, anchor)` — the new hook. `Joint` returns
  `(anchor,)`; `Orbit` returns `(anchor, self.arguments(node)[3])`.
- `Joint.place` — `self.arguments(node)[:3]`, then
  `self._carry(node, axis, *self.carried_points(node, anchor))`, then
  `self.placement(node, value, local_axis, *local_points)`. The slot
  rule, `clear`, the tagging and the sweep are untouched.
- `Joint.resolve` — unchanged; `Orbit.resolve` calls it and appends the
  fourth argument through the same `_vector` path `at` takes, or the
  sentinel when `carries` is unstated.
- `_orbit_frame(axis, anchor, carried)` — the one construction: the
  radius vector `across`, its quarter turn `quarter = axis × across`, and
  `radius`. `Orbit.placement` calls it, and the tests read the derived
  radius and phase off it rather than recomputing them.
- `Orbit.placement(node, value, axis, anchor, carried)` — refuses a
  radius within `_SNAP` of zero, then returns ONE `Translation` whose
  components are `(cos(value) - 1) * across[i] + sin(value) * quarter[i]`,
  each term dropped when its coefficient is within `_SNAP` of zero and
  the whole component a plain numeric `0` when both are. `cos` and `sin`
  are imported from `solid_node.math` INSIDE the method, so the module's
  import cost does not move (`JointImportCostTest` still passes).

**Task 3.6, the error class.** The on-axis refusal raises a plain
`ValueError` carrying `_where(node)`, the same shape the non-numeric rest
placement uses. No new name is exported: the test catches `ValueError`
and reads the message, and nothing needs to catch this case
specifically. `JointRangeError` stays the only named joint error.

## 4. Cycle 1's contract, with an orbit in it (task 2.4)

**No cycle-1 test needed an edit.** `git diff tests/test_joints.py` shows
exactly one deleted line in the whole file — the import statement,
replaced by one naming `Orbit`. Everything in §1.6b is intact, and the
three new cases are additions to `CompositionOrderTest`.

## 5. Nothing existing moved (task 6.3)

- (a) the whole suite green — §1 above.
- (b) cycle 1's composition tests green with an `Orbit` in the fixture —
  `SpunAndCarried` (a three-operation `Revolute` then a one-operation
  `Orbit`), `SlideSwingCarry` (a `Prismatic`, an off-origin `Revolute`,
  an `Orbit` and a hand-written rotation), both binding orders, the
  contiguity of the revolute's run, and re-binding the orbit.
- (c) `Revolute.placement` and `Prismatic.placement` are **byte-identical**
  to the base, checked by extracting each method's source from
  `19730ac`'s file and from this one:

      Revolute.placement identical: True  (501 bytes)
      Prismatic.placement identical: True  (625 bytes)

**Said plainly: this cycle has NO measurement over a real machine.**
`Orbit` is additive and nothing existing changes, so no pose comparison
of the catalogue was run or is meaningful here. The two project fixtures
in §6 reproduce a project's own numbers and its own hand-written
composition *inside the framework's test file*; they are not the
projects. The measurement over the machines themselves is the four
projects' adoption at stage B, in their own repositories, and it is not
this cycle's evidence.

## 6. The two project fixtures

### 6.1 The Internal Cycloidal Actuator's algebraic identity

`tests/test_joints.py::ProjectAlgebraTest::
test_the_cycloidal_actuators_two_forms_are_one_transform`, over
θ ∈ {0, 17, 90, 213.5, 360} × `mesh_phase` ∈ {0.0, 4.5}:

    actuator identity: max rotation deviation 0.000e+00,
                       max position deviation 4.441e-16 mm

Both acceptances hold as the task states them: the rotation blocks agree
at `atol=0` (asserted, not merely measured), the positions at `atol=1e-9`
with a measured maximum four orders of magnitude below it.

The derived radius is 2.0000 mm and the derived phase −79.0959°, the
`_axis_distance` and the angle the project's proposal records, neither
written anywhere in the declaration.

**One correction to the task's own numbers, and it is a finding.** Task
6.1 quotes `DISK_1_BORE_CENTRE = (0.378316, -5.25, 1.963896)` as an input.
That literal is a ROUNDING of the point the project DERIVES
(`R_r·B + t`), which is `(0.3783302103755334, -5.25, 1.9638905903847317)`.
Fed in as a literal it breaks the identity at **3e-6 mm**, and its own
derived radius is 2.0000026 rather than 2.0000000. The fixture therefore
derives the bore centre the way `_capture_disk_rest()` derives it and
CHECKS it against both recorded values — the project's `_close()`
reference `(0.3783, -5.25, 1.9639)` to 1e-3 and the task's six-decimal
figure to 1e-4. This is the argument for deriving rather than typing,
made by the number that was typed.

### 6.2 YouCanBuildDog's `swung_offset`

`test_the_dogs_swung_offset_is_what_an_orbit_publishes`: the project's
own `R(θ)·s − s`, written out, against an `Orbit` anchored at the chassis
pivot and carrying the knee pivot, over four angles and both measured
spans. The published translation agrees at `atol=1e-9`, and the derived
radius and phase are:

| Leg | Span (dy, dz) | Derived radius | Project typed | Derived phase | Project typed |
|---|---|---|---|---|---|
| front (three of four) | (22.9431, −32.7661) | 40.00004 mm | `radius=40.0000` | −54.99997° | `phase=-55.000` |
| back-left (0.076 short) | (22.8404, −32.7450) | 39.92391 mm | `radius=39.9239` | −55.10333° | `phase=-55.104` |

**A second finding.** The back-left phase the project's proposal typed,
`-55.104`, is not the angle of the span it was derived from: that span is
−55.1033°, a 7e-4° transcription of the third decimal. The framework
derives the span's own angle. The fixture asserts −55.1033 and records
the project's figure beside it; nothing in the project is edited.

## 7. Serialization: the design's probe, re-run against the real `Orbit` (task 6.5)

`evidence/probe_orbit.py` beside this file: a body placed by `translate([10, 0, 0])`,
axis z through the origin, the default carried point, bound from
`self.time * 360`:

    SYMBOLIC serialized: ['t', ['((cos(($t * 360)) - 1) * 10.0)',
                               '(sin(($t * 360)) * 10.0)',
                               '0']]
    KEYFRAME 0.25 serialized: ['t', ['-9.999999999999998', '10.0', '0']]
    CLEARED  serialized: ['t', ['((cos(($t * 360)) - 1) * 10.0)',
                               '(sin(($t * 360)) * 10.0)',
                               '0']]

    theta=     0  max|R - I| = 0.0e+00   carried point [10. 0. 0.]
    theta=    17  max|R - I| = 0.0e+00   delta 0.000e+00 mm
    theta=    90  max|R - I| = 0.0e+00   delta 1.164e-15 mm
    theta= 213.5  max|R - I| = 0.0e+00   delta 0.000e+00 mm

Identical to `design.md` §6 in every particular, including the honest
`-9.999999999999998`, except that the probe there bound `$t * 360.0` and
this one bound `$t * 360`: the design's prototype multiplied by a float
and this one by an int, which is the binding expression, not the joint.
No other difference to report.

## 8. Pixels (task 6.4)

`evidence/carried.py` beside this file — a disk carried round a post by an
`Orbit` (lower) beside an identical disk turned about the same line by a
`Revolute` (upper), each carrying an arm that points +x at rest, rendered
with `solid snapshot`.

(the four PNGs are beside this file; the fixture is rendered with
`solid snapshot carried.py:Machine --set angle=<deg> [--set
spin_angle=<deg>] --viewall`)

    orbit-0.png    both arms point +x, both disks at the same station
    orbit-60.png   the carried disk has travelled 60 deg; its arm still
                   points +x. The revolute disk's arm has swung with it
    orbit-150.png  the carried disk is now on the far side of the post,
                   arm still pointing +x, straight at the post. The
                   revolute disk's arm points away, up and left
    orbit-240.png  same again, the two disks unmistakably different
    orbit-150-spin-90.png  spin=90 and orbit=150 on the carried disk:
                   its arm has turned a quarter turn about its OWN
                   centre while that centre travelled the circle -- the
                   spin innermost, the orbit outside it

Looked at, all five. The carried body travels without turning, and the
composition of a spin inside an orbit is what the eye sees.

## 9. The open questions (task 7)

**7.1 — the declaration order the projects wrote.** Confirmed, without
editing anything, that the corrected order (rotation innermost, so
declared FIRST) is what each project's algebra needs, and that three
listings must be transposed at stage B:

| Project | Site | What it lists |
|---|---|---|
| OpenCycloid | `openspec/changes/move-onto-motion/proposal.md` lines 247-248 | `orbit` "outer, declared first", `spin` "inner, declared second" — the pre-ADR-093 assumption, exactly inverted |
| Internal-Cycloidal-Actuator | same file, lines 206-207 (its preferred form; the table rows 55-58 list the same order) | `orbit` then `spin`. Its fallback form at lines 215-216 already lists `spin` then `orbit`, which is the right order |
| v8-engine | `docs/move-onto-motion.md` lines 297-298 | `orbit` then `swing`, with prose "with `swing` composed INSIDE `orbit`" — so the prose is right and the listing is not |

YouCanBuildDog has one joint per carried body and no order to correct.
`design.md` §7 states all four in the corrected order.

**7.2 — the V8's `at`.** Confirmed. `CylinderUnit`'s own docstring
(`v8_engine/cylinders/cylinder_unit.py`): "the cylinder axis is local Z,
the crank axis is local X through the origin". So `at` may keep its
default, and `carries=(0, 0, CRANK_RADIUS)` is the crank pin at top dead
centre — `solid_node.mechanisms.crank_pin(θ, R) = (−R sin θ, R cos θ)` in
(y, z) is exactly `R(θ, +X)·(0, 0, R)`, so the orbit is 1:1 with the
crank with no phase term. `design.md` §7's acceptance sentence is
correct as written.

**7.3 — the export target.** Left open, carried by `design.md`'s open
questions. Not closed here.

## 10. Not done, deliberately

- `openspec/specs/joints/spec.md` is NOT synced and the change is NOT
  archived: task 4.7 assigns both to whoever reviews this. The note there
  stands — the four MODIFIED requirement blocks carry every existing
  scenario heading verbatim and only add.
- `libresolid-studio/docs/motion-general-refactor.md` is shop material in
  another repository and was not touched (task 5.3). What it needs: the
  `deferred` rows for OpenCycloid, YouCanBuildDog and v8-engine should
  record that the orbit blocker is lifted by ADR-094, that YouCanBuildDog
  now waits on nothing, that OpenCycloid still waits on the `.repeat()`
  relation fan-out, and that the v8-engine still waits on the
  own-placed-origin anchor for its four timing gears.
- No git write command was run. The implementation is uncommitted in the
  worktree.
