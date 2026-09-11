## 0. Before anything

- [ ] 0.1 Work only in `solid-node/WTs/motion-catalogue-2` (branch
  `motion-catalogue-2`, base `5b28510`), with `PYTHONPATH="$PWD"` and the
  workspace venv `/home/asa/devel/libresolid-studio/.venv/bin/python`.
  Confirm `python -c "import solid_node; print(solid_node.__file__)"`
  prints the WORKTREE path before running anything: the venv's editable
  install points at the primary checkout. Never touch a project, the
  primary checkout or the shop.
- [ ] 0.2 **Confirm the stack.** Cycle 1 (`repeat-fan-out`, ADR-096) must
  be on the branch, and cycle 4 (`whole-tree-fixpoint`) must be
  IMPLEMENTED AND ARCHIVED before this cycle's implementation begins: two
  of this change's four MODIFIED requirements are written on top of cycle
  4's text, and its deferral rule is what a relation with an unbound
  source relies on. If cycle 4 is not archived yet, STOP and report.
- [ ] 0.3 Record the FULL SUITE at the base:
  `.venv/bin/python -m pytest -x -q` from the worktree, exact counts, into
  `evidence.md`. Any failure here is pre-existing and must be shown to be
  so before task 5 begins.
- [ ] 0.4 Re-run the two proposal probes and paste their current output
  into `evidence.md`: `evidence/probe_today.py` (the tuple has no verb and
  cannot be given one; `a.drives((b, c))` reaches the framework's
  refusal; `&` is free; a class body that binds `drives` shadows a free
  function; what the law is handed today) and `evidence/probe_returns.py`
  (a value has no length; a law returning four values binds the tuple and
  produces `Rotation(1.0, 2.0, 3.0, 4.0)`). They are the reason the
  spelling and the length check read as they do; if either has changed,
  STOP and report rather than adapting the design.
- [ ] 0.5 Re-read `design.md` §14 and confirm with the orchestrating
  session which of the open questions the pilot answered — the law's
  argument shape (proposal (b)) decides the whole of task 2.

## 1. Red first: a group at class definition

Lands in `tests/test_couplings.py`, in a new section "Several
coordinates at one end" after the fan-out section. **Every case MUST be
seen RED on the current tree before task 5 begins, and the RED text
recorded in `evidence.md`.**

- [ ] 1.1 **Fixtures.** `Rod`, a rigid leaf declaring four joints
  (`spin`, `lean`, `swing` as `Revolute`, `rise` as `Prismatic`) in that
  order; `Leg`, declaring two; `Machine`, declaring three `Driver`s,
  `rods = Rod().repeat(6)` and a plain `rod = Rod()`.
- [ ] 1.2 **A group of sources drives one coordinate.**
  `(a & b).drives(child.turn, law=...)` builds the class and states ONE
  relation whose source names two coordinates in the order written. RED
  (today: `TypeError: unsupported operand type(s) for &`).
- [ ] 1.3 **A tuple of driven ends.** `a.drives((b, c), law=...)` and
  `a.drives(b & c, law=...)` state the same relation. RED (today:
  `(...) is not a coordinate`).
- [ ] 1.4 **`&` chains flat.** `x & y & z` is one group of three, in
  written order, not a nested pair — assert the ends the relation
  carries, not the object.
- [ ] 1.5 **Every group refusal, each by its own message** (design §7):
  a repeated source inside a group; a driven group mixing a broadcast
  with a plain end; a driven group over two different repeated segments;
  `ratio=`/`offset=` with a group; a group with NO `law=`; the empty
  group; the group of one; the nested group; a repeated coordinate in one
  group; a coordinate on both sides; a group as a term of a formula;
  `a & 3` and `a & <node>`; and the missing parentheses
  (`count & next_count.drives(...)`, which must name the relation the
  inner call stated). Assert the MESSAGE, not only the type.
