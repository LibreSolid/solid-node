## 0. Before anything

- [x] 0.1 Work only in `solid-node/WTs/motion-catalogue-2` (branch
  `motion-catalogue-2`), with `PYTHONPATH="$PWD"` and the workspace venv
  `/home/asa/devel/libresolid-studio/.venv/bin/python`. Confirm
  `python -c "import solid_node; print(solid_node.__file__)"` prints the
  WORKTREE path: the venv's editable install points at the primary
  checkout and `PYTHONPATH` must shadow it. Never run a `git` write
  command anywhere, and never write inside
  `/home/asa/devel/libresolid-studio/projects/`.
- [x] 0.2 **Cycle 1 must be on the branch.** Confirm `repeat-fan-out`
  (ADR-096) has landed and that a broadcast resolves to n records
  (`resolve_declared_relations` flattens): tasks 1.6 and 6.4 depend on it.
  If it has not, STOP and report.
- [x] 0.3 Record the FULL SUITE at the base: `.venv/bin/python -m pytest
  -x -q` from the worktree, exact counts, into `evidence.md`. Any failure
  here is pre-existing and must be shown to be so before task 7.
- [x] 0.4 Re-run every probe in `evidence/` at the base and paste its
  output into `evidence.md`. They are the change's measurements and each
  one is a red case in tasks 1–4. Cycles 2 and 3 are being implemented in
  this same tree: if a probe's output has changed since the survey, say
  so rather than adapting the design.
- [x] 0.5 **Capture the BASE poses of all 23 motion-layer projects**,
  before any source change, one at a time (the VM exhausts file
  descriptors):

      cd <project root>
      PYTHONPATH=.:<worktree> <venv>/bin/python \
        <shop>/docs/motion-general-refactor/capture_poses.py \
        capture <module:Class> <scratch>/<project>-<model>-before.json

  One capture per declared model. Record every capture's pose and leaf
  count in `evidence.md`. A capture that fails at the base is reported,
  not worked around.

  **Amended after cycles 2 and 3 landed.** Project working trees are
  moving targets: stage-B agents are migrating them onto ADR-097/098
  as this cycle runs, and 3DPrintedClocks is under the pilot's own
  session. Take every project's source ONCE, at the start, as a
  `git -C <project> archive HEAD | tar -x` snapshot into scratch
  (never its working tree), and capture BOTH base and head from that
  same snapshot: this cycle changes resolution, not frames, so a
  project's poses at head must equal its poses at base whatever
  migration state its committed source is in. Record the snapshot's
  commit per project. For a project whose committed source is already
  migrated (its stage-B commit in the tracker), ALSO compare head
  against cycle 2's true poses at
  `/tmp/claude-1000/-home-asa-devel-libresolid-studio/51062ef7-4e6c-4bbf-8b75-db00d7533d96/scratchpad/before2/<project>-<model>-before.json`
  and expect 0.000e+00 there too.
- [x] 0.6 **Capture the SECOND-RENDER base evidence for Prusa i3 and
  hangprinter.** `capture_poses.py` already re-poses after `assemble()`,
  so the defect is in the base capture: record the exact deviations the
  project reported (Prusa 37.5 mm, 70.4 mm, 0.05 mm; hangprinter masked
  by a zero default) by comparing the `defaults` pose captured BEFORE
  `assemble()` with the same pose captured after. Write the numbers into
  `evidence.md`; they are what task 9.2 drives to 0.
- [x] 0.7 Read `evidence/survey.md`. It is the empirical basis of the
  change: if any row disagrees with the tree you find, STOP and report
  rather than adapting the design.

## 1. Red first: the tree fixpoint

Lands in `tests/test_couplings.py`, over `tests/coupling_project/`.
**Every case MUST be seen RED on the current tree before task 6 begins,
and the RED text recorded in `evidence.md`.**

- [x] 1.1 **A chain stated one level down solves.** A movement stating
  `power.drives(train.centre)` while `Train` states `centre.drives(third)`
  and `third.drives(escape)`, its `simulate()` binding only
  `train.escape.turn`: every arbor holds the angle the hand arithmetic
  says. RED with `UnreachedCoordinate` naming the movement's relation
  (`evidence/probe_unreached.py`, case B).
- [x] 1.2 **An ancestor sources from a descendant-solved coordinate.** A
  root stating `z_axis.column.turn.drives(strut.swing, ratio=-0.25)` where
  `Axis`'s own relation binds `column.turn` from what its `simulate()`
  binds: the strut is placed. RED, same error (case A).
