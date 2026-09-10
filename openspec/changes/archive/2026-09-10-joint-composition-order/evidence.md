# Evidence: `joint-composition-order`

Implementation evidence for the ratified change. Worktree
`solid-node/WTs/composed-joints`, branch `composed-joints`, base
`92f4292`, planning commit `a09bec0`. Every run used the workspace venv
`/home/asa/devel/libresolid-studio/.venv/bin/python` with
`PYTHONPATH="$PWD"` from the worktree, verified once per session:

    $ PYTHONPATH="$PWD" python -c "import solid_node; print(solid_node.__file__)"
    /home/asa/devel/libresolid-studio/solid-node/WTs/composed-joints/solid_node/__init__.py

Raw pytest output for the red runs is kept beside this file in
`evidence/red-new-cases.txt` and `evidence/red-modified-cases.txt`.

## 1. The suite before the change

    $ PYTHONPATH="$PWD" python -m pytest -q
    2003 passed, 16 skipped, 49 warnings, 509 subtests passed in 321.26s

No failures at the base. There is therefore no pre-existing failure to
account for in this cycle.

## 2. Red first

Every case below was written against the UNCHANGED source and run before
task 2 began. `tests/test_joints.py::CompositionOrderTest` ran
**9 failed, 1 passed** — the one pass being 1.1's fixture guard, which is
green by design (it asserts the fixture's two joints do not commute, so a
fixture that stopped exercising the question fails loudly). The three
modified cases in `MotionDisciplineTest` ran **3 failed, 7 passed**.

| Task | Test | Recorded failure before the change |
|---|---|---|
| 1.1 | `test_the_fixture_joints_do_not_commute` | GREEN by design: the fixture guard. `T_slide·R_pivot ≠ R_pivot·T_slide` for `pivot = Revolute(axis=(0,0,1), at=(0,30,0))` and `slide = Prismatic(axis=(0,1,0))`. |
| 1.2 | `test_two_joints_compose_in_declaration_order_either_way_round` | `AssertionError: Lists differ: [['t', ['0','-30.0','4.0']], ['r','35',[0,0,1]], …] != [['t', ['0','12','0']], ['t', ['0','-30.0','4.0']], …]` — the slide-first bench put the slide innermost. |
| 1.3 | `test_relation_bound_joints_ignore_the_solve_order` | `AssertionError: Lists differ` — the swapped machine (`orbit` relation stated first) composed `['t','r','t']` for the orbit before the spin's run; the two relation statements decided the pose. |
| 1.4 | `test_re_binding_one_joint_of_several_keeps_its_place` | `AssertionError: Lists differ: ['t','t','r','t','t'] != ['t','r','t','t','t']` — re-binding the pivot moved its run outside the slide. |
| 1.5 | `test_inherited_joints_compose_inside_a_subclasss_own` | `assert_allclose` mismatch on the composed matrix: bound `c, b, a`, the node composed `a ∘ b ∘ c`. `list(declared_joints(ThreeSub)) == ['a','b','c']` was already green — asserted here so a later refactor of the enumerator cannot silently change geometry. |
| 1.6 | `test_a_reversed_application_order_across_a_sweep_changes_nothing` | `AssertionError: Lists differ: [['t',['0','12','0']], ['t',['0','-30.0','4.0']], …] != [['t',['0','-30.0','4.0']], …]` — the second walk, with the binding order reversed by the `order` driver, produced `[slide, pivot]` where the first produced `[pivot, slide]`. |
| 1.7 | `test_two_animators_on_one_node_keep_the_declared_order` | `AssertionError: Lists differ: ['t','t','r','t','t'] != ['t','r','t','t','t']` on the THIRD walk — after A's sweep and re-bind, A's joint landed outside B's. |
| 1.8 | `test_a_three_operation_joint_is_one_unbroken_run_at_its_slot` | `AssertionError: Lists differ: ['t','r','t','r','t','r','t','t','t'] != ['t','t','r','t','t','r','t','r','t']` — the hand-written rotation sat BETWEEN the twist's run and the swing's. |
| 1.9 | `test_hand_written_motion_sits_outside_the_whole_joint_block` | `AssertionError: Lists differ: ['r','t','r','t','t','t'] != ['t','r','t','r','t','t']` — the hand-written rotation applied first composed innermost. |
| 1.10a | `MotionDisciplineTest::test_joint_motion_is_innermost_and_tagged` (MODIFIED) | `AssertionError: Lists differ: ['r','t','r','t','t'] != ['t','r','t','r','t']`. |
| 1.10b | `MotionDisciplineTest::test_the_joint_block_is_innermost_of_hand_written_motion` (MODIFIED + renamed from `test_hand_written_and_joint_motion_coexist_in_order`) | `AssertionError: Lists differ: ['10','25'] != ['25','10']`. |
| 1.10c | `MotionDisciplineTest::test_re_simulating_leaves_one_motion` (MODIFIED, not named by the tasks) | `AssertionError: ['0','-10.0','4.0'] != '40'` — the joint's rotation moved from index 2 to index 1 because the joint run is now the innermost thing on the node. See §6. |
| 1.11 | `test_the_published_document_reads_innermost_first` | `AssertionError: Lists differ: ['r','t','r','t','t','t'] != ['t','r','t','r','t','t']` in `serialize_node`'s published operations. The "no new key" half was green before and after: the document key set is unchanged. |