- [ ] 1.6 **The existing per-member refusals are reached inside a group**
  and are the EXISTING messages, not new ones: a `Driver` as a driven
  member, a node whose class declares two joints, a path stopping on a
  multi-coordinate joint.

## 2. Red first: the law protocol

- [ ] 2.1 **What the law is handed.** A relation of three sources and
  four driven ends: the callable is called ONCE at realization with two
  arguments; the first is the tuple of the three owners in written order,
  the second the tuple of the four owners in written order. Assert with a
  callable whose signature is `(*args)`, so a signature-sniffing
  implementation would be caught, and assert the call happened before any
  `simulate()`.
- [ ] 2.2 **A one-to-one law is untouched.** The same two-argument
  callable on an ordinary relation in the same class still receives two
  NODES, not two tuples. This is the compatibility case; it is green
  today and must stay green.
- [ ] 2.3 **Mixed arities.** n sources with one driven end hands a tuple
  and a node; one source with m driven ends hands a node and a tuple.
- [ ] 2.4 **`forward` spreads its sources and returns a sequence.** Three
  values in, a four-sequence out, bound in written order. Assert the four
  slots, and assert that a list, a tuple and any other sized sequence are
  all accepted.
- [ ] 2.5 **A wrong return shape is refused by name**, at the moment it
  is applied: too few, too many, a bare number, a string, and an object
  with no length. Each message names the relation, the law, the driven
  ends as written and what came back, and NO coordinate was bound. RED —
  and record what happens today for the four-values case
  (`evidence/probe_returns.py`: `Rotation(1.0, 2.0, 3.0, 4.0)`).
- [ ] 2.6 **A single driven end still returns a bare value**, including
  when the value is symbolic; nothing is unpacked.
- [ ] 2.7 **No new error kind.** The shape refusal is a `CouplingError`
  and the three named errors are still exactly three — assert the module
  exports.

## 3. Red first: the solver

- [ ] 3.1 **Forward once, when the last source is bound.** Two sources
  bound in `simulate()` and a third bound by a relation of the same
  class: nothing is bound until the third is, and then all m ends are.
- [ ] 3.2 **Deferred across the tree.** The last source is bound by a
  DESCENDANT's relation, so the record defers to the enumeration's
  fixpoint (cycle 4) and is applied there, under the stating assembly's
  phase — assert the animator tag and that the motion is swept on the
  next run.
- [ ] 3.3 **Never inverted.** All m driven ends bound by hand and the
  sources unbound: `NotInvertible` naming the relation, a bound driven
  end and the unbound sources, saying a relation of several ends is read
  forward only — with a law that DOES offer an `inverse`, so the case
  proves the rule and not the law.
- [ ] 3.4 **The unreached message names the unbound sources.** Two of
  three sources bound, nothing reaches the third:
  `UnreachedCoordinate` naming the ONE unbound source, not all three.
- [ ] 3.5 **Claim before bind.** The author binds one of four driven ends
  and every source is bound: `DoublyBound` names that coordinate and its
  two binders, and the OTHER THREE are still unbound afterwards. Assert
  the three slots, not only the message.
- [ ] 3.6 **The second run re-solves**: three successive instants, each
  clearing what the last bound, every driven end holding the current
  instant's value, nothing refused as doubly bound.
- [ ] 3.7 **Symbolic values pass through.** With nothing bound, each of
  the m driven ends carries its own expression in the driver ids and
  `$t`, and `set_keyframe` makes them numeric. Assert the published
  strings, one per end.
- [ ] 3.8 **Order is unchanged.** A class declaring relation A, then a
  several-ended relation, then relation B solves in declaration order and
  the result does not depend on the order written — the existing
  guarantee, over the new record shape.

## 4. Red first: several ends over a repeat