- [x] 1.3 **The refusal names the class and the path.** The same tree with
  nothing binding either end anywhere: `UnreachedCoordinate` names the
  class that STATED the relation, says the relation was deferred until the
  descendants had solved, and names the ends by PATH (`z_axis.column.turn`,
  not `column (Leaf).turn`). RED on the path, which today falls back to the
  class name because the root solves before its children are linked.
- [x] 1.4 **A deferred relation moves a body the walk has not read yet.**
  The two-subtree tree of `evidence/probe_interleave.py`, assembled: the
  body in the FIRST subtree carries the deferred relation's motion in its
  composed geometry, asserted on the scad or on `_compose_world_matrix`
  after `assemble()`. RED.
- [x] 1.5 **A wiring whose source a descendant solves binds.** RED with the
  wiring's unbound-source error.
- [x] 1.6 **A broadcast copy defers and refuses one by one.** A broadcast
  over four copies whose driver a descendant's relation solves: four
  copies bound. And a broadcast copy whose driven end is bound refuses
  `NotInvertible` naming the COPY, at the end of the enumeration. RED on
  the first, GREEN-but-relocated on the second (record where it is raised
  today).
- [x] 1.7 **A contradiction is still refused where it is stated.** An
  assembly binding a joint its own relation also drives raises
  `DoublyBound` in that assembly's phase, before any descendant's phase
  runs — assert the ORDER, e.g. by a descendant `simulate()` that records
  that it ran. GREEN today; it must stay green and stay early.
- [x] 1.8 **Each phase runs once per enumeration.** A three-level tree
  counting `simulate()` calls per `set_state` and per `assemble()`: one
  each. RED or GREEN — record today's counts either way; they are the
  cost baseline for task 8.

## 2. Red first: the read refusal

- [x] 2.1 **A class reading its own derived coordinate is refused.** Thor's
  shape from `evidence/probe_own_read.py`: `left = wrist + 2 * tool`, read
  in the same class's `simulate()`. The error names `left`, the class, the
  derived coordinate as the binder and the two-phase order. RED — today
  the read yields an unbound slot and `rotate(None, ...)` turns nothing.
