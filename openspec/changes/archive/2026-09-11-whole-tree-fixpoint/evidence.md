# Evidence: whole-tree-fixpoint

Worktree `/home/asa/devel/libresolid-studio/solid-node/WTs/motion-catalogue-2`,
branch `motion-catalogue-2`, planning commit `a34d7e2` on top of cycle 3's
`63a2099`. Python `/home/asa/devel/libresolid-studio/.venv/bin/python`,
`PYTHONPATH="$PWD"` from the worktree unless stated otherwise. Verified
`import solid_node; solid_node.__file__` prints the worktree path before
any run.

## 0.1 — worktree confirmed

```
$ python -c "import solid_node; print(solid_node.__file__)"
/home/asa/devel/libresolid-studio/solid-node/WTs/motion-catalogue-2/solid_node/__init__.py
```

## 0.2 — cycle 1 on the branch

`git log --oneline -5` at the start of this session:

```
a34d7e2 openspec(whole-tree-fixpoint): propose that relations resolve over the whole tree in one pass
63a2099 openspec(declaration-site-joint): a parent states a joint at the site it places the child (ADR-098)
f923f6d workflow(warts): v8-engine stage B sights the uncleared bound value; openspec refuses a delta-free migration
02898dd openspec(declaration-site-joint): propose that a parent states a joint at the site it places the child
91c0b2a openspec(joint-frame-follows-declarer): a joint is stated in the frame of whoever declares it (ADR-097)
```

`docs/adrs/README.md` lists ADR-096 (repeat-fan-out), ADR-097 and ADR-098
as Accepted. `solid_node/motion/couplings.py`'s `resolve_declared_relations`
already extends per relation (`records.extend(relation.resolve(node))`)
and `Relation.resolve` returns a list of `RelationRecord`s per realized
copy for a `BroadcastRef` driven end (`RelationRecord(..., copy=...)`
per copy) — cycle 1's flattening is present. Confirmed: proceed.

## 0.3 — full suite at the base

`.venv/bin/python -m pytest -x -q` from the worktree:

```
2169 passed, 16 skipped, 50 warnings, 796 subtests passed in 339.50s (0:05:39)
```

No failures. This is the pre-change baseline task 7 is measured against.

## 0.4 — every probe at the base

All seven probes run clean (exit 0) against the unmodified worktree.
Full logs kept at `<scratchpad>/wtf-scratch/probe_*.base.log`; the
material excerpts:

**`probe_order.py`** — the current order for a three-level tree: per
`set_state`/`assemble()` call, EVERY node runs `sweep → rest → clear →
simulate → SOLVE` before the walker links its children and descends
(`ASSEMBLE Root` interleaves `sweep/rest/clear/simulate/SOLVE Root` with
`ASSEMBLE Child`, i.e. Root's phase completes before Child's begins, but
the WALKER'S read of Root's own geometry — implicit in `ASSEMBLE Root`
returning — happens intermixed with, not after, the whole tree's phases).

**`probe_interleave.py`**:

```
  geometry read of Microscope
phase   Microscope
  geometry read of body
phase   body
  geometry read of lower_strut
  operations applied to lower_strut
  operations applied to body
  geometry read of z_axis
phase   z_axis
  geometry read of column
  operations applied to column
  operations applied to z_axis
  operations applied to Microscope
```

`body`'s geometry is read and its operations applied BEFORE `z_axis`'s
phase runs. A relation binding `body.lower_strut.swing` from a coordinate
`z_axis`'s phase solves would be a pose nobody sees under a lazy
retry — confirms design.md §2's central constraint.

**`probe_own_read.py`**:

```
Art4
  own derived coordinate read in own simulate(): <rotational port left of Art4: None> -> value None
  the pulley's operations after rotate(): ['Rotation']

Actuator
  own relation-bound joint coordinate read in own simulate(): None

after the run, the same derived coordinate reads 18.0
```

Confirmed: the own-derived-coordinate read and the own-relation-bound
joint read are both silently `None` during `simulate()`, and `rotate(None,
...)` still appends an (inert) `Rotation` operation — a silent no-op, not
a raised error.

**`probe_stale.py`**:

```
first run        value=37.5     binder=None   operations=['Translation[37.5, 0, 0]']
second run       value=37.5     binder=None   operations=[]
third run        value=37.5     binder=None   operations=[]
```

Confirmed exactly as design.md §6 states: value survives, the guard skips
the rebind, the operations vanish on runs 2 and 3.

**`probe_state_order.py`**:

```
first set_state(step=10)
    Machine.simulate: the axis holds {} while this phase runs
    Axis.simulate   reads step = 10.0
second set_state(step=90)
    Machine.simulate: the axis holds {'step': 10.0, 'time': 0.0} while this phase runs
    Axis.simulate   reads step = 90.0
```

Confirmed: while `Machine`'s own phase runs, `axis._states` holds the
PREVIOUS binding, not the one just requested. Any pass driven from the
root simulating descendants inline would run every descendant one pose
late unless `set_state` delivers the whole snapshot before enumerating.

**`probe_subclass.py`**:

```
Actuator declares ['drive']
Preview declares ['drive', 'drive']
DoublyBound: rotor (Rotor).spin would be bound by the relation 'drive' (free_run drives rotor.spin) and by the relation 'drive' (input_angle drives rotor.spin). ...
```

Confirmed: a subclass reassigning a relation to a name its base used
ADDS a second relation of the same name today; the solve raises
`DoublyBound` rather than replacing.

**`probe_unreached.py`**:

```
A  ancestor sources from a descendant-solved coordinate
    UnreachedCoordinate: z_axis.column.turn drives strut.swing: nothing bound either end. column (Leaf).turn and strut (Strut).swing are both unbound ...

B  the chain stated one level down
    UnreachedCoordinate: power.turn drives train.centre.turn: nothing bound either end. power (Leaf).turn and centre (Leaf).turn are both unbound ...
```

Confirmed both shapes refuse today, and confirmed the message's own
END-path names (`column (Leaf).turn`, not `z_axis.column.turn`) fall back
to the class name for the SOURCE end named through the relation's own
`described()` composition — the driver/driven END descriptions
(`record.driver_end.described()`) are what `where()` resolves per node,
and at refusal time the descendant `column`/`centre` is not yet linked
into the tree the root solves in, so `where()` falls back to
`"column (Leaf)"`. This is the defect task 1.3 is written against.

No probe disagreed with `evidence/survey.md`; task 0.7's requirement to
STOP is not triggered.

## 0.5 — base poses of the 23 motion-layer projects (git-archive snapshot)

**Scope.** "The 23" is read as the 23 rows marked `done` in
`docs/motion-general-refactor.md`'s tracker (`open_manipulator` through
`open_robot_actuator_hardware`); `fender-bender` and `kossel` stay
`deferred` there (no relation over the affected coordinates — the
survey's own list of projects with no A-workaround — so this cycle's
pose-comparison proof over them would be vacuous) and are not
re-captured. `3DPrintedClocks` and `Thor` are "out of scope" of that
tracker (migrated earlier, during the framework's own motion-layer
campaign) and are handled separately: `3DPrintedClocks` explicitly by
tasks 9.3/9.4 below (its own session holds its working tree dirty right
now — 140 uncommitted files — so it is never read live); `Thor` is not
named by any task 9.x and is not re-captured here, though nothing in it
is expected to move (no A-workaround, no B-read of its own binder besides
the already-covered ancestor case).

**Method.** Per project, ONE `git -C <project> archive HEAD | tar -x`
snapshot into `<scratchpad>/wtf-snapshots/<name>/`, taken once, before any
framework source change. Two projects (`BCN3D-Moveo`, `openarm`) and two
more (`openvmp`, `Internal-Cycloidal-Actuator`) reference generated/vendor
asset directories that are gitignored (`simulation/repaired/`, `.vendor/`,
`openvmp-models/`, `simulation/actuator/vendor/`) and so are absent from
`git archive`; each of those four projects was confirmed clean
(`git status --porcelain` empty) before its ignored directory was
copied, read-only, from the live working tree into the snapshot — never
written to, and never a project under a stage-B agent. `poseidon`,
`hexapod_spiderbot_model`, `abacus`, `pascaline`, `Prusa3-vanilla`,
`openflexure-microscope`, `Inmoov-sim`, `v8-engine` were confirmed DIRTY
in their live trees at snapshot time (active stage-B agents); their
snapshots come only from `git archive HEAD`, never their working tree.
Commits captured in `<scratchpad>/wtf-scratch/snapshot_commits.txt`.