## 3. The seam as implemented

`solid_node/node/base.py`

    def apply_joint_motion(node, operations, slot):
        index = 0
        for existing in node.operations:
            if not getattr(existing, '_motion', False):
                break
            existing_slot = getattr(existing, '_joint_slot', None)
            if existing_slot is None or existing_slot > slot:
                break
            index += 1
        phase = _phase.current()
        for offset, operation in enumerate(operations):
            operation._motion = True
            operation._joint_slot = slot
            node.operations.insert(index + offset, operation)
            if phase is not None:
                _tag_operation(node, operation, phase)
        return operations

**The insertion rule, in one sentence:** a joint's whole placement run is
inserted at the length of the prefix of `node.operations` whose entries
are motion, carry a `_joint_slot`, and whose slot is `<= slot` — after
every joint of an earlier-or-equal slot, before the first joint of a
later slot, before every hand-written motion, before every rest
operation.

`solid_node/motion/joints.py::Joint.place` computes
`slot = list(declared_joints(type(node))).index(self.name)` off the
enumerator's existing per-class cache (no second cache) and calls the
seam once with the whole `placement(...)` list. `Joint.clear` is
unchanged. `_insert_motion` is unchanged and is now documented as the
HAND-WRITTEN motion path. `apply_motion` no longer exists; its only
caller was `Joint.place`, it was exported from no public module and
appears in no export test. The only remaining occurrences of the old
name in the tree are historical: `docs/adrs/NODE/ADR-088` (an ADR records
a decision at its date) and the pre-cycle plan note.

## 4. The suite after the change

    $ PYTHONPATH="$PWD" python -m pytest -q
    2013 passed, 16 skipped, 49 warnings, 513 subtests passed in 306.47s

Ten new tests, four new subtests, no failures, no skips gained or lost.
`tests/test_couplings.py`, `tests/test_animator_tag.py`,
`tests/test_simulate_split.py` and `tests/test_ports.py` were run
separately and are green with NO edits: `108 passed, 3 warnings,
57 subtests passed`.

## 5. The catalogue's poses do not move (task 5)

The acceptance of the whole cycle. Every capture was taken with
`libresolid-studio/docs/motion-general-refactor/capture_poses.py`, run
from the project root with the workspace venv, **sequentially, never in
parallel**, and each run printed and recorded its `solid_node.__file__`
under the exact `PYTHONPATH` used for that half:

- **BEFORE**: `PYTHONPATH=.` — the venv's editable install, which
  resolves to the PRIMARY checkout
  `/home/asa/devel/libresolid-studio/solid-node/solid_node/__init__.py`.
  That checkout was verified at **92f4292** (this cycle's recorded base)
  with no modified tracked file before the run started, and nothing was
  written to it.
- **AFTER**: `PYTHONPATH=.:/home/asa/devel/libresolid-studio/solid-node/WTs/composed-joints`
  so the worktree shadows the editable install, verified as
  `.../WTs/composed-joints/solid_node/__init__.py`.

The verification line was taken on every one of the 66 capture runs and
every one printed the expected tree; the column below records that.

| Project (commit, branch) | Model | Poses | Leaves | Max deviation | `solid_node.__file__` before / after |
|---|---|---:|---:|---|---|
| `Robotic-Arms/open_manipulator` (394b6ef, main) | `simulation.open_manipulator_x:OpenManipulatorX` | 15 | 43 | `0.000e+00` | primary / worktree ✔ |
| `Lab-Equipment/poseidon` (d790e6d, release) | `simulation.pump:PoseidonPump` | 7 | 14 | `0.000e+00` | primary / worktree ✔ |
| " | `simulation.microscope:PoseidonMicroscope` | 4 | 7 | `0.000e+00` | primary / worktree ✔ |
| " | `simulation.poseidon:PoseidonSystem` | 11 | 49 | `0.000e+00` | primary / worktree ✔ |
| `Actuators/OpenTorque-Actuator` (1119ed7, master) | `simulation.actuator:OpenTorqueActuator` | 7 | 23 | `0.000e+00` | primary / worktree ✔ |
| " | `simulation.actuator:ActuatorPosePreview` | 7 | 23 | `0.000e+00` | primary / worktree ✔ |
| " | `simulation.output_stack:OutputStackPreview` | 4 | 10 | `0.000e+00` | primary / worktree ✔ |
| " | `simulation.reducer:ReducerPreview` | 7 | 10 | `0.000e+00` | primary / worktree ✔ |
| " | `simulation.reducer:ReducerPosePreview` | 4 | 10 | `0.000e+00` | primary / worktree ✔ |
| `Robotic-Arms/BCN3D-Moveo` (a3b1aaf, master) | `simulation.moveo:Moveo` | 17 | 8 | `0.000e+00` | primary / worktree ✔ |
| `Robotic-Arms/openarm` (8e62dc2, main) | `simulation.openarm:OpenArm` | 21 | 21 | `0.000e+00` | primary / worktree ✔ |
| " | `simulation.arm:ArmsAtRest` | 4 | 20 | `0.000e+00` | primary / worktree ✔ |
| " | `simulation.gripper:GrippersAtThirtyDegrees` | 4 | 6 | `0.000e+00` | primary / worktree ✔ |
| `Robotic-Hands/HACKberry` (e24765d, master) | `simulation.hackberry:Hackberry` | 17 | 58 | `0.000e+00` | primary / worktree ✔ |
| `Robots/openvmp` (f193ab6, main) | `simulation.don1.robot:Don1` | 53 | 499 | `0.000e+00` | primary / worktree ✔ |
| `Vibecoded-demos/pascaline` (4ab92da, main) | `pascaline.pascaline:Pascaline` | 27 | 35 | `0.000e+00` | primary / worktree ✔ |
| " | `pascaline.digit:Digit` | — | — | **not capturable** (identical failure before and after) | primary / worktree ✔ |
| `3D-Printers/hangprinter` (10873b5, version_4) | `simulation.hangprinter:Hangprinter` | 11 | 149 | `0.000e+00` | primary / worktree ✔ |
| " | `simulation.winch:WinchABC` | 4 | 12 | `0.000e+00` | primary / worktree ✔ |
| `Robots/AlbertPro` (50a9dc5, main) | `simulation.albert:Albert` | 13 | 66 | `0.000e+00` | primary / worktree ✔ |
| " | `simulation.leg:LegBench` | 9 | 4 | `0.000e+00` | primary / worktree ✔ |
| " | `simulation.trunk:Trunk` | 4 | 2 | `0.000e+00` | primary / worktree ✔ |
| `3D-Printers/snappy-reprap` (2e69ad5, master) | `simulation.snappy_reprap:SnappyReprap` | 11 | 170 | `0.000e+00` | primary / worktree ✔ |
| `3D-Printers/Prusa3-vanilla` (f54fc4d, master) | `simulation.prusa_i3:PrusaI3` | 13 | 216 | `0.000e+00` | primary / worktree ✔ |
| " | `simulation.xaxis:XAxis` | 4 | 56 | `0.000e+00` | primary / worktree ✔ |
| " | `simulation.yaxis:YAxis` | 4 | 50 | `0.000e+00` | primary / worktree ✔ |
| " | `simulation.extruder:Extruder` | 4 | 26 | `0.000e+00` | primary / worktree ✔ |
| " | `simulation.frame:Frame` | 4 | 91 | `0.000e+00` | primary / worktree ✔ |
| `Lab-Equipment/openflexure-microscope` (6967b214, simulation) | `simulation.microscope.microscope:Microscope` | 11 | 113 | `0.000e+00` | primary / worktree ✔ |
| `3D-Printers/Metamaquina2` (f462ba9, main) | `metamaquina2.metamaquina2:Metamaquina2` | 11 | 452 | `0.000e+00` | primary / worktree ✔ |
| `Lab-Equipment/science-jubilee` (1fde9ff, main) | `simulation.jubilee:Jubilee` | 11 | 35 | `0.000e+00` | primary / worktree ✔ |
| " | `simulation.sonicator.assembly:Sonicator` | 4 | 22 | `0.000e+00` | primary / worktree ✔ |
| `Actuators/open_robot_actuator_hardware` (565e966, master) | `simulation.actuator:ActuatorModuleV1` | 7 | 19 | `0.000e+00` | primary / worktree ✔ |

**Result: maximum deviation `0.000e+00` on every capturable model of all
sixteen migrated projects — 32 models, 334 poses, 2 319 leaf world
matrices, and every bound coordinate the script reads. Not a tolerance:
zero.** The static survey's prediction (no hand-written simulate-phase
motion on a joint-carrying node anywhere in the sixteen) held.