- [ ] 4.1 **Six copies, four ends, six law calls.**
  `(x & y & z).drives((rods.spin, rods.lean, rods.swing, rods.rise), law=...)`
  over `.repeat(6)`: six records, each holding four driven ends of ONE
  copy; the law called six times, each with that copy's four owners;
  every copy's four coordinates bound; every copy's body placed. Assert
  the composed world matrix of at least two copies, not only the slots.
- [ ] 4.2 **The named relation reads as six records in copy order**, each
  with `direction == 'forward'`, and each `described()` naming the ends
  as written and the copy.
- [ ] 4.3 **A doubly bound copy is refused naming that copy**, and the
  other copies' records are unaffected by the message's content.
- [ ] 4.4 **Several sources, one driven end, over a repeat**:
  `(x & y & z).drives(towers.height, law=...)` over `.repeat(3)`.
- [ ] 4.5 **A zero-count repeat with several driven ends is zero
  records** — binds nothing, refuses nothing.
- [ ] 4.6 **`copy` is the node the repeated segment realized.** With a
  path continuing past the repeat (`legs.femur.lift`), the record's copy
  names the LEG, not the femur. Find the cycle-1 test that asserts this
  message text today (tasks §2.4 of `repeat-fan-out`), record what it
  asserted, and change it with its reason. The law's own argument is
  UNCHANGED: it is still the owner of the driven coordinate.

## 5. The implementation

Only after every case above has been seen red and recorded.

- [ ] 5.1 `solid_node/motion/couplings.py`: `Coordinates` (what `&`
  builds, holding raw operands in order, with `drives`, a flattening
  `__and__`, and the arithmetic refusals); `EndGroup` (what
  `coordinate_ref` returns for a `Coordinates` or a tuple, holding
  `CoordinateRef`s, with `check(role)`, `check_declared_on`,
  `described()` and `resolve`); the group refusals of design §7.
- [ ] 5.2 `RelationRecord` carries `driver_ends` and `driven_ends`
  TUPLES; `driver_end`/`driven_end` stay as properties for the
  one-to-one case; `described()` names several ends in written order.
- [ ] 5.3 `Relation.resolve`: resolve the driver ends; resolve the driven
  ends, zipping per copy when they are broadcasts; call the law once per
  record with the two shaped arguments; set `copy` from the repeated
  segment.
- [ ] 5.4 `_step_relation`, `_claim`, `_refuse`: all sources bound →
  claim all, apply, check the shape, bind all; any source unbound →
  defer; never backwards. The messages of design §6.
- [ ] 5.5 The `&` operator beside `drives`, on exactly the declarations
  that already carry `drives`: the `Coordinate` mixin in
  `solid_node/motion/ports.py`, `ChildDeclaration` and
  `RepeatDeclaration` in `solid_node/node/declarative.py`,
  `DriverDeclaration` in `solid_node/node/qualified.py`, and
  `CoordinateRef` in `couplings.py`. Every one raises the same by-name
  refusal for a non-coordinate operand.
- [ ] 5.6 Keep every existing message that does not have to change. Where
  one does, the new text is asserted by a test in tasks 1-4 — a message
  changed with no test asserting it is a message nobody reads.
- [ ] 5.7 `tests/coupling_project/`: one tree that states a two-source,
  four-target law over a repeat, so the fixture project carries the shape
  and not only the unit tests.

## 6. Nothing that is not rewritten moves

The proof, not an argument. Run ONE heavy process at a time: the VM
exhausts file descriptors under parallel CAD runs.

- [ ] 6.1 Full framework suite from the worktree,
  `.venv/bin/python -m pytest -x -q`, exact counts, compared with the
  base counts from task 0.3. Any newly red test is a stop.