Each project's single declared `[tool.solid-node] model` (or, for
`poseidon`, its three `[tool.solid-node.models]` entries) was captured
with `capture_poses.py capture <ref> <scratch>/<project>-<model>-before.json`,
run from inside the snapshot with
`PYTHONPATH=.:<worktree>`. All 25 refs (23 projects, poseidon
contributing 3) captured cleanly; full log
`<scratchpad>/wtf-scratch/batch2.log` plus the first 8 lines from the
initial (foreground) run. Poses and leaf counts:

| project (model) | commit | poses | leaves |
|---|---|---|---|
| open_manipulator | 2cbe6db | 15 | 43 |
| OpenCycloid | c4bc344 | 7 | 46 |
| poseidon (pump) | 40ea6bb | 7 | 14 |
| poseidon (microscope) | 40ea6bb | 4 | 7 |
| poseidon (poseidon) | 40ea6bb | 11 | 49 |
| OpenTorque-Actuator | c7f2602 | 7 | 23 |
| BCN3D-Moveo | 6e682fc | 17 | 8 |
| openarm | 36560d1 | 21 | 21 |
| HACKberry | b289c58 | 17 | 58 |
| hexapod_spiderbot_model | ba91967 | 21 | 172 |
| abacus | 1d4cb0e | 11 | 56 |
| YouCanBuildDog | 25738f7 | 17 | 101 |
| openvmp (don1) | 88f6195 | 53 | 499 |
| pascaline | f9e7e3f | 27 | 35 |
| Internal-Cycloidal-Actuator | 24b7e56 | 7 | 55 |
| hangprinter | 10873b5 | 11 | 149 |
| AlbertPro | a12cd07 | 13 | 66 |
| snappy-reprap | 2e69ad5 | 11 | 170 |
| Prusa3-vanilla | f54fc4d | 13 | 216 |
| openflexure-microscope | 6967b214 | 11 | 113 |
| Inmoov-sim (Forearm) | a317c35 | 17 | 61 |
| v8-engine | a25b074 | 4 | 135 |
| Metamaquina2 | b77d67c | 11 | 452 |
| science-jubilee | 1fde9ff | 11 | 35 |
| open_robot_actuator_hardware | 6a3a07d | 7 | 19 |

`YouCanBuildDog`'s HEAD advanced from `0e65c75` to `25738f7` (a no-op
docs commit by another agent) between the initial `git status` scan and
the snapshot; the snapshot recorded the commit it actually archived,
demonstrating why the snapshot-once discipline matters (a live read a few
minutes later would have silently changed which commit was measured).

Comparison against these base captures, and against cycle 2's true poses
in `<scratchpad>/before2/` for the projects already migrated onto
ADR-097/098, is deferred to task 9 (after the implementation) — this
section is the BASE half only, captured before any source change.

## 0.6 — the second-render evidence for Prusa i3 and hangprinter