### The one model that could not be captured

`pascaline.digit:Digit` — the standalone `Digit`, which the archived
`move-onto-motion` capture list did not include either — fails with
`TypeError: (36.0 * (20 * $t)) is not a number` from
`_compose_world_matrix`: built standalone, its drum is bound from an
expression in the animation time and the world composition refuses a
non-numeric value. **The failure is identical before and after**, byte
for byte in the traceback, and it is a limit of the capture script on
that model, not a regression. `pascaline.pascaline:Pascaline`, the
declared model, captures 27 poses over 35 leaves at deviation 0.

### What this does NOT cover (task 5.4)

- **The nine deferred projects** (OpenCycloid, hexapod_spiderbot_model,
  abacus, YouCanBuildDog, fender-bender, Internal-Cycloidal-Actuator,
  kossel, Inmoov-sim, v8-engine). They are at stage A and will be
  refactored ONTO this contract, so their poses are stage B's
  acceptance, not this cycle's. Nothing here says their stage-B
  refactors will succeed.
- **Projects whose suite was already red at baseline**, which the
  tracker names: BCN3D-Moveo, abacus, fender-bender, pascaline,
  Prusa3-vanilla, openflexure-microscope, v8-engine. This task compared
  poses, not test verdicts: a project red at baseline is still red, for
  the reasons the tracker records, and none of those reasons is motion
  composition.
- **Test suites.** No project's `solid test` or `pytest` was run in this
  cycle; the evidence here is pose identity plus the framework's own
  suite.
- **Pixels**, which no pose comparison replaces — §7 below.
- **Models not declared and not named in an archived `move-onto-motion`
  record.** The set captured is every declared model of the sixteen plus
  every standalone sub-assembly those records named; a model that exists
  in a project's source but is neither declared nor named there was not
  captured.
- **Coordinates that are not `declared_ports`.** The script compares leaf
  world matrices and every declared port's value; a piece of state that
  is neither is outside its reach.

## 6. Open questions (task 6)

### 6.1 The same-slot survivor — settled, `<=` kept