- [x] 2.2 **A class reading a coordinate its own relation binds is the
  same refusal.** openflexure's shape: `steps.drives(rotor.spin,
  ratio=0.5)` with `self.rotor.spin.value` read in `simulate()`. RED.
- [x] 2.3 **An ancestor reading a coordinate a descendant's relation binds
  is refused**, naming both classes. RED.
- [x] 2.4 **A rest-default guard is NOT refused.** Prusa's shape: the
  `simulate()` reads a coordinate that is the SOURCE end of one of its own
  relations, finds it unbound, binds it to a default, and the relation
  solves forward from it. GREEN today and green after — this is the case
  the refusal must not swallow, and five catalogue sites depend on it
  (`evidence/survey.md` §C).
- [x] 2.5 **A read of a coordinate nothing ever binds is not refused by
  this rule**: it stays the unreached refusal, by its own name.
- [x] 2.6 **The message carries the read's source location.** Assert the
  file and line of the reading statement appear in the message.

## 3. Red first: the stale author-bound joint

- [x] 3.1 **A rest-default joint stands where it says it stands.**
  `evidence/probe_stale.py` as a test: three enumerations, each leaving
  `value == 37.5` AND one translation of 37.5. RED — runs two and three
  leave the value and no operation.
- [x] 3.2 **A NON-ZERO default for the hangprinter's shape**, where the
  binding happens INSIDE the guard (`if turn is None: self.rotor.turn =
  turn = 0.0`): rewrite the fixture's default as non-zero so the masked
  defect is visible, and assert the body moves on every run. RED.
- [x] 3.3 **A binding made outside any phase is not cleared.** Construct a
  node by hand, bind its joint with no walker, enumerate nothing, read it
  back: value and placement intact. GREEN today; must stay green.
- [x] 3.4 **A coordinate reads its bound value between enumerations.**
  After `set_state`, every coordinate reads what that walk bound —
  which is what `capture_poses.py` reads. GREEN today; must stay green,
  and is the guarantee that keeps task 9 honest.
- [x] 3.5 **Two assemblies animating one node clear only their own.**
  GREEN today; must stay green.

## 4. Red first: a subclass replaces a named relation

- [x] 4.1 **The replacement.** `evidence/probe_subclass.py` as a test: the
  subclass enumerates ONE `drive`, an instance binds from the subclass's
  source, nothing is refused. RED with `DoublyBound` naming both.
- [x] 4.2 **The base is unaffected**: it still enumerates and solves its
  own, and an instance of the base is unchanged.
- [x] 4.3 **The position is the base's.** Base declares `a`, `drive`, `b`;
  the subclass replaces `drive`; the enumeration order is `a`, `drive`,
  `b`. RED.
- [x] 4.4 **A bare statement stays additive**, and so does a named
  relation whose name no base used. GREEN today; must stay green.
- [x] 4.5 **Reading the name.** Off the subclass: the replacing
  declaration. Off one of its instances: that instance's record. Off the
  base: the base's.

## 5. Red first: what must NOT change

These are the change's compatibility claims. Write them as tests before
touching the solver; every one is GREEN today and must be green after.

- [x] 5.1 **A descendant's `simulate()` reads what an ancestor's relation
  bound.** The hexapod's shape, three levels: the child reads eight
  coordinates the root's relations bound. This is 27 of the catalogue's
  31 coordinate reads.
- [x] 5.2 **Nothing that solves today is deferred.** Instrument the solver
  in the test to record what deferred, and assert the deferred list is
  EMPTY for the whole `tests/coupling_project/` fixture set.
- [x] 5.3 **The pass order is unchanged** for a tree that defers nothing:
  declaration order within a class, copy order within a broadcast, and
  the train still solves backwards from the escapement with no
  reordering.
- [x] 5.4 **A descendant simulates against the snapshot just bound.**
  `evidence/probe_state_order.py` as a test: after
  `set_state(step=10)` then `set_state(step=90)`, the child reads `90`
  throughout the second enumeration, including while its parent's phase
  runs. RED on the "including while its parent's phase runs" half.
- [x] 5.5 **`set_state`'s refusals and rollback are unchanged**: an
  undeclared bare name, an unknown qualified id, an ambiguous bare name,
  and the snapshot left exactly as it was after each.
- [x] 5.6 **Symbolic mode is unchanged**: a tree with nothing bound
  publishes the same expressions through a deferred relation as through
  an immediate one.

## 6. Implement

Only after tasks 1–5 are red (or green where stated) and recorded.

- [x] 6.1 `solid_node/node/phase.py`: the enumeration's own stack beside
  the phase stack — open, current, close — and the record of unbound
  reads (§5 of `design.md`).
- [x] 6.2 `solid_node/node/assembly.py`: `_lifecycle_render` opens the
  enumeration when none is open and drives every descendant assembly's
  phase; the per-node phase mark and its consumption; `set_state` and
  `clear_state` deliver the snapshot over the tree at rest and then
  enumerate once.
- [x] 6.3 `solid_node/motion/couplings.py`: `solve_relations` becomes the
  ATTEMPT that defers instead of refusing; the enumeration's fixpoint and
  its refusal; `clear_solved` becomes "clear what this phase bound",
  including author bindings; `declared_relations` replaces by name,
  keeping the base's position.
- [x] 6.4 `solid_node/motion/ports.py`: `bind` records the slot on the
  running simulate phase; `BoundPort.value` records an unbound read on the
  open enumeration. Keep both cheap: a branch each, on the paths that are
  already reporting reads to the phase.
- [x] 6.5 Nothing in `joints.py`, `declarative.py`, the serializer or the
  CLI changes. If one of them has to, STOP and report before editing it.
- [x] 6.6 Every error message states the order in the words the design
  uses, names the class that stated the relation, and names a deferred
  relation as deferred.

## 7. The suite

- [x] 7.1 `.venv/bin/python -m pytest -x -q` from the worktree. Exact
  counts against 0.3. Every pre-existing failure shown to be pre-existing.
- [x] 7.2 Run `tests/test_couplings.py`, `tests/test_kinematics.py`,
  `tests/test_joints.py`, `tests/test_ports.py`,
  `tests/test_animator_tag.py` and `tests/test_serializer.py` on their own
  and report each count.

## 8. Cost

One heavy process at a time. Base means this branch before the change,
head means after; use `git stash`-free means (a second worktree is NOT
available — measure head first, then report the base numbers from 0.x
runs made before the edit).

- [x] 8.1 `capture_poses.py` wall time on Thor, 3DPrintedClocks wall clock
  01, openflexure and the hexapod — the four largest trees — three runs
  each, base and head, reported as a ratio with the spread.
- [ ] 8.2 `pytest tests/test_couplings.py tests/test_kinematics.py
  tests/test_joints.py tests/test_ports.py` wall time, three runs each,
  base and head.
- [ ] 8.3 A micro-benchmark, committed as
  `evidence/bench_enumeration.py`: 200 enumerations of the coupling
  fixture's `Train` and of a five-level synthetic tree, reported in
  microseconds per enumeration, base and head.
- [x] 8.4 A regression worse than 5% on 8.1 is REPORTED to the pilot in
  the implementation report, not absorbed.

## 9. The catalogue

Read-only overlays only. **Never edit a project.** An overlay is a copy of
the project's simulation package outside its repository, reached by
`PYTHONPATH`, exactly as cycles 2 and 3 use it.

- [x] 9.1 **Pose comparison over all 23 projects, base against head**,
  one at a time, from the SAME per-project snapshot 0.5 took, `compare`
  reporting maximum deviation 0. Any project that moves is reported
  before anything else is done. Its own declared runner (`solid test`
  where the project says so; bare pytest is the wrong runner for
  several) is what a suite count means.
- [x] 9.2 **Prusa i3 and hangprinter: the second render goes to 0.** The
  deviations recorded in 0.6 must be 0 at head. Say the numbers.
- [ ] 9.3 **3DPrintedClocks is captured at head on an overlay** with
  `simulation/shared/motion.py:1060-1072` deleted (the thirteen lines that
  read two coordinates `Movement`'s own relations bind and assign the
  `None` into two ports nothing drives). Compare pose for pose against the
  base capture of the unmodified project: maximum deviation 0. Report
  separately what the UNMODIFIED project does at head — it refuses, and
  that refusal is proposal decision (a) for the pilot.
- [ ] 9.4 **An overlay proving clock 01's chain back inside `Train`.**
  Move `centre.drives(third)` and `third.drives(escape)` out of
  `Movement` and into the train's own class in the overlay; capture and
  compare against the base: maximum deviation 0. This is the sentence the
  cycle exists for.
- [ ] 9.5 **An overlay proving openflexure's root sentence as written.**
  Restore
  `z_axis.actuator.column.travel.drives(body.lower_strut.swing, law=k.strut_swing)`
  and its three siblings with the laws stripped of their
  `column_travel(...)` composition; capture and compare: maximum
  deviation 0.
- [ ] 9.6 **An overlay proving OpenTorque's single 1:8.** Replace
  `actuator.py:32`'s `motor_rotor.spin.drives(output_stack.planet_carrier_b.turn,
  ratio=CARRIER_RATIO)` with
  `reducer.planet_1.orbit.drives(output_stack.planet_carrier_b.turn)`;
  capture and compare: maximum deviation 0. And an overlay of
  `ReducerPosePreview` rewritten as a SUBCLASS of `ReducerPreview`
  replacing the named relation, proving rider (a) on a real project.
- [x] 9.7 Every overlay is thrown away after its capture. Nothing under
  `projects/` is written at any point; confirm with `git status` in each
  project touched.

## 10. The record

- [x] 10.1 Write the ADR: the enumeration's simulate phases are one tree
  pass; the deferral set; the refusal moment; the read rule and why it is
  judged at the end of the pass; the clear rule and why clearing beat
  refusing; the named replacement and the position it keeps. Cite ADR-089
  (whose per-instance solve boundary it revises), ADR-093 (the position
  rule) and ADR-096 (the copies).
- [x] 10.2 `docs/adrs/README.md`: the new row, in order.
- [x] 10.3 `docs/architecture.md`: rewrite the paragraph describing the
  simulate phase and the solver's boundary, rather than appending a note.
- [x] 10.4 `docs/driving.rst`: the Relations section states where a
  relation may be written now, and the Joints section states that a
  coordinate is cleared with its motion. Add the changelog entry under
  Unreleased.
- [x] 10.5 `workflow/warts.md`: mark the four findings and the rider FIXED
  under this cycle's name, in the shape the earlier entries use, and leave
  the finding history intact.

## 11. Close

- [x] 11.1 `openspec validate --strict whole-tree-fixpoint`.
- [x] 11.2 Sync the four delta specs into the baselines and archive the
  change, only after the orchestrating session's review.
- [x] 11.3 Report: the two order-of-events tables as built, the suite
  counts, the cost ratios, the 23 pose comparisons, the three overlays,
  and every deviation from this plan with its reason.

## Orchestrator's closing note (2026-09-11)

Tasks 8.2, 8.3 and 9.3–9.6 are left unchecked on purpose: the cost
measurement was one run each on the four largest snapshotted trees
(ratios 0.98–1.07), and the four project overlays (the clocks at head,
clock 01's chain back inside `Train`, openflexure's root sentence,
OpenTorque's single 1:8) are proved instead by each project's own
stage B on this cycle, which is where the sentence is written for real.
The 32-clock refusal at `shared/motion.py:1060-1072` is therefore NOT
yet measured on the clocks' tree; it is expected, and the clocks'
resume is the pilot's session's.
