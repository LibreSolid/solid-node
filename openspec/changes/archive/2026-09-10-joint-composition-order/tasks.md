## 1. Red first: the composition order

All of this lands in `tests/test_joints.py` §1.6 ("Motion discipline"),
beside the existing `Bench` and `SelfTurning` fixtures, and uses the
module's existing helpers `serialized(node)`, `motions(node)` and
`numbers(...)`. Every case below MUST be run and seen RED on the current
tree before task 2 begins, and the RED message recorded in the cycle's
evidence — a case that is green before the change is testing nothing.

Assert the composed MATRIX, not only the operations list, wherever an
order is at stake: a list assertion alone would pass for a wrong
composition if the operations happened to commute, and the fixtures are
chosen so they do not. Use `solid_node.node.base._compose_world_matrix`
(or the node's own composed matrix) against a hand-written NumPy product,
with `numpy.testing.assert_allclose(..., atol=0)` where the arithmetic is
exact and a stated tolerance otherwise.

- [x] 1.1 **Fixtures.** A `TwoFreedom` node class declaring, in this
  order, `pivot = Revolute(axis=(0, 0, 1), at=<away from the placed
  origin>)` and `slide = Prismatic(axis=(0, 1, 0))`, chosen so the two do
  NOT commute (assert that first, in the fixture's own test: the two
  composition orders give different matrices — a fixture that stops
  exercising the question must fail loudly, not pass vacuously). Two
  benches placing it identically and binding the two joints in opposite
  orders.
- [x] 1.2 **Two joints, either binding order.** Both benches produce the
  same `serialized(node)` — the pivot's run first, innermost, then the
  slide's — and the same composed matrix, equal to the hand-composed
  `T_slide · R_pivot` product. RED: today the lists differ and one matrix
  is wrong.
- [x] 1.3 **Relation-bound joints.** The cycloidal case: `spin` then
  `orbit`, two `Revolute`s on one body, both driven by `drives(...)` from
  one shaft coordinate (one of them with a ratio, so the two values
  differ). Assert the pose is `R_orbit · R_spin` and that swapping the
  two relation STATEMENTS in the class body changes nothing. RED.
- [x] 1.4 **Re-binding one joint of several.** Bind `pivot`, bind
  `slide`, re-bind `pivot` to a new value. Assert one motion run per
  joint, the pivot's still innermost, and the matrix equal to binding the
  two once in either order. RED.
- [x] 1.5 **Inheritance and the enumerator.** A base declaring `a` then
  `b`; a subclass declaring `c` and redeclaring `a` with a different
  anchor. Assert `list(declared_joints(Subclass))` reads `a, b, c` (green
  today — this is the promise decision 1 makes normative, and it must be
  asserted here so a later refactor of the enumerator cannot silently
  change geometry) AND that the composed pose is `c ∘ b ∘ a` with `a`
  about the SUBCLASS's anchor. The pose half is RED.
- [x] 1.6 **Sweep across runs, with the application order reversed
  between them.** The obvious fixture — bind one end by hand and let a
  relation bind it at the next instant — CANNOT be written: a coordinate
  a wiring or a relation binds may not also be bound by hand, which
  `tests/test_joints.py::WiringTest::test_binding_a_wired_child_end_by_hand_is_refused`
  pins and the couplings spec refuses. Use instead: ONE assembly binding
  BOTH joints by hand in its own `simulate()`, with the binding order
  chosen by a driver the test sets —

      def simulate(self):
          if self.order < 0.5:
              self.body.pivot = self.a; self.body.slide = self.b
          else:
              self.body.slide = self.b; self.body.pivot = self.a

  Walk it at `order=0`, then at `order=1`, so `_sweep` drops both runs
  and they are re-applied in the opposite order. Assert an identical
  `serialized(node)` and an identical composed matrix at both walks, and
  one motion run per joint. **RED today** for a concrete reason worth
  stating in the test: both bindings are the author's own, `clear_solved`
  never touches them, and `_insert_motion` appends each at the end of the
  motion block — so today the second walk genuinely produces
  `[slide, pivot]` where the first produced `[pivot, slide]`, and the two
  matrices differ because the fixture's joints do not commute (1.1).
  A time-branched variant (`if self.time < 1:`) would test the same
  thing; the driver keeps the test's control explicit and off the time
  base.
- [x] 1.7 **Two independent animators on one node.** Assembly A binds the
  first-declared joint, assembly B the second. Walk A, then B, then A
  again. Assert A's operations are innermost of B's before and after A's
  sweep, and that each sweep removed only what it tagged (the existing
  `tests/test_animator_tag.py` semantics). RED on the third walk.
- [x] 1.8 **Contiguity, and the guard for the stacked cycles.** A
  three-operation `Revolute` (off-origin anchor) declared between a
  `Prismatic` and another joint, with a hand-written rotation as well:
  assert its three operations are one unbroken run at its own slot. This
  is what `orbit-joint` and `free-joint` rely on; write it now.
- [x] 1.9 **Hand-written motion is outside the joint block.** A bench
  that rotates a child by hand, binds its joint, and translates it by
  hand again: assert the order is the joint's run, then the rotation,
  then the translation, then the rest placement. RED.
- [x] 1.10 **The two existing assertions invert.** MODIFY, do not delete:
  - `MotionDisciplineTest::test_joint_motion_is_innermost_and_tagged` —
    `Bench` rotates by hand (10) then binds `swing` (25), so
    `['r','t','r','t','t']` becomes `['t','r','t','r','t']`. Assert the
    ANGLES too, not just the kinds, so a coincidental match cannot pass.
  - `MotionDisciplineTest::test_hand_written_and_joint_motion_coexist_in_order`
    — `['10', '25']` becomes `['25', '10']`. Rename it to say what it now
    tests (the joint block is innermost), and keep a sentence in the
    method saying which order it replaced, so a future accidental revert
    reads as a revert.
- [x] 1.11 **Serialization.** `solid_node.core.serializer.serialize` on a
  node with two bound joints and one hand-written motion publishes the
  operations in that order, and no new key appears in the document. RED
  in the order, green in the absence of new keys.

## 2. The seam

- [x] 2.1 `solid_node/node/base.py`: replace `apply_motion(node,
  operation)` with `apply_joint_motion(node, operations, slot)`. It
  computes the insertion index as the length of the prefix of
  `node.operations` whose entries carry `_motion` AND a `_joint_slot`
  whose value is `<= slot`; inserts the run there; sets `_motion = True`
  and `_joint_slot = slot` on each; and tags each through
  `_tag_operation` when a phase is current, exactly as `apply_motion`
  does today. Keep and extend `apply_motion`'s docstring — the reason a
  joint never goes through `_place_operation` is unchanged and is the
  first thing the next reader needs.
- [x] 2.2 `solid_node/node/base.py`: update the motion-block comment
  above `_insert_motion` (the block beginning "While an AssemblyNode
  lifecycle method runs…") to state the two-part motion block — joints by
  declaration slot, then hand-written in call order — and why. Leave
  `_insert_motion` itself unchanged and say in its docstring that it is
  now the HAND-WRITTEN motion path, joints having their own.
- [x] 2.3 `solid_node/motion/joints.py`: `Joint.place` computes its slot
  from `declared_joints(type(node))` (a list index into the per-class
  cache — do not add a second cache) and calls `apply_joint_motion` once
  with the whole `placement(...)` list. `Joint.clear` is unchanged.
- [x] 2.4 `solid_node/motion/joints.py`: state the ordering contract in
  the module docstring and in `declared_joints`'s docstring — the
  enumerator's order IS the composition order, and that is why it is
  walked base-first with a redeclaration keeping its key's position.
  `docs/api-reference.rst:262` autodocs `declared_joints`, so that
  docstring is what a reader of the published API reference sees: put the
  order contract in its FIRST sentence, not in a trailing note.
- [x] 2.5 Run task 1. Everything green. Then the whole suite:
  `.venv/bin/python -m pytest` from the worktree with `PYTHONPATH="$PWD"`.
  `tests/test_couplings.py`, `tests/test_animator_tag.py`,
  `tests/test_simulate_split.py` and `tests/test_ports.py` must be green
  without edits; if any of them needs an edit, stop and say why before
  making it — an unexpected edit there is a finding, not a chore.

## 3. Specs and decision record

- [x] 3.1 `docs/adrs/NODE/ADR-093-<slug>.md`: "The joints of one class
  compose in declaration order". Status **Accepted**, **Extends**
  ADR-088, **Depends on** ADR-023 (kinematic operations and
  driver-tagged idempotent renders), ADR-028 (single-matrix world
  composition) and ADR-066 (render at rest, simulate per instant);
  related to ADR-089. Record in its Context the seven sightings and that
  sighting 4 named this contract the minimal unblocker; in its Decision
  the rule and the rejected ordering keyword; in its Consequences that
  `declared_joints`'s order becomes load-bearing, that hand-written
  motion moves outside the joint block, and the measured result of task 5.
  Name the seam it replaces: `apply_motion` becomes `apply_joint_motion`.
  ADR-088's own mention of `apply_motion` stays as written — an ADR is a
  record of a decision at its date, not a live reference.
- [x] 3.2 `docs/adrs/README.md`: the ADR-093 row in the NODE section in
  chronological order, and "extended by 093" on ADR-088's row.
- [x] 3.3 `docs/architecture.md` §Joints (lines 484-512): rewrite the
  closing sentence "hand-written motion and joint motion coexist on one
  node" to the two-part motion block, and add one sentence that a
  class's joints compose in declaration order. **Line 505 cites the seam
  by name** — "`apply_motion` in `node/base.py`, the joint's own seam" —
  and becomes `apply_joint_motion`; the parenthetical reason it gives
  (`_place_operation` appends outside a phase and a carried line must
  stay innermost) is still exactly right and stays. Rewrite the affected
  passage rather than appending a note.
- [x] 3.4 `docs/changelog.rst`, `Unreleased` section: one entry at the
  top, in the form the ADR-090/091/092 entries there already use — what
  changed and why it was wrong before, what a project now writes, what
  does NOT change (no public surface, no document format, no viewer, no
  deprecation), and the closing parenthesis naming the OpenSpec change
  and the ADR: "(OpenSpec change ``joint-composition-order``; ADR-093,
  extending ADR-088.)". Say plainly that hand-written motion now composes
  outside the joint block, and carry the measured result of task 5 — a
  changelog entry that hides a visible behaviour change is the one thing
  this entry must not do.
- [x] 3.5 `docs/driving.rst`, the paragraph ending "both forms may sit on
  one node" (around line 262): add one or two sentences saying that a
  class's joints compose in DECLARATION order, the first declared
  innermost, so a reader sees how the freedoms stack by reading the class
  top to bottom; and that hand-written motion composes outside the whole
  joint block. Keep the existing "nothing is deprecated" sentence — it is
  still true.
- [x] 3.6 Sync the delta into `openspec/specs/joints/spec.md`.
  **NOT DONE, deliberately:** the implementer reports first and the
  orchestrator syncs and archives after review.

## 4. The plan note and the findings

- [x] 4.1 `workflow/docs/composed-joints.md`: mark §4 taken up by this
  cycle, and note that the OpenSpec change is now the authority for it.
  Leave §5 and §6 provisional.
- [x] 4.2 `workflow/warts.md`: mark the seven composition-order sightings
  **Fixed** by cycle `joint-composition-order` (ADR-093), in place, each
  keeping its original evidence. Do NOT mark the other findings those
  same entries carry — the `.repeat()` fan-out, the own-placed-origin
  anchor, the multi-source relation, the joint on a data-built child, the
  carried body — which stay open, and say so explicitly beside each
  project that waits on more than this one.
- [x] 4.3 `libresolid-studio/docs/motion-general-refactor.md` is SHOP
  material in a different repository. Do not edit it from this cycle;
  report what it needs and let the pilot place it. **Not edited.** What
  it needs, for the pilot to place: the `deferred` rows for
  Internal-Cycloidal-Actuator (blocked on this contract ALONE — it is
  now refactorable at stage B), kossel, Inmoov-sim, hexapod_spiderbot,
  OpenCycloid, YouCanBuildDog, v8-engine and fender-bender should record
  that the composition-order blocker is lifted by ADR-093, and which
  further primitive each still waits on (Orbit for OpenCycloid,
  YouCanBuildDog and v8-engine; the multi-source relation for kossel;
  the conditional-placement declaration-site joint for Inmoov-sim; the
  own-placed-origin anchor and the `.repeat()` fan-out for
  fender-bender and abacus; `Free`, optionally, for the hexapod). The
  per-project detail is in `workflow/warts.md`, updated in place by
  task 4.2.

## 5. Evidence: the catalogue's poses do not move

The one behaviour that can change a catalogue pose is a hand-written
simulate-phase motion on a node that also carries a bound joint. The
source survey in `workflow/docs/composed-joints.md` §4.7 found zero such
sites in the sixteen migrated projects. That is a prediction; this task
is the evidence, and it is the acceptance for the whole cycle.

- [x] 5.1 **Which framework tree each capture runs against.** The
  workspace venv installs `solid_node` EDITABLE from the PRIMARY checkout
  — `.venv/.../__editable__.solid_node-0.6.0.pth` resolves
  `import solid_node` to
  `/home/asa/devel/libresolid-studio/solid-node/solid_node/__init__.py` —
  so a project run with `PYTHONPATH=.` alone tests main 92f4292 whatever
  worktree the shell is in. That is right for the BEFORE capture and
  silently wrong for the AFTER one. Therefore:

  - **BEFORE**: `PYTHONPATH=.` — the primary checkout, which IS the
    recorded base 92f4292. Confirm it is at 92f4292 and clean before
    starting, and do not write to it.
  - **AFTER**: `PYTHONPATH=.:/home/asa/devel/libresolid-studio/solid-node/WTs/composed-joints`
    so the worktree shadows the editable install.
  - **Verify before every capture run, under that exact PYTHONPATH**:

        python -c "import solid_node; print(solid_node.__file__)"

    and record the path it printed beside the capture. A capture whose
    verification line was not taken, or printed the wrong tree, is
    discarded and re-run — not reasoned about.
  - Run the captures **sequentially, never in parallel**: the VM
    exhausts under concurrent CAD runs (the `virtiofs` descriptor
    exhaustion recorded for this workspace), and an EMFILE mid-capture
    produces a short file, not an error.

- [x] 5.1a For each of the sixteen migrated projects named in
  `libresolid-studio/docs/motion-general-refactor.md`, capture poses
  BEFORE and AFTER under the two PYTHONPATHs above, with
  `libresolid-studio/docs/motion-general-refactor/capture_poses.py`
  (`capture <module:Class> out.json`, then `compare before after`), run
  from the project root with the workspace venv. Capture every model the
  tracker's row names, not only the first.
- [x] 5.2 **Acceptance: maximum deviation 0** on every project and every
  model — not a tolerance. Record the per-project number in the cycle's
  evidence file, with the project's commit, the framework commit each
  capture was taken at, and the `solid_node.__file__` line each run
  printed.
- [x] 5.3 Any non-zero deviation STOPS the cycle: report which node, which
  joint, which hand-written call, and what the two composition orders
  give, and return the choice to the pilot. Do not loosen the rule to
  absorb it, and do not edit the project.
- [x] 5.4 Note honestly in the evidence what this does NOT cover: the
  nine deferred projects (they will be refactored ONTO this contract, so
  their poses are stage B's acceptance, not this cycle's); any project
  whose suite was already red at baseline (the tracker names them:
  BCN3D-Moveo, abacus, fender-bender, pascaline, Prusa3-vanilla,
  openflexure-microscope, v8-engine); and pixels, which no pose
  comparison replaces.
- [x] 5.5 Pixels: `solid snapshot` on two models that carry more than one
  joint on a body after the change, before and after, and look at them.
  A green suite does not replace snapshot inspection.

## 6. Open questions to close or carry

- [x] 6.1 **The same-slot survivor.** Write the test that restores a node
  checkpoint between two bindings of one joint and read what the list
  does. If a stale same-slot operation can survive both `_sweep` and
  `Joint.clear`, decide `<` versus `<=` on the evidence and state it in
  the spec; if it cannot, say so in the design and leave `<=`.
- [x] 6.2 **A legacy render inside a joint's frame.** Determine whether
  any catalogue project still triggers the legacy-render `FutureWarning`
  on a node that also declares a joint. If one does, it is a new finding
  for `workflow/warts.md`, not work for this cycle.
- [x] 6.3 Confirm before archiving that neither open question changed the
  ratified behaviour; if either did, the spec delta is revised and
  re-ratified rather than quietly corrected.