- [ ] 6.2 **Pose comparison over every project on the motion layer, base
  against head** — the list `whole-tree-fixpoint` used (23 at the time it
  was written; take the current list from
  `libresolid-studio/docs/motion-general-refactor.md`), and for every
  model each manifest declares:
  `PYTHONPATH=.:<worktree> .venv/bin/python
  <shop>/docs/motion-general-refactor/capture_poses.py capture
  <module:Class> before.json` at the BASE tree, the same at the HEAD
  tree, then `compare before after`. **Maximum deviation must be 0**;
  anything else is a stop and a report, not a tolerance. Captures go
  under `openspec/changes/multi-source-multi-target-laws/evidence/poses/`,
  never into a project repository, and no project file is edited.
  **Amended 2026-09-11:** take each project's source ONCE as a
  `git -C <project> archive HEAD | tar -x` snapshot into scratch (never a
  live working tree: 3DPrintedClocks is under the pilot's own session and
  others may be under stage-B agents) and capture base and head from that
  same snapshot; record the snapshot commit per project. Suite counts,
  where taken, use each project's DECLARED runner (`solid test` where its
  pyproject or .env says so; bare pytest is the wrong runner for kossel,
  abacus, the clocks and others).
- [ ] 6.3 Cost: `pytest tests/test_couplings.py tests/test_kinematics.py`
  wall time, three runs, base against head; and `capture_poses.py` wall
  time on kossel and 3DPrintedClocks wall clock 01. A regression worse
  than 5% is reported to the pilot rather than absorbed.

## 7. The four sentences, on read-only overlays

**Never edit a project.** An overlay is a copy of the project's
simulation package OUTSIDE its repository, reached by `PYTHONPATH`,
exactly as cycles 2, 3 and 4 use it. Every overlay is thrown away after
its capture, and `git status` in each project is confirmed clean
afterwards.

