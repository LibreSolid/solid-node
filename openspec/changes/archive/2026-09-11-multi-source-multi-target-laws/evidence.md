# Evidence: several coordinates at one end of one relation

Base for this cycle: this branch (`motion-catalogue-2`) at the planning
commit `9d5947b`, cycle 4 (`whole-tree-fixpoint`, ADR-099) already on it.
Never the primary checkout. Worked entirely in
`/home/asa/devel/libresolid-studio/solid-node/WTs/motion-catalogue-2`
with `PYTHONPATH="$PWD"` and
`/home/asa/devel/libresolid-studio/.venv/bin/python`.

## 0. Before anything

- 0.1 confirmed: `python -c "import solid_node; print(solid_node.__file__)"`
  printed the worktree path.
- 0.2 confirmed: cycle 1 (`repeat-fan-out`, ADR-096) is on the branch;
  cycle 4 (`whole-tree-fixpoint`) is IMPLEMENTED AND ARCHIVED
  (`openspec/changes/archive/2026-09-11-whole-tree-fixpoint/`).
- 0.3 full suite at the base (before this cycle's code changes, cycles
  1-4 already applied):

  ```
  .venv/bin/python -m pytest -x -q
  2199 passed, 16 skipped, 50 warnings, 804 subtests passed in 291.82s
  ```

- 0.4 re-ran both probes; output unchanged from the proposal/design:

  `evidence/probe_today.py`:
  ```
  (a, b).drives(...): AttributeError: 'tuple' object has no attribute 'drives'
  tuple has drives: False
  patching tuple: TypeError cannot set 'drives' attribute of immutable type 'tuple'
  a.drives((b, c), law=...): TypeError: (<path one.turn>, <path two.turn>) is not a coordinate, so it cannot be the driven end of a relation. An end is a port, a joint, a child declaration, a path through one, a derived coordinate or a Driver.
  (a & b).drives(...): TypeError: unsupported operand type(s) for &: 'SignalPort' and 'SignalPort'
  a free `drives` inside a body that declares one: TypeError: 'list' object is not callable
  law calls at realization: [('law called with', 'OneToOne', 'Leaf')]
  & is unused on every declaration kind that carries drives: nothing printed above
  ```

  `evidence/probe_returns.py`:
  ```
  float: len? False  iter? False  getitem? False  type=float
  int: len? False  iter? False  getitem? False  type=int
  symbolic: len? False  iter? False  getitem? False  type=OpenSCADConstant
  the slot after one run: (1.0, 2.0, 3.0, 4.0)
  the operations it produced: ['Rotation(1.0, 2.0, 3.0, 4.0)']
  ```

  Neither changed; proceeded on the ratified design.