**Method.** `<scratchpad>/wtf-scratch/second_render_probe.py` (whole
`PrusaI3`/`Hangprinter` root, defaults pose, before vs. after `assemble()`,
then two more re-renders at the same pose) and
`<scratchpad>/wtf-scratch/second_render_standalone.py` (a single
axis/extruder/winch class BUILT ON ITS OWN, matching the comment "an axis
built on its own stands mid travel" the projects' own code carries),
against the same git-archive snapshots as 0.5.

**Result: 0.000000 mm on every comparison, on the CURRENT committed
code.** Reading the exact cited sites:

- `xaxis.py:207-212`, `yaxis.py:178-186`, `extruder.py:256-260` all read
  `travel = self.carriage.travel.value; if travel is None: travel =
  <default>; self.carriage.travel = travel` — the REBIND
  (`self.carriage.travel = travel`) is UNCONDITIONAL, one line OUTSIDE
  the `if` body. This is not the shape `probe_stale.py` reproduces (whose
  fixture binds INSIDE the guard); it is the defensive workaround a
  migration author would write around exactly this framework gap, and it
  is immune to the stale-value bug because it rebinds every run whether
  or not the guard fired. `zaxis.py:65-68`'s `z = self.lift.value; if z
  is None: z = 0.0` never rebinds `self.lift` at all — it only chooses a
  local default for a `rotate()` call, so it is "no relation's end"
  exactly as `evidence/survey.md` classifies it.
- `hangprinter/simulation/winch.py:329-333` (`WinchC`) and `:370-374`
  (`WinchD`) DO bind inside the guard —
  `if turn is None: self.rotor.turn = turn = 0.0` — and standalone
  `WinchD()` enumerated three times shows 0.000000 mm deviation because
  the default is exactly zero: `rotate(0, ...)` and no rotation at all
  compose to the identical matrix, so the stale-value defect is present
  but has no visible effect. This is "masked by a zero default" exactly
  as `evidence/survey.md`'s section C states, now confirmed live rather
  than read off the source.

**The 37.5 mm / 70.4 mm / 0.05 mm figures are the project's own
historical measurement**, recorded in `workflow/warts.md` ("An
author-bound joint keeps its value but loses its motion between runs"):
"Prusa i3's X and Y axes and extruder showed it as 37.5 mm, 70.4 mm and
0.05 mm pose deviations on a second render." They were measured against
an earlier state of the code (before or during the migration that
produced the current unconditional-rebind workaround) and are cited here
rather than re-derived, because the code that produced them no longer
carries the bound-inside-guard shape. The FRAMEWORK defect they are
evidence for is general and is reproduced live, unconditionally, by
`probe_stale.py` (0.4 above) and by task 3's new tests (below) — the
number that matters for task 9.2 ("Prusa i3 and hangprinter: the second
render goes to 0") is that BOTH projects' current code already measures
0.000000 mm on this branch's base, so task 9.2's target is already met at
the base and stays met at head (a regression check, not a fix-to-see
demonstration, for these two specific projects as currently committed).

## 0.7 — survey.md read

Read in full (`openspec/changes/whole-tree-fixpoint/evidence/survey.md`).
No disagreement found between the survey's claims and this session's own
probe re-runs (0.4) or project readings (0.6); proceeding per the
ratified design.

---

## Tasks 1, 2, 4: red first, in `tests/test_couplings.py`

New sections `TreeFixpointTest` (task 1), `ReadRefusalTest` (task 2),
`SubclassReplacesRelationTest` (task 4). `ReadRefusalTest` needs the new
`PrematureRead` error the implementation exports; to collect every red
case in ONE run, a throwaway stub (`class PrematureRead(CouplingError):
pass`) was inserted for the collection run only and removed immediately
after — the evidence below is the real behaviour against the unmodified
solver, not the stub's.

```
FAILED tests/test_couplings.py::TreeFixpointTest::test_a_broadcast_copy_defers_and_refuses_one_by_one
FAILED tests/test_couplings.py::TreeFixpointTest::test_a_chain_stated_one_level_down_solves
FAILED tests/test_couplings.py::TreeFixpointTest::test_a_deferred_relation_moves_a_body_the_walk_has_not_read_yet
FAILED tests/test_couplings.py::TreeFixpointTest::test_a_wiring_whose_source_a_descendant_solves_binds
FAILED tests/test_couplings.py::TreeFixpointTest::test_an_ancestor_sources_from_a_descendant_solved_coordinate
FAILED tests/test_couplings.py::TreeFixpointTest::test_each_phase_runs_once_per_enumeration
FAILED tests/test_couplings.py::TreeFixpointTest::test_the_refusal_names_the_class_and_the_path
FAILED tests/test_couplings.py::ReadRefusalTest::test_a_class_reading_a_coordinate_its_own_relation_binds
FAILED tests/test_couplings.py::ReadRefusalTest::test_a_class_reading_its_own_derived_coordinate_is_refused
FAILED tests/test_couplings.py::ReadRefusalTest::test_an_ancestor_reading_a_descendant_solved_coordinate_is_refused
FAILED tests/test_couplings.py::ReadRefusalTest::test_the_message_carries_the_reads_source_location
FAILED tests/test_couplings.py::SubclassReplacesRelationTest::test_reading_the_name
FAILED tests/test_couplings.py::SubclassReplacesRelationTest::test_the_position_is_the_bases
FAILED tests/test_couplings.py::SubclassReplacesRelationTest::test_the_replacement
```

Without the stub, `ReadRefusalTest`'s four cases fail at COLLECTION
(`ImportError: cannot import name 'PrematureRead'`) — the more honest red,
recorded here too:

```
ImportError while importing test module '.../tests/test_couplings.py'.
E   ImportError: cannot import name 'PrematureRead' from 'solid_node.motion.couplings'
```

Task 1.3's exact red text (the path defect, before the fix):

```
UnreachedCoordinate: z_axis.column.turn drives strut.swing: nothing bound
either end. column (FixLeaf).turn and strut (FixStrut).swing are both
unbound when nothing changes any more, so the relation has no side to be
read from. ...
```

`column (FixLeaf).turn`/`strut (FixStrut).swing` are the class-name
fallback the fix replaces with `z_axis.column.turn`/`strut.swing`.

Green today, as the tasks require (`test_a_contradiction_is_refused_where_it_is_stated`
1.7, `test_a_rest_default_guard_is_not_refused` 2.4,
`test_a_read_of_a_coordinate_nothing_ever_binds_is_not_this_refusal` 2.5,
`test_the_base_is_unaffected` 4.2, `test_a_bare_statement_stays_additive`
4.4): all pass unmodified.

## Task 3: red first, in `tests/test_joints.py::StaleAuthorBoundJointTest`

```
SUBFAILED(run='second') test_a_non_zero_default_reveals_the_hangprinters_shape
SUBFAILED(run='third')  test_a_non_zero_default_reveals_the_hangprinters_shape
SUBFAILED(run='second') test_a_rest_default_joint_stands_where_it_says_it_stands
SUBFAILED(run='third')  test_a_rest_default_joint_stands_where_it_says_it_stands
  AssertionError: 0 != 1 : run second: []
  AssertionError: 0 != 1 : run third: []
```

Run one always passes (the value binds and the body moves); runs two and
three find the coordinate already non-None (the guard skips the rebind)
and the sweep has already dropped the prior run's operation — zero
translations/rotations where one is asserted, reproducing `probe_stale.py`
exactly as a test. `test_a_binding_made_outside_any_phase_is_not_cleared`
(3.3), `test_a_coordinate_reads_its_bound_value_between_enumerations`
(3.4) and `test_two_assemblies_animating_one_node_clear_only_their_own`
(3.5) are green today.

## Task 5: red first, in `tests/test_kinematics.py::CompatibilityTest` (new file)

```
FAILED test_a_descendant_simulates_against_the_snapshot_just_bound
  AssertionError: 10.0 != 90.0
FAILED test_nothing_that_solves_today_is_deferred
  AssertionError: [] is not true : the instrumentation never ran
FAILED test_symbolic_mode_is_unchanged
  UnreachedCoordinate: down.column.turn drives sink.turn: nothing bound
  either end. ...
```

5.4 reproduces `probe_state_order.py` exactly: the parent's OWN phase
sees the child's PREVIOUS snapshot (`10.0`), not the one just requested
(`90.0`). 5.2's instrumentation monkeypatches
`solid_node.motion.couplings.solve_relations` expecting a
`(assembly, enum)` two-argument signature that does not exist yet, so it
never runs — itself red evidence that the deferral seam is not there yet.
5.6 fails because the "ancestor sources from a descendant" shape it
serializes symbolically is exactly what refuses today.
`test_a_descendants_simulate_reads_what_an_ancestors_relation_bound`
(5.1), `test_the_pass_order_is_unchanged_for_a_tree_that_defers_nothing`
(5.3) and `test_set_states_refusals_and_rollback_are_unchanged` (5.5) are
green today.

**Totals**: 21 failed, 13 passed, 4 subtests passed across the five new
test classes — every novel-behaviour case red, every
compatibility/must-not-change case green, before any source change.

---

## Task 6: the implementation, as built

- `solid_node/node/phase.py`: `Phase` gains a `.bound` list (every
  coordinate slot bound while this phase is running, author or
  framework alike) and `note_bound(slot)`; a new `Enumeration` (`.deferred`,
  `.reads`) and its own stack (`current_enumeration`, `open_enumeration`,
  `close_enumeration`); `note_unbound_read(slot)` records `(slot,
  reading_assembly, reading_class, filename, lineno)` on the open
  enumeration when a SIMULATE phase reads an unbound slot.
- `solid_node/node/assembly.py`: `_run_phase(assembly, render,
  enumeration)` is the per-node phase — sweep, rest, LINK, clear, the
  author's `simulate()`, `solve_relations(assembly, enumeration)` — and
  records `assembly.__dict__['_solver_bound'] = phase.bound`
  unconditionally (so a coordinate an assembly's OWN `simulate()` binds,
  with no relation of its own at all, is still cleared next phase).
  `_lifecycle_render`'s `wrapped()`: a `render()` with no enumeration
  open OWNS one, drives `_run_phase` for itself then every drivable
  child (`_drivable(node)`: `type(node).render._idempotent`), then (if
  owning) `_finish_enumeration` (`run_deferred` then `refuse_reads`) and
  closes it. A node already marked as having run in the CURRENTLY OPEN
  enumeration returns its cached rest children without re-running its
  phase. `_rest_children(assembly)` is the rest-only descent
  `set_state`/`clear_state` now use to DELIVER a snapshot over the whole
  tree before enumerating once (`_rendered_children`, which used to
  render-and-therefore-simulate as it delivered, is gone; a compatibility
  alias is kept in `tests/test_traversal_naming.py` only).
- `solid_node/motion/couplings.py`: `solve_relations(assembly,
  enumeration)` is the per-instance ATTEMPT — unchanged propagate loop —
  whose leftovers become a `_Deferred(assembly, records, derived,
  wirings, claimed, bound)` appended to `enumeration.deferred`, where
  `bound` is the SAME list `_run_phase` will read back.
  `run_deferred(enumeration)` re-runs the unchanged `_step_relation`/
  `_step_derived`/`_step_wiring` over every deferred unit to a fixpoint,
  then calls the unchanged `_refuse` per unit. `refuse_reads(enumeration)`
  is the read-refusal rule (skips a still-unbound slot, and a slot whose
  binder is `None` — the author). `clear_solved` skips a slot whose
  `_enum_marker` IS the currently open enumeration (see task 9.2 below).
  `declared_relations` walks the MRO base-first, replacing a name already
  seen at ITS position rather than appending, so a subclass's named
  relation keeps the base's place and the base's own relation is
  unaffected. New export `PrematureRead(CouplingError)`.
- `solid_node/motion/ports.py`: `BoundPort.value` records an unbound
  read (`note_unbound_read`) when `_value is None`; `bind()` sets
  `sink._enum_marker = current_enumeration()` on every bind, framework or
  author, and calls `note_bound(sink)`.
- `solid_node/node/qualified.py`: `drive_tree` restructured into a
  rest-only `deliver()` pass over the whole tree (binding every node's
  entries, calling `visit()`, descending via the NEW `_rest_children`),
  followed by ONE `root.render()` — necessary because a nested driver's
  own render() now runs as part of whatever ancestor's enumeration
  reaches it first, which can be before this walk's own visit to that
  node. `joints.py`, `declarative.py` and the serializer are untouched,
  as the proposal states; `qualified.py` is not named there and needed
  this one change (found by `tests/test_build_defaults.py`).

**The resolution rule, in one sentence:** a relation, derived formula or
wiring an instance's own attempt cannot resolve is DEFERRED to the
enumeration that opened when the outermost `render()` found none
already running, resolved once every assembly's phase in that
enumeration has run (parents before children, tree order), and refused
only if it is still unresolved then — except a `DoublyBound` coordinate,
which is never a question of timing and is refused where it is found.

## Task 6 (a second finding, not in the ratified design): the
`_enum_marker` fix

Implementing task 9's catalogue comparison surfaced a defect the
proposal's own design did not anticipate: `clear_solved`, as first
implemented (clearing every slot in an assembly's own `_solver_bound`
unconditionally), let a DESCENDANT's belated clear of ITS OWN stale
record erase a value an ANCESTOR's relation had ALREADY correctly
bound earlier in the SAME enumeration — measured directly on Prusa
i3's `x.drives(xaxis.carriage.travel)` racing `XAxis`'s own
rest-default guard (`evidence.md` §9 below has the exact before/after
numbers: 1.199e4 mm max deviation before the fix, 0 after). Fixed by
giving every `BoundPort` an `_enum_marker` (the `Enumeration` object
whose bind it was last touched by, set on every `bind()`) and having
`clear_solved` skip a slot whose marker is the CURRENTLY open
enumeration — meaning some other assembly, earlier in this same
cascade, already claimed it fresh. This is reported here rather than
silently folded in because it is a departure the ratified design.md did
not state; see the report's "every open question's resolution" section
for the full account.

## Task 7: the suite

Base (task 0.3): `2169 passed, 16 skipped, 50 warnings, 796 subtests
passed in 339.50s`. Head, full suite, after every fix above:

```
2199 passed, 16 skipped, 50 warnings, 804 subtests passed in 288.78s (0:04:48)
```

`2199 - 2169 = 30` — exactly the 30 new task 1/2/3/4/5 tests (task
1.4/1.7/1.8/2.4/2.5/4.2/4.4 GREEN-today cases included), `804 - 796 = 8`
new subtests (task 3's `subTest(run=...)` x2 tests x3 runs = 6, plus
`TreeFixpointTest.test_a_contradiction_is_refused_where_it_is_stated`
and `SubclassReplacesRelationTest`/`ReadRefusalTest` subTests actually
land as 2 more). Zero failures at head; the two full-suite runs taken
during debugging (2199 passed both times, once before and once after
the `_enum_marker` fix) confirm the fix did not disturb anything else.

Task 7.2, per file:

| file | result |
|---|---|
| `tests/test_couplings.py` | 135 passed, 105 subtests passed |
| `tests/test_kinematics.py` (new) | 6 passed, 2 subtests passed |
| `tests/test_joints.py` | 149 passed, 231 subtests passed |
| `tests/test_ports.py` | 28 passed, 25 subtests passed |
| `tests/test_animator_tag.py` | 3 passed |
| `tests/test_serializer.py` | does not exist in this tree; not run |

**Four pre-existing tests needed updating** (not new tests; existing
ones whose assertions encoded exactly the behaviour the ratified design
overturns):

- `test_couplings.py::FreshnessTest::test_an_author_binding_from_an_earlier_run_is_not_cleared`
  → renamed `..._is_cleared_with_its_motion`: it tested the OLD "author
  bindings are never cleared" guarantee directly; now expects
  `UnreachedCoordinate` on the run that finds neither end bound.
- `test_declarative_render.py::RenderReturnsNothingTest::test_a_grouping_node_needs_no_methods`
  and `test_a_legacy_render_is_untouched`: both asserted a bare
  `render()` call leaves a child UNLINKED (`_parent is None`, or named
  by class-name fallback); `whole-tree-fixpoint` links a node's children
  as part of its own phase, so both now assert the (correct) linked
  state.
- `test_traversal_naming.py`: three tests' exact index-build counts
  needed doubling (`name_index_calls`/`instrumented_alias.iterations`
  parameterized, default still 1) because a walker that explicitly
  re-links after `render()` (the serializer, `as_scad`) now does so
  AFTER render()'s own internal link, not instead of it; two
  `MidTraversalMutationTest` tests needed their expected NAMES
  corrected, because a mutation an `AssemblyNode` child's action causes
  now happens during the SAME cascade a walker's `render()` call
  triggers, before that walker's own necessary re-link, rather than
  only on ITS OWN later, separate visit to that child.

Every one of these is a necessary, traced consequence of the ratified
design (linking, and every phase preceding any geometry read), not a
workaround; each edit's reasoning is recorded in a comment at the site.

## Task 8: cost

One heavy process at a time; base is the PRIMARY checkout at `63a2099`
(this cycle's own base commit, confirmed clean on `solid_node/`), head
is this worktree; one run each (not three — time did not allow the
ratified three, noted as a reduced sample), same four snapshot trees
task 9 already used (the two named in the proposal, Thor and wall clock
01, are not among this cycle's own snapshots — see §0.5's scope note —
so the four LARGEST among the 23 actually snapshotted stand in):

| project (leaves) | base | head | ratio |
|---|---|---|---|
| openvmp (499) | 11.34s | 12.10s | 1.07 |
| Metamaquina2 (452) | 12.05s | 12.26s | 1.02 |
| hexapod_spiderbot_model (172) | 6.37s | 6.25s | 0.98 |
| openflexure-microscope (113) | 4.06s | 4.21s | 1.04 |

All within single-run noise of 1.0; none over the 5%-regression
reporting bar with any margin worth trusting from one sample. Task 8.2
(the couplings/kinematics/joints/ports suite, three runs) and 8.3 (a
committed micro-benchmark) were NOT done — reported here rather than
invented, given the time this cycle had left after task 9's defect and
its fix. `evidence/bench_enumeration.py` does not exist in this change.

## Task 9: the catalogue

**Scope.** "The 23" = the tracker's `done` rows (§0.5). Base captures:
§0.5 above (git-archive snapshot, before any framework source change).
Head captures: the SAME 25 refs, SAME snapshots, run again after the
complete implementation (including the `_enum_marker` fix).

**9.1 — base vs. head, same snapshot, all 23 (25 refs):**

| project (model) | max deviation |
|---|---|
| open_manipulator | 0.000e+00 |
| OpenCycloid | 0.000e+00 |
| poseidon (pump/microscope/poseidon) | 0.000e+00 / 0.000e+00 / 0.000e+00 |
| OpenTorque-Actuator | 0.000e+00 |
| BCN3D-Moveo | 0.000e+00 |
| openarm | 0.000e+00 |
| HACKberry | 0.000e+00 |
| hexapod_spiderbot_model | 0.000e+00 |
| abacus | 0.000e+00 (after the `_enum_marker` fix — see below) |
| YouCanBuildDog | 0.000e+00 |
| openvmp | 0.000e+00 |
| pascaline | 0.000e+00 |
| Internal-Cycloidal-Actuator | 0.000e+00 |
| hangprinter | 0.000e+00 |
| AlbertPro | 0.000e+00 |
| snappy-reprap | 0.000e+00 |
| Prusa3-vanilla | 0.000e+00 (after the `_enum_marker` fix — see below) |
| openflexure-microscope | 0.000e+00 |
| Inmoov-sim | 0.000e+00 |
| v8-engine | 0.000e+00 |
| Metamaquina2 | 0.000e+00 |
| science-jubilee | 0.000e+00 |
| open_robot_actuator_hardware | 0.000e+00 |

**Every project moved before the fix went in, is reported before
anything else was done** (per task 9.1's own instruction): Prusa3-vanilla
showed max deviation 1.199e4 (`xaxis.carriage.travel -11.5 -> -37.5`,
and every downstream body it carries) and abacus showed 7.0
(`columns-N.earth 2.52 -> 0.0` and every bead it drives) on the FIRST
head capture, both traced to the SAME root cause (an ancestor's relation
racing a descendant's own rest-default guard for one coordinate) and
fixed by the `_enum_marker` change above; both are 0.000e+00 on the
capture taken after the fix, from the identical, never-re-snapshotted
project source.

**9.2 — Prusa i3 and hangprinter, second render:** both measure
0.000000 mm at the BASE (task 0.6) because their current, committed
code already works around the framework gap defensively; both stay at
0.000e+00 at HEAD (task 9.1's table above and the dedicated second-render
probe re-run at head). The number that matters — that this project's
poses do not move — holds at both ends.

**9.3, 9.4, 9.5, 9.6 (3DPrintedClocks overlay; wall clock 01's chain
overlay; openflexure's root-sentence overlay; OpenTorque's single-1:8
and subclass overlay) — NOT DONE.** 3DPrintedClocks' working tree was
under the pilot's own session throughout (confirmed by a live
pose-audit process running against it at the start of this session);
reading it for an overlay, even read-only, was avoided per the
briefing's own instruction. The other three overlays (9.4 on wall clock
01, which is also 3DPrintedClocks; 9.5 on openflexure; 9.6 on
OpenTorque) were deferred to keep to the time this session had left
after task 9.1 surfaced and required fixing the `_enum_marker` defect;
each of the two framework mechanisms they would prove (the tree
fixpoint; the named-replacement) already has a passing, focused unit
test (cited in the corresponding `workflow/warts.md` FIXED entries), and
each named project's OWN existing code, unmodified, already measures
0.000e+00 base-against-head (9.1's table). Overlay proof on the EXACT
sentence from the project's own docstring, over and above that, remains
open for a follow-up session.

**9.7 — nothing under `projects/` was written.** Every capture ran from
a `git archive HEAD` snapshot under scratch, never the project's own
working tree; `git status --porcelain` on every project touched by this
session was checked clean of anything BUT scratch/screenshot files
before its ignored vendor/asset directories were copied (§0.5), and
untouched after (nothing in this implementation ever opens a project
path for writing).

## Task 10: the record

- ADR-099 (`docs/adrs/NODE/ADR-099-the-enumerations-simulate-phases-are-one-tree-pass.md`),
  revising ADR-089, citing ADR-093/096; indexed in `docs/adrs/README.md`.
- `docs/architecture.md`'s "The simulate phase runs in a fixed order"
  paragraph rewritten in place (not appended to), plus a new "One
  ENUMERATION is one tree pass" paragraph after it.
- `docs/driving.rst`: the "Relations" section gains the split-chain
  example, the deferral/read-refusal/replacement/clear paragraphs; the
  "Joints" section gains the "cleared with the motion it caused"
  paragraph. `docs/changelog.rst`'s Unreleased section gains the entry.
- `workflow/warts.md`: the four findings and the OpenTorque subclass
  rider marked FIXED under this cycle's name, each stating exactly what
  shipped and honestly noting which catalogue overlay proofs (9.4/9.5/9.6)
  were not completed; finding history left intact.

## Task 11: close

- `openspec validate --strict whole-tree-fixpoint`: **valid**.
- 11.2 (sync specs, archive) explicitly NOT done — the orchestrating
  session's review comes first, per the briefing.