- [ ] 7.1 **kossel: all four of a rod's joints from one law, under
  fan-out over six rods.** The overlay declares `spin`, `lean`, `swing`,
  `rise` on `Rod` in that order (its stage-B proposal, §"The joints", and
  ADR-093's composition order), states
  `(x & y & z).drives((rods.spin, rods.lean, rods.swing, rods.rise), law=delta_rod)`
  and `(x & y & z).drives(towers.height, law=delta_carriage_law)`, and
  deletes the corresponding loop from `Kossel.simulate()` — keeping the
  per-rod station `translate`, which is the rest placement and not a
  freedom. Capture and compare against the project's stage-A capture at
  the base: **maximum deviation 0**. This is the sentence the cycle
  exists for and the project deferred on; if it does not come out at 0,
  report the deviation and the pose before anything else is done.
- [ ] 7.2 **The Pascaline's pawl.** The overlay states
  `(count & next_count).drives(sautoir.pawl.swing, law=pawl_deflection)`
  in `Digit` and deletes the hand binding from `Digit.simulate()`. Note
  in the report that `next_count` must be BOUND when a position is built
  on its own, where today `Digit.simulate()` defaults it to `0` in a
  local variable: with several sources there is no partial application,
  and the guard moves from the local to the port. Capture and compare
  against the base: maximum deviation 0.
- [ ] 7.3 **OpenFlexure's four legs.** The overlay declares `lean` and
  `tilt` on `FlexureLeg`, states
  `(stage.slide_x & stage.slide_y).drives((driven_legs.lean, driven_legs.tilt), law=leg_lean)`
  and its `idle_legs` twin in `MainBody`, with the law reading the copy's
  `index` for the leg angle, and deletes `_lean_leg`. Capture and
  compare: maximum deviation 0. Report plainly that the ratified sighting
  wrote this as `z_motor.drives((legs.tilt, legs.lean), law=flexure)` and
  that the measured project sources it from the two STAGE coordinates
  (design §15).
- [ ] 7.4 **InMoov's hand.** The overlay states
  `(thumb & index & middle & ring & little).drives(fingers.drive, law=by_finger)`
  and its twin over `drives = Drive().repeat(5)`, plus the thumb's own
  two one-to-one relations, and deletes the ten `connect()` calls from
  `Hand.simulate()`. Capture and compare: maximum deviation 0. Report
  that the law is a SELECTOR (design §10) and that the cleaner sentence
  needs the still-open indexing finding.
- [ ] 7.5 Confirm with `git status` that nothing under `projects/` was
  written, and say so in the report.

## 8. Specs, decision record and docs

- [ ] 8.1 **Re-base the delta.** Two of the four MODIFIED requirements
  ("Relations are solved from the bound side…", "Three refusals…") were
  written on top of cycle 4's text. Before syncing, diff them against the
  baseline as it stands with cycle 4 archived and reconcile any wording
  cycle 4 changed after this proposal was written. Requirement HEADINGS
  and existing SCENARIO headings must be identical to the baseline's —
  `openspec archive` refuses a renamed scenario heading.
- [ ] 8.2 If cycle 4's ADDED requirement "Relations defer to a whole-tree
  fixpoint" still enumerates the deferral set in words that do not cover
  "a relation record whose sources are not all bound", widen that
  sentence here as a fifth MODIFIED requirement, in the words design §6
  uses.
- [ ] 8.3 A new ADR under `docs/adrs/NODE/` at the next free number: *a
  relation may name several coordinates at each end*. It records the
  spelling and the three rejected spellings with the measurement that
  rejected the free function; the law's shaped two arguments and the
  rejected positional shape; the one record holding all its ends and the
  rejected m-records; the one-direction rule; the return-shape check and
  why it is not a new error kind. Extends ADR-089, depends on ADR-096,
  cites the `whole-tree-fixpoint` ADR for the deferral. Its row in
  `docs/adrs/README.md`, in chronological order.
- [ ] 8.4 `docs/architecture.md` §Couplings: several ends at one
  relation, in the reference voice — rewrite the paragraph that says an
  end is one coordinate rather than appending to it.
- [ ] 8.5 `docs/driving.rst`: a passage for the several-ended relation
  with kossel's `for` loop beside the sentence that replaces it; the law
  protocol table (what the callable is handed, what `forward` takes and
  returns); the guidance of design §8 — a LINEAR combination is a derived
  coordinate and stays invertible, a non-linear one is a law over several
  sources and loses the reverse; and the two symbolic rules of design §9.
- [ ] 8.6 `docs/api-reference.rst` and `docs/changelog.rst` Unreleased.
  `tests/test_docs_exports.py` passes unchanged — confirm rather than
  assume.

## 9. The findings

- [ ] 9.1 `workflow/warts.md`: mark FIXED the multi-source finding in its
  four places (the Pascaline pawl entry, the kossel entry under
  "Motion catalogue refactor", OpenFlexure's sighting (b)'s last
  sentence, and InMoov's ten `connect()`s moved here by cycle 1), naming
  this change and the ADR. Record the two residual wants with their own
  findings: InMoov's per-copy source wants INDEXING A REPEAT in a class
  body (design §10), and the Pascaline's eight-way carry stays open as
  the list-held structurally-different-expression finding (design §11).
- [ ] 9.2 `workflow/docs/motion-catalogue-2.md` §3.5: it is the
  provisional note and this change is the authority for it from here on;
  record the refinement in the same shape §3.1 uses — the spelling, the
  law's shape, the corrected OpenFlexure source, and kossel's fourth
  sighting.
- [ ] 9.3 Do NOT touch `libresolid-studio/docs/motion-general-refactor.md`
  or any project. kossel's stage B is its own cycle in its own
  repository, and so are the Pascaline's, InMoov's and OpenFlexure's.

## 10. Close

- [ ] 10.1 `openspec validate --strict multi-source-multi-target-laws`.
- [ ] 10.2 Sync the delta specs into the baselines and archive the
  change, only after the orchestrating session's review.
- [ ] 10.3 Report: the suite counts, the pose comparisons, the four
  overlays with their deviations, the cost ratios, every message whose
  text changed, and every deviation from this plan with its reason.