- 0.5 `design.md` section 14 open questions, resolved by the content of
  the ratified planning commit itself (the delta spec under
  `specs/couplings/spec.md`, committed at 9d5947b, already states the
  chosen resolution in normative language — there was no separate
  orchestrating session to ask mid-implementation in this run, so the
  committed spec text is read as the ratified answer):
  1. **Law argument shape (proposal b):** SHAPED (owner, or tuple of
     owners), not positional-per-end — the spec text states this
     directly ("An end naming ONE coordinate SHALL be handed as the
     realized node... an end naming SEVERAL SHALL be handed as the
     TUPLE of their owners").
  2. **Coordinate on both sides of a ONE-to-one relation (proposal c):**
     NOT widened — the spec's refusal is scoped to "a relation whose
     ends name several coordinates", matching "not taken" in the design.
  3. Naming a group in a class body: untouched, as the design left it.
  4. `&` on the driven side as well as the tuple: both kept, per the
     spec text ("`&` applied to either side").
  5. Binding a subset from a multi-target law: not offered; unchanged.

  Also confirmed per the pilot's own instruction for this run: the
  source-side spelling is `(a & b).drives(...)`, a plain tuple on the
  source side is refused by name (Python-level: tuple has no `.drives`),
  and the driven side may be a tuple — exactly what `design.md` section 2
  and the spec already state.

## 1-4. Red first

**Every new test in the new section
"1.3c Several coordinates at one end" (`GroupStatementTest`,
`GroupRefusalTest`, `LawShapeTest`, `GroupSolverTest`, `GroupFanOutTest`,
40 test methods, some with subTests) was run BEFORE any implementation
change and observed red**, except the one explicit compatibility case
task 2.2 asks to already be green
(`LawShapeTest.test_a_one_to_one_law_still_receives_two_nodes`, the
unchanged one-to-one law path).

```
.venv/bin/python -m pytest tests/test_couplings.py \
  -k "GroupStatementTest or GroupRefusalTest or LawShapeTest or GroupSolverTest or GroupFanOutTest" -q
39 failed, 4 passed, 135 deselected in 3.10s
```

The 4 "passed" are `test_a_one_to_one_law_still_receives_two_nodes`
(intentionally green, task 2.2) plus three subTest-parametrized methods
that pytest's outer-test bookkeeping reports as "passed" while every one
of their subTests is independently listed as `SUBFAILED` in the same run
(`test_ampersand_over_a_non_coordinate_is_refused`,
`test_an_empty_group_and_a_group_of_one_are_refused`,
`test_ratio_or_offset_with_a_group_is_refused` — 6 SUBFAILED entries
total, all before any implementation change). Full red list:

```
FAILED GroupStatementTest::test_a_group_of_sources_drives_one_coordinate
FAILED GroupStatementTest::test_a_tuple_of_driven_ends_and_an_ampersand_state_one_relation
FAILED GroupStatementTest::test_ampersand_chains_flat_not_nested
FAILED GroupRefusalTest::test_a_coordinate_on_both_sides_of_a_group_relation_is_refused
FAILED GroupRefusalTest::test_a_driven_group_mixing_a_broadcast_with_a_plain_end
FAILED GroupRefusalTest::test_a_driven_group_over_two_different_repeats_is_refused
FAILED GroupRefusalTest::test_a_group_as_a_term_of_a_formula_is_refused
FAILED GroupRefusalTest::test_a_group_with_no_law_is_refused
FAILED GroupRefusalTest::test_a_nested_group_is_refused
FAILED GroupRefusalTest::test_a_repeated_coordinate_in_one_group_is_refused
FAILED GroupRefusalTest::test_a_repeated_source_inside_a_group_is_refused
SUBFAILED GroupRefusalTest::test_ampersand_over_a_non_coordinate_is_refused (number_form, text_form)
SUBFAILED GroupRefusalTest::test_an_empty_group_and_a_group_of_one_are_refused (empty_form, one_form)
FAILED GroupRefusalTest::test_existing_per_member_refusals_are_reached_inside_a_group
SUBFAILED GroupRefusalTest::test_ratio_or_offset_with_a_group_is_refused (ratio_form, offset_form)
FAILED GroupRefusalTest::test_the_missing_parentheses_are_named
FAILED LawShapeTest::test_a_single_driven_end_returns_a_bare_value_symbolic_too
FAILED LawShapeTest::test_a_wrong_return_shape_is_refused_by_name
FAILED LawShapeTest::test_forward_spreads_sources_and_returns_in_written_order
FAILED LawShapeTest::test_mixed_arities_hand_a_tuple_and_a_node_each_way
FAILED LawShapeTest::test_no_new_error_kind
FAILED LawShapeTest::test_the_law_is_handed_two_tuples_once_at_realization
FAILED GroupSolverTest::test_a_group_relation_is_never_inverted
FAILED GroupSolverTest::test_a_relation_of_several_ends_defers_to_the_whole_tree_fixpoint
FAILED GroupSolverTest::test_claim_before_bind_leaves_the_other_three_untouched
FAILED GroupSolverTest::test_forward_once_when_the_last_source_is_bound
FAILED GroupSolverTest::test_order_is_unchanged_by_the_new_record_shape
FAILED GroupSolverTest::test_symbolic_values_pass_through_a_group
FAILED GroupSolverTest::test_the_second_run_re_solves
FAILED GroupSolverTest::test_the_unreached_message_names_the_unbound_source
FAILED GroupFanOutTest::test_a_doubly_bound_copy_is_refused_naming_that_copy_alone
FAILED GroupFanOutTest::test_a_zero_count_repeat_with_several_driven_ends_is_zero_records
FAILED GroupFanOutTest::test_copy_is_the_node_the_repeat_realized_not_a_further_descendant
FAILED GroupFanOutTest::test_several_sources_one_driven_end_over_a_repeat
FAILED GroupFanOutTest::test_six_copies_four_ends_six_law_calls
FAILED GroupFanOutTest::test_the_named_relation_reads_as_six_records_in_copy_order
```

## 5. Implementation, then green

After implementing (see report for the file list), the same selection:

```
.venv/bin/python -m pytest tests/test_couplings.py \
  -k "GroupStatementTest or GroupRefusalTest or LawShapeTest or GroupSolverTest or GroupFanOutTest" -q
37 passed, 135 deselected, 58 subtests passed
```

(37 test methods rather than 40+4 lines above because several red
FAILED lines were subTest-parametrized forms of the SAME method,
counted together here.)

Full `tests/test_couplings.py`:

```
172 passed, 163 subtests passed in 5.65s
```

Related files unaffected by the change (regression check):

```
.venv/bin/python -m pytest tests/test_joints.py tests/test_ports.py \
  tests/test_declarative_nodes.py tests/test_kinematics.py -q
264 passed, 7 warnings, 292 subtests passed in 8.80s
```

## 6. Nothing that is not rewritten moves

### 6.1 Full framework suite

Base (task 0.3, repeated here for the delta):
```
2199 passed, 16 skipped, 50 warnings, 804 subtests passed in 291.82s
```

Head (after implementation):
```
.venv/bin/python -m pytest -x -q
2236 passed, 16 skipped, 50 warnings, 862 subtests passed in 290.16s
```

Delta: +37 passed, +58 subtests passed — exactly the new section's own
tests (37 test methods, 58 subTest invocations across the
subTest-parametrized ones). No newly red test, no skip count change.

### 6.2 Pose comparison over every project on the motion layer

**Amended per this run's instructions:** each project's source was taken
ONCE as `git -C <project> archive HEAD | tar -x` into
`/tmp/.../scratchpad/projects/<name>`, never a live working tree. Base
framework = `git archive 9d5947b` of this worktree (the planning commit,
before this cycle's code) into `scratchpad/base-framework`; head
framework = this worktree as edited. **Both captures for one project ran
from the SAME snapshot.** Full commands and output are in
`scratchpad/run_pose_comparisons.sh` and
`scratchpad/pose_comparison_results.tsv` (session-local, referenced here
by content).

Project list: the 23 "done" rows of
`libresolid-studio/docs/motion-general-refactor.md` (current list, more
than the 19 the change's own text estimated). One model per project
(poseidon: all three of its declared models).

| Project | Model | Result | Snapshot commit |
|---|---|---|---|
| open_manipulator | OpenManipulatorX | max deviation 0.000e+00, 15 poses | 2cbe6db |
| OpenCycloid | OpenCycloid | max deviation 0.000e+00, 7 poses | c4bc344 |
| poseidon | PoseidonPump | max deviation 0.000e+00, 7 poses | 40ea6bb |
| poseidon | PoseidonMicroscope | max deviation 0.000e+00, 4 poses | 40ea6bb |
| poseidon | PoseidonSystem | max deviation 0.000e+00, 11 poses | 40ea6bb |
| OpenTorque-Actuator | OpenTorqueActuator | max deviation 0.000e+00, 7 poses | ad0230b |
| BCN3D-Moveo | Moveo | **CAPTURE_ERROR** (see below) | 6e682fc |
| openarm | OpenArm | **CAPTURE_ERROR** (see below) | 36560d1 |
| HACKberry | Hackberry | max deviation 0.000e+00, 17 poses | b289c58 |
| hexapod_spiderbot_model | Spiderbot | max deviation 0.000e+00, 21 poses | ba91967 |
| abacus | Abacus | max deviation 0.000e+00, 11 poses | 1d4cb0e |
| YouCanBuildDog | Dog | max deviation 0.000e+00, 17 poses | 334e7a4 |
| openvmp | Don1 | **CAPTURE_ERROR** (see below) | 88f6195 |
| pascaline | Pascaline | max deviation 0.000e+00, 27 poses | f9e7e3f |
| Internal-Cycloidal-Actuator | Actuator | **CAPTURE_ERROR** (see below) | 24b7e56 |
| hangprinter | Hangprinter | max deviation 0.000e+00, 11 poses | f43172f |
| AlbertPro | Albert | max deviation 0.000e+00, 13 poses | a12cd07 |
| snappy-reprap | SnappyReprap | max deviation 0.000e+00, 11 poses | 69856fc |
| Prusa3-vanilla | PrusaI3 | max deviation 0.000e+00, 13 poses | a9e61ee |
| openflexure-microscope | Microscope | max deviation 0.000e+00, 11 poses | cf875bd |
| Inmoov-sim | Forearm | max deviation 0.000e+00, 17 poses | d6b177e |
| v8-engine | Engine | max deviation 0.000e+00, 4 poses | a25b074 |
| Metamaquina2 | Metamaquina2 | max deviation 0.000e+00, 11 poses | b77d67c |
| science-jubilee | Jubilee | max deviation 0.000e+00, 11 poses | 1fde9ff |
| open_robot_actuator_hardware | ActuatorModuleV1 | max deviation 0.000e+00, 7 poses | d9e3863 |

**21 of 25 captures: max deviation 0.000e+00.** The remaining 4
(BCN3D-Moveo, openarm, openvmp, Internal-Cycloidal-Actuator) failed
identically at BOTH base and head with `FileNotFoundError`/
`ValueError: string is not a file` for a vendored mesh or STEP source
(`.vendor/...stl`, `...vendor/*.stp` extracted from a project-local zip)
that is untracked or gitignored in the project's own repository — `git
archive HEAD` does not include it. This is a snapshot-methodology gap,
not a framework regression: the SAME missing file is the error on both
sides of the comparison, for every one of the four. Structural blind
spot, honestly reported: these four projects' pose equivalence under
this cycle is UNMEASURED, not measured-and-passing.

### 6.3 Cost

```
tests/test_couplings.py tests/test_kinematics.py, 3 runs each:
  base (9d5947b, 141 tests/107 subtests):  4.26s / 4.14s / 4.34s (pytest-internal)
  head (178 tests/165 subtests):           4.86s / 5.06s / 4.53s (pytest-internal)
```
Per-test cost: base ~30ms/test, head ~27ms/test — no regression; the
added wall time is the added coverage (+37 tests, +58 subtests), not a
per-test slowdown.

`capture_poses.py` on kossel (`simulation.kossel:Kossel`, unmodified
project, `git archive HEAD` snapshot), one run each (not three, given
CAD-render cost):
```
base framework: 7.18s, 11 poses, 378 leaves
head framework: 7.03s, 11 poses, 378 leaves
```
No regression (within run-to-run noise).

3DPrintedClocks wall_clock_01 timing: **not obtained.** Its `git archive
HEAD` snapshot fails to render even against the BASE framework
(`PrematureRead: movement.train.centre.turn was read by Movement's own
simulate() ... before the relation ... bound it`) — a pre-existing
mismatch between the project's last COMMITTED state and this framework
version, unrelated to this cycle (it fails identically with no cycle
code involved). Consistent with this run's own briefing note that
3DPrintedClocks carries uncommitted local work; kossel's timing above
stands in as the CAD-cost proxy for a comparably sized project.

## 7. The four sentences, on read-only overlays

Every overlay: `git -C <project> archive HEAD` into a scratch directory
OUTSIDE the project's repository, edited there, captured against the
HEAD framework, compared against the SAME project's unmodified snapshot
(also `git archive HEAD`, into a separate scratch directory) captured
against the SAME HEAD framework. `git status --short` in every project
confirmed clean afterward (task 7.5) — only pre-existing untracked
scratch files (`screenshot.png`, `_shots.py`) were present, none created
by this session.

| Overlay | Model | Result |
|---|---|---|
| kossel (7.1) | `simulation.kossel:Kossel` | **max deviation 0.000e+00, 11 poses, 378 leaves** |
| Pascaline (7.2) | `pascaline.pascaline:Pascaline` | **max deviation 0.000e+00, 27 poses, 35 leaves** |
| OpenFlexure (7.3) | `simulation.microscope.microscope:Microscope` | **max deviation 0.000e+00, 11 poses, 113 leaves** |
| InMoov Hand (7.4) | `Inmoov_sim.hand:Hand` | **max deviation 0.000e+00, 15 poses, 53 leaves** |

Every leaf count matches its unmodified twin exactly (378/378, 35/35,
113/113, 53/53), confirming the overlay changed no structure, only how
the same pose is stated.

## 8. Re-measurement of the four snapshot-blocked projects (2026-09-11)

The four projects that `git archive` could not capture in §6.2
(BCN3D-Moveo, openarm, openvmp, Internal-Cycloidal-Actuator) carry
vendored meshes or STEP sources that are untracked or gitignored, so a
tar snapshot of their tree is missing files their models need. Measured
instead read-only, in place, from each project's own working tree (all
four confirmed clean by `git status --short` before and after every
capture — no repository write of any kind was made).

Framework commits compared:

- **before** = `9914a2e` (the commit immediately preceding this cycle),
  materialized with `git -C solid-node archive 9914a2e | tar -x` into a
  scratch directory outside any repository, run with
  `PYTHONPATH=.:<scratch>/base` from each project root.
- **after** = `c83207f` (this cycle's tip, `main`), run with
  `PYTHONPATH=.` against the workspace venv's editable install, which
  resolves to the `solid-node` primary checkout at that same commit.

For each project's declared model, `capture_poses.py capture` was run
once against each framework commit, then `compare`d against each other,
and the **after** capture was also compared against this campaign's own
pre-cycle reference capture (`.../scratchpad/before2/<project>-<model>-before.json`,
taken 2026-09-10 before cycle 5 began).

| Project | Model | Poses | before(9914a2e) vs after(c83207f) | after(c83207f) vs pre-campaign reference |
|---|---|---|---|---|
| BCN3D-Moveo | `simulation.moveo:Moveo` | 17 | max deviation 0.000e+00 | max deviation 0.000e+00 |
| openarm | `simulation.openarm:OpenArm` | 21 | max deviation 0.000e+00 | max deviation 0.000e+00 |
| openvmp | `simulation.don1.robot:Don1` | 53 | max deviation 0.000e+00 | max deviation 0.000e+00 |
| Internal-Cycloidal-Actuator | `simulation.actuator.machine:Actuator` | 7 | max deviation 0.000e+00 | max deviation 0.000e+00 |

No nonzero entry, no missing pose, no missing node, and no changed leaf
count appeared in any of the eight comparisons. This closes the
structural blind spot left open in §6.2: all four projects' pose
equivalence under this cycle is now measured, not merely presumed from
the identical pre-existing capture failure on both sides — and the
result is the same as every other project in this campaign: zero
deviation.