The design left open whether an operation of the joint being re-bound
can survive both `_sweep` and `Joint.clear`, and therefore whether the
insertion rule should use `<` or `<=`. Two probes, each restoring a
node's operations list between two bindings of one joint, exactly as
`solid_node/manager/test.py::restore_children_checkpoints` does
(`child.operations[:] = list(saved)`, restoring by CONTENT and
resurrecting the old operation objects):

**Probe A — a joint bound under a simulate phase (the runner's own
case).** The stale run does NOT survive:

    after first binding:  [t(-a), r(10), t(a), rest]
    snapshot taken here
    after second binding: [t(-a), r(20), t(a), rest]
    restore:              [t(-a), r(10), t(a), rest]   # r(10) resurrected
    _joint_motion records: the r(20) objects
    after third binding:  [t(-a), r(30), t(a), rest]   # one run, correct
    slots:                [0, 0, 0, None]
    tagged with the bench: [True, True, True, False]

`Joint.clear` misses the resurrected objects — they are not the ones it
recorded — but `_sweep` drops them anyway, by ANIMATOR identity, which is
precisely what its docstring says it exists for. So on the path the
runner actually takes, no same-slot survivor is reachable and `<` and
`<=` cannot be distinguished.

**Probe B — a joint bound OUTSIDE any lifecycle phase** (a test posing a
tree by hand, a script). Here the operations are untagged, so no sweep
touches them, and a survivor IS constructible:

    after restore:  [t(-a), r(10), t(a), t(slide 12), rest]
    after re-bind:  [t(-a), r(10), t(a), t(-a), r(30), t(a), t(slide 12), rest]
    slots:          [0, 0, 0, 0, 0, 0, 1, None]

The node ends up carrying two runs of one joint — its pose is already
wrong from the duplication, and it is wrong under `<` too, which would
only put the fresh run innermost of the stale one instead of outermost.
The decisive argument is compatibility: BEFORE this cycle,
`_insert_motion` appended the fresh run at the end of the motion block,
i.e. AFTER the stale one. `<=` keeps that relative order and keeps all
of one slot's operations adjacent; `<` would reverse it for no gain.
**`<=` is kept, and this is no longer open.** It changes no ratified
behaviour: the spec's promise is that binding one joint twice leaves one
motion "tolerating operations a sweep has already dropped", and a
wholesale list restore that resurrects an untagged operation is outside
what it describes. Not written as a permanent test: it asserts a
double-run outcome that is wrong either way and would pin a bug in
place.

### 6.2 A legacy render inside a joint's frame — no sighting, no finding

**No catalogue project triggers the legacy-render `FutureWarning` at
all**, so none triggers it on a node that declares a joint. Two
independent measurements:

- The 66 pose-capture runs of §5 emitted **zero** `FutureWarning`s
  across the whole log (`grep -c FutureWarning` → 0), and those runs
  render and simulate the sixteen migrated projects at every pose.
- A dedicated probe over **all twenty-five** catalogue projects — the
  sixteen migrated and the nine deferred — constructing each declared
  model, binding every qualified driver to its default, walking the tree
  with `render()` under `warnings.simplefilter('always')`, and reporting
  any `FutureWarning` naming a class together with that class's
  `declared_joints`. Every one of the twenty-five reported `CLEAN`.

There is therefore **no new finding for `workflow/warts.md`**, and the
hazard the design named — a `render()` that read a driver re-running per
binding and appending tagged non-motion operations that `Joint._carry`
would compose into the rest placement it inverts — remains a latent
hazard in the framework with no live sighting. It is recorded in the
design and nowhere else.

### 6.3 Neither open question changed the ratified behaviour

6.1 confirms the rule as ratified (`<=`, and the spec sentence unchanged);
6.2 produced no behaviour at all. The spec delta needs no revision and no
re-ratification.

## 7. Pixels (task 5.5)

`solid snapshot` on two models that carry more than one joint on a body,
before and after, `--time 0.5 --viewall --autocenter --imgsize 1280x960`,
with the same PYTHONPATH discipline as §5:

| Model | Body with several joints | Before | After |
|---|---|---|---|
| `Lab-Equipment/science-jubilee` `simulation.jubilee:Jubilee` | `Toolhead` — `traverse`, `advance`, `lift` | `jubilee.before.png` | `jubilee.after.png` |
| `Vibecoded-demos/pascaline` `pascaline.pascaline:Pascaline` | `Stylus` — `x`, `y`, `lift` | `pascaline.before.png` | `pascaline.after.png` |

Both pairs are **byte-identical** (`md5sum`:
`6e2c4a3bcaf05b3eca03d687434349db` for both jubilee images,
`bcec477c3e62f2be8729d4cd63057bd4` for both pascaline images), so
looking at the two halves is looking at one image each.

What I saw, at
`/tmp/claude-1000/-home-asa-devel-libresolid-studio/51062ef7-4e6c-4bbf-8b75-db00d7533d96/scratchpad/shots/`:

- **Jubilee**: the frame's four uprights standing, the bed lattice flat
  and square below, and the toolhead — the body carrying the three
  prismatics — hanging on its gantry at mid travel with the orange
  plate and the yellow syringe column above it, upright and centred
  over the bed. Nothing skewed, nothing displaced along a single axis,
  which is what a reversed prismatic composition would have shown as a
  translation applied in the wrong frame.
- **Pascaline**: the case closed and square, the nine input dials in a
  row on the lid with their spokes, the carry window strip along the
  top, and the stylus standing vertically in one dial. The stylus is
  the three-prismatic body; it stands where its dial is, at its
  declared height, not offset into the case or hovering above it.

The two chosen bodies carry three PRISMATICS each, which commute — that
is exactly why they were safe under the old rule and why the whole
catalogue moved by zero. Pixels here confirm the change is inert on the
catalogue; they do not exercise a non-commuting stack, which is what
`tests/test_joints.py::CompositionOrderTest` does with a matrix
assertion instead. **No migrated project has a body with two
non-commuting joints** — those are exactly the seven deferred sightings
this cycle unblocks — so there is nothing in the catalogue to
photograph for that case yet. Stage B of the deferred projects is where
that picture gets taken.

## 8. Things the ratified design could not state

- **`tests/test_joints.py::MotionDisciplineTest::test_re_simulating_leaves_one_motion`
  also had to change**, and the tasks named only two existing tests. It
  asserted `operations[2].serialized[1] == '40'`; with the joint run now
  innermost the joint's rotation is at index 1. The assertion's meaning
  is unchanged and the reason is written into the method.
- **`Joint.place` looks its slot up on EVERY binding** —
  `list(declared_joints(type(node))).index(self.name)` builds a list of
  the cached dict's keys and scans it per bind. The design said "a list
  index into the per-class cache — do not add a second cache", and that
  is what is implemented; it is O(number of joints on the class) per
  binding, which for the catalogue's largest class is a handful of
  names. If a profile ever shows it, the fix is a slot cached on the
  `Joint` at `__set_name__` time, which would need the owning class,
  which `__set_name__` has.
- **`declared_joints` returns the live cached dict**, so the slot lookup
  and the ordering contract now depend on no caller mutating it. Nothing
  does today; nothing enforces it either.
- **The pose comparison cannot see a pose no driver reaches.**
  `capture_poses.py` poses each driver at 40%, 100% and 63% of its
  declared range, plus time; a driver with no `range` stays at its
  default in every range-derived pose. A composition error that only
  appears outside those states would not have been caught.
- **The framework suite has no test for a joint on a node whose rest
  placement is a ROTATION composed with another joint's**, because
  `Joint._carry` already excludes motion and that is pinned elsewhere.
  The new fixtures all use translation-only rest placements; the
  rotational carry is covered by the pre-existing `FrameCarryTest`.
- **Nothing here proves the forward-compatibility intent for `Orbit` and
  `Free`.** Task 1.8 pins the part that is testable today — a
  three-operation joint staying one unbroken run at its own slot — and
  that is all. A `Free` owning six coordinates on one slot is asserted
  by the implementation's shape (it orders by joint, not by coordinate)
  and by nothing that runs.
