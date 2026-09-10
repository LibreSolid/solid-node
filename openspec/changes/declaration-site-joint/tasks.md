## 0. Before anything

- [ ] 0.1 Work only in `solid-node/WTs/motion-catalogue-2` (branch
  `motion-catalogue-2`), with `PYTHONPATH="$PWD"` and the workspace venv
  `/home/asa/devel/libresolid-studio/.venv/bin/python`. Confirm
  `python -c "import solid_node; print(solid_node.__file__)"` prints the
  WORKTREE path: the venv's editable install points at the primary
  checkout and `PYTHONPATH` must shadow it. Never run a `git` write
  command anywhere, and never write inside
  `/home/asa/devel/libresolid-studio/projects/`.
- [ ] 0.2 **Cycle 2 must be integrated AND archived first.** Confirm that
  `joint-frame-follows-declarer` has landed on this branch, that
  `Joint._carry`, `_OwnPlacedOrigin` and `_OWN_PLACED_ORIGIN` are gone
  from `solid_node/motion/joints.py`, and that
  `openspec/specs/joints/spec.md` carries the requirement "A joint is
  stated in the frame of whoever declares it". Every delta in this change
  is written against that baseline; three of the five `joints` MODIFIED
  requirements do not exist until cycle 2 archives. If it has not landed,
  STOP and report — do not implement around it.
- [ ] 0.3 Record the FULL SUITE at the base: `.venv/bin/python -m pytest
  -x -q` from the worktree, exact counts, into `evidence.md`. Any failure
  here is pre-existing and must be shown to be so before task 8.
- [ ] 0.4 **The reference poses are cycle 2's BEFORE captures, for every
  project.** Cycle 2's evidence showed that at its head EVERY project
  whose `at` restates its placement, or whose axis sits on a rotated
  body, poses WRONG until its own stage B rewrites it (its `evidence.md`
  §7 and `evidence/survey.md` §1.1, §2.2, §2.3) — not only the four it
  knowingly left wrong or refused (Inmoov-sim, the Internal Cycloidal
  Actuator, openflexure-microscope, OpenCycloid). A capture at this
  cycle's base of an unmigrated project therefore records a wrong pose
  and is worthless as a reference. The true poses are the ones cycle 2
  captured from the untouched sources on the pre-cycle-2 framework,
  still on disk at
  `/tmp/claude-1000/-home-asa-devel-libresolid-studio/51062ef7-4e6c-4bbf-8b75-db00d7533d96/scratchpad/before2/<project>-<model>-before.json`
  (one per declared model, 23 projects plus OpenCycloid). Use those as
  BEFORE for every project; say so in `evidence.md`, with each file's
  leaf and pose count. If one is missing, re-measure it from the commit
  that is cycle 2's base on this branch (47bc5bd: `repeat-fan-out`
  integrated, cycle 2 not) and record which tree it came from.
  Consequently each overlay in task 8 must carry cycle 2's own-frame
  rewrite (the `patch_<project>.py` scripts beside those captures, which
  reached 0.000e+00) BEFORE this cycle's site rewrite is applied on top;
  the comparison then measures this cycle alone.
- [ ] 0.5 Where a base pose must be re-measured, capture one project at a time, from the project's
  own root (the VM exhausts file descriptors):

      cd <project root>
      PYTHONPATH=.:<worktree> <venv>/bin/python \
        <shop>/docs/motion-general-refactor/capture_poses.py \
        capture <module:Class> <scratch>/<project>-<model>-before.json

  One capture per declared model (`pyproject.toml [tool.solid-node]`, or
  `solid models`). Record every capture's leaf and pose count. A capture
  that fails at the base is reported, not worked around.
- [ ] 0.6 Re-read `evidence/sightings.md`. It is the empirical basis of
  the whole change: if any row disagrees with the tree you find, STOP and
  report rather than adapting the design.
## 1. Red first: the carry returns

Lands in `tests/test_joints.py`. **Every case MUST be seen RED on the
current tree before task 7 begins, and the RED text recorded in
`evidence.md`.** A case red only with an `AssertionError` about numbers
must also record the numbers it read today.

- [ ] 1.1 **Thor's elbow, stated by its parent.** The inverse of cycle
  2's task 1.4, against the same two pinned numbers. A parent placing a
  forearm with `rotate(90, [1, 0, 0])` then `translate([0, 241.5, 68])`
  and declaring `forearm = Forearm(elbow=Revolute(axis=(0, 0, 1), at=(0, 241.5, 68), range=…, unit='deg'))`
  produces, at 30 degrees, exactly the operations cycle 2's fixture
  produces from `axis=(0, 1, 0), at=(0, 0, 81.5)` on the class:
  `translate([0, 0, -81.5])`, `rotate(30, [0, 1, 0])`,
  `translate([0, 0, 81.5])`, then the two rest operations. RED — today
  the keyword is refused at class definition. **This is the acceptance
  cycle 2 pinned for the restored arithmetic; if the carry cannot
  reproduce it to the same tolerance, STOP and report.**
- [ ] 1.2 **A site joint anchors on the PARENT's origin.** A parent
  translating a child by `[0, 3.9, 0]` and declaring
  `child = Screw(orbit=Revolute(axis=(0, 0, 1), unit='deg'))`: bound, the
  child is carried round the line through the PARENT's origin at radius
  3.9, not turned on its own centre. RED.
- [ ] 1.3 **One declaration, opposed placements, opposite own-frame
  axes.** Two copies of one class placed with `rotate(90, [1, 0, 0])` and
  `rotate(-90, [1, 0, 0])`, one site joint stating one parent-frame axis,
  both bound to the same angle: the two published rotations carry
  opposite own-frame axes and the two bodies turn the same way in the
  parent's frame. RED. This is Prusa's guides, hangprinter's rollers and
  openvmp's legs in one case.
- [ ] 1.4 **A site joint's run sits at its own slot, inside the rest
  placement.** A class declaring `spin`, a site declaring `orbit`, the
  parent translating the child: the operations read `spin` run, `orbit`
  run, rest placement — and the composed pose equals the pose the same
  two joints produce when BOTH are declared on the class with the anchor
  hand-inverted. RED. This is ADR-093's sighting 4 and OpenCycloid's disk.
- [ ] 1.5 **A site joint of a name the class declares keeps that slot.**
  A class declaring `pip` then `mcp`, a site redeclaring both: `pip`
  innermost, the site's arguments used, and the node's joint enumeration
  reads `pip`, `mcp`. RED.
- [ ] 1.6 **A site joint of a new name comes last, in keyword order.** A
  class declaring `spin`, a site passing `orbit=` then `lift=`:
  enumeration `spin`, `orbit`, `lift`. RED.
- [ ] 1.7 **A symbolic rest placement refuses a SITE joint and not a
  class one.** A body whose rest placement carries a symbolic value: its
  class-declared joint binds and places (cycle 2's relaxation intact), and
  binding a site-declared joint raises naming the node, the joint and the
  operation. RED for the second half; the first half must stay green
  UNEDITED.
- [ ] 1.8 **A site `Free` floats against the parent's frame.** A parent
  rotating a child, declaring `pose=Free()` at the site, binding `x`: the
  child displaces along the PARENT's x̂. RED. Assert alongside that cycle
  2's class-declared `Free` cases pass unedited.
- [ ] 1.9 **A site `Prismatic`'s axis is carried and its anchor is
  inert.** A rotated child with `travel=Prismatic(axis=(1, 0, 0), at=P)`
  at the site: the published translation runs along the parent's x̂, and
  the same case with a different `at` produces identical operations. RED.

## 2. Red first: `Orbit` and the returned sentinel

- [ ] 2.1 **A defaulted site `carries` is the CHILD's own origin.** A
  parent translating a disk by `[0, -2.5, 0]` and declaring
  `disk = Disk(orbit=Orbit(axis=(0, 0, 1), unit='deg'))`: bound to 90, the
  disk's own origin has travelled a quarter of the circle of radius 2.5
  about the line through the PARENT's origin, attitude unchanged, and
  neither radius nor phase was written. RED. **This is OpenCycloid's disk
  and it is the case that decides the default; if it cannot be made
  green, the design is wrong and the cycle stops.**
- [ ] 2.2 **Six copies, one declaration, six derived phases.** Six copies
  placed round a circle at 60 degree spacing with one site `Orbit` and one
  broadcast: six distinct phases, one radius, nothing written per copy.
  RED. OpenCycloid's output pins.
- [ ] 2.3 **A written site `carries` is a point of the PARENT's frame.**
  A disk placed off the axis with `carries=` naming the bore centre in the
  parent's frame: the derived radius is the bore centre's distance from
  the axis, not the disk origin's. RED. The Internal Cycloidal Actuator.
- [ ] 2.4 **A site `Orbit` whose defaulted carried point lands on the
  line is still refused at binding**, naming node, joint, axis, anchor,
  carried point and the radius of zero — the case of a parent that places
  the child ON the line it states.
- [ ] 2.5 **Cycle 2's class-declared `Orbit` cases pass UNEDITED**,
  including `ProjectAlgebraTest` at its ADR-094 acceptance (rotation block
  `atol=0`, position `atol=1e-9`). If any needs an edit, stop and report:
  that would mean this change reached into the class rule.

## 3. Red first: the declaration, and what it refuses

Lands in `tests/test_declarative.py`.

- [ ] 3.1 **A site joint is not a parameter and not identity.** A
  non-declarative child class with a positional argument, declared with a
  joint keyword: the constructor sees only its own arguments, the
  `uniq_id` equals the one without the keyword, and two siblings
  differing only in their joints share one artifact key. RED.
- [ ] 3.2 **A wiring still means a wiring.** A keyword whose value is a
  coordinate declared on the declaring class keeps today's behaviour,
  including the refusal when the child declares no such name. Must pass
  with only the message unchanged.
- [ ] 3.3 **Every refusal of design decision 10**, one case each, each
  asserting the message names the declaring class, the attribute, the
  child class, the keyword and what the child declares: a port; a derived
  coordinate; a declared parameter; a named parameter of a
  non-declarative child's `__init__`; a method or property; a child
  declaration; a joint declared on a third class; two site joints of one
  name through `**{...}`; a site joint colliding with a coordinate a
  sibling site `Free` owns. RED.
- [ ] 3.4 **A site joint on a `.repeat()` and on a literal list.** Every
  copy carries the freedom, all copies resolve identical arguments, and
  each is carried through its own placement. RED.
- [ ] 3.5 **A callable is handed the declaring parent.** Two parents with
  different parameters declaring one child class with a callable `axis`
  and `at`: each callable was called once per realized child, with the
  PARENT, and the two children carry different arguments. Assert the
  parent's `render()` has not run at that moment, and that reading a
  later-declared sibling from the callable raises. RED.
- [ ] 3.6 **A copy's `index` is NOT reachable from a site callable.**
  A site joint on a `.repeat()` whose callable tries to read a copy:
  refused or unavailable by construction, and the test states why (design
  decision 5) so a later reader sees the choice rather than an omission.

## 4. Green by construction: the rules that must already answer

These are not new machinery; they are the reason the mechanism was
chosen. Each is a test that an EXISTING rule answers for a site-declared
joint, and each must be seen RED first (today the keyword is refused at
class definition) and then green with no edit to the module it exercises.

- [ ] 4.1 **The descriptor protocol.** On a child whose `turn` came from
  its declaration site: `self.turn` yields the same `BoundPort` a
  class-declared joint yields; `self.turn = value` binds through the one
  binding path and places the body; a second assignment leaves ONE
  motion; and a `Free` at a site answers to its dotted names.
- [ ] 4.2 **`declared_ports` and `declared_joints`** of the realized
  child's CLASS report the site's joint, in composition order, with its
  domain and unit, constructing nothing. Assert both, and assert the
  WRITTEN class still reports only what it declares.
- [ ] 4.3 **`get_coordinate` / `set_coordinate`** answer for a site name,
  including a dotted one, and still refuse a name nothing declares by
  naming the node, the name and what is reported. `solid_node/motion/ports.py`
  MUST NOT be edited for this to pass; if it must be, stop and report.
- [ ] 4.4 **A relation names a site coordinate by path**, driver and
  driven (OMX's `left.travel.drives(right.travel)`), and a broadcast
  names one through a `.repeat()` (OpenCycloid's
  `carrier.spin.drives(pins.orbit)`). `solid_node/motion/couplings.py`
  MUST NOT be edited; if it must be, stop and report.
- [ ] 4.5 **A bare child end means the one joint the declaration gives
  it**, and a child with a class joint AND a different site joint is
  refused as a two-joint node by name.
- [ ] 4.6 **A path naming a keyword no site passed is refused at class
  definition**, naming the path, the segment and what the class declares.
- [ ] 4.7 **`capture_poses.py` sees a site joint.** Build a two-node
  fixture with one site joint and run the campaign's own script over it;
  it walks the reported coordinate names, so this is the test that the
  pose evidence for this cycle is possible at all.

## 5. Red first: what the specialization must and must not be

- [ ] 5.1 **Identity is unchanged.** Two children of one class, declared
  at two sites that pass different joints, and a third declared with
  none: all three share one `uniq_id`, one `scad_file` and one
  `stl_file`. RED. This is the rule the copied qualified name exists for.
- [ ] 5.2 **`isinstance` holds and the class reads as the written one.**
  `isinstance(child, ZScrew)`; `type(child).__name__`,
  `__qualname__` and `__module__` are `ZScrew`'s;
  `inspect.getfile(type(child))` and `source_scope` name `ZScrew`'s own
  file. RED.
- [ ] 5.3 **One specialization per declaration site.** All six copies of
  a `.repeat(6)` are instances of ONE class; two different sites
  declaring the same class with the same joint text get two classes and
  still share one `uniq_id`. RED.
- [ ] 5.4 **The specialization is invisible to model discovery.**
  `solid_node.node.sources.node_classes_in` and
  `solid_node.core.loader._defined_classes` over the module that defines
  the parent report the written classes and NOT the specialization, so
  `solid models` and every reference resolver are unaffected. RED.
- [ ] 5.5 **A class with its own metaclass specializes.** The
  `CheckCQEditor`-shaped case named in `NodeMeta`'s docstring: the
  specialization is built through `type(cls)`, not through `NodeMeta`
  directly. RED.
- [ ] 5.6 **Record the one identity check the change loosens.**
  `solid_node/node/internal.py:166` refuses a render returning its own
  type via `type(child) is type(self)`; a site-jointed child of a
  parent's own class now slips past it. Add a test that PINS the current
  behaviour of that guard for the ordinary case, and record the loosening
  in `evidence.md` and in the ADR rather than fixing it here.
- [ ] 5.7 **Class-keyed caches stay bounded.** After realizing a tree
  with n declaration sites carrying joints, `_declared_cache`,
  `_children_cache`, `_relations_cache` and the parameter cache have
  grown by at most n entries, not by one per realized child. RED.

## 6. The change

Two modules. `solid_node/motion/ports.py` and
`solid_node/motion/couplings.py` are NOT edited, and task 4 is what says
so.

- [ ] 6.1 `solid_node/motion/joints.py`: a joint carries whether it was
  declared at a SITE. Restore `_carry` from cycle 2's deleted
  implementation, applied only to a site-declared joint, with its
  refusal naming the node, the joint and the operation. Restore
  `_OwnPlacedOrigin`/`_OWN_PLACED_ORIGIN` as the SITE default of
  `Orbit.carries` only, with a docstring saying it was deleted in cycle 2
  and why it is back. `resolve_declared_joints` SKIPS a site-declared
  joint, which is resolved against the parent instead (6.2). The module
  docstring states both halves of the frame rule. No new exported name.
- [ ] 6.2 `solid_node/node/declarative.py`: split a coordinate-valued
  keyword into wiring and site joint by the VALUE; build the
  specialization for a declaration carrying site joints, copying
  `__name__`, `__qualname__`, `__module__` and `__doc__`, through
  `type(node_class)` so a project metaclass is preserved; hold it as the
  declaration's `node_class` so `_check_wiring`, `read_through` and every
  path reading see it; refuse the keywords of decision 10; resolve the
  site's joints against the realized parent in `realize`.
  **Build the specialization in `ChildDeclaration.__init__`, not in
  `__set_name__`**: a declaration held in a literal list never receives
  `__set_name__` (which is also why a wiring in a list-held declaration
  goes unvalidated today), and the specialization must exist before any
  class body reads a path through the declaration. Refusals that need the
  DECLARING class's name are added at `__set_name__`, where it is known.
- [ ] 6.3 `solid_node/node/base.py`: `ChildDeclaration.realize` receives
  the realized PARENT — it receives the declaring class's NAME today, a
  string, and `_record_wiring`'s message must keep reading exactly as it
  does. Nothing else in `base.py` changes; in particular no attribute
  hook is added.
- [ ] 6.4 Grep the framework for every reader of
  `declared_joints(type(node))`, `declared_ports(type(node))` and
  `type(node)` generally, and record in `evidence.md` which now see a
  specialization and that each is correct to. `solid_node/node/flexible.py`
  reads `declared_ports(type(self))` in four places and now sees a site
  joint on a flexible leaf, which is the wanted answer.

## 7. Green, and the guard rails

- [ ] 7.1 Every case of tasks 1-5 green.
- [ ] 7.2 FULL SUITE: `.venv/bin/python -m pytest -x -q` from the
  worktree, exact counts in `evidence.md`, matched against 0.3. Any new
  failure stops the cycle.
- [ ] 7.3 **No test of ADR-088, ADR-093, ADR-094, ADR-095 or ADR-096 was
  edited.** List in `evidence.md` every test file and test name touched,
  with the reason. Cycle 2's own cases — `FrameCarryTest`,
  `NumericHygieneTest`, `CompositionOrderTest`, the hexapod `Free`
  fixtures, `ProjectAlgebraTest` — must pass UNEDITED: this cycle adds a
  second declaration site and changes nothing about the first, and an
  edit there is evidence it reached further than the design says.
- [ ] 7.4 Assert the joints module's import cost is unchanged except for
  `numpy`, which returns with `_carry` (ADR-087), and record it.

## 8. The evidence: the catalogue, before and after

The implementer MUST NOT edit any project repository. The overlay is a
throwaway copy, made read-only from the project, as cycle 2 does:

    SCRATCH=<a scratch dir outside every repository>
    git -C <project> archive HEAD | tar -x -C $SCRATCH/<project>
    ln -s <project>/<asset dir> $SCRATCH/<project>/<asset dir>

Then apply that project's rewrites, from `evidence/sightings.md`, to the
copy's `.py` files ONLY, and capture as in 0.5. One project at a time;
delete each copy after its comparison. Confirm before every capture that
`git -C <project> status --porcelain` is unchanged from what 0.5
recorded.

- [ ] 8.1 **The four projects cycle 2 leaves broken, against their
  pre-cycle-2 reference (0.4).** OpenCycloid (4 site declarations, 12
  bodies), Internal-Cycloidal-Actuator (2), Inmoov-sim (7), and
  openflexure-microscope (1). **Required result: maximum deviation 0** on
  every model of every one. These are the rows that prove the rule is not
  lossy; if any cannot be brought to 0, the design is wrong and the cycle
  stops. Record, per project, that the overlay bound the coordinates cycle
  2 refuses and that they now bind.
- [ ] 8.2 **For the Internal Cycloidal Actuator, prove no forbidden
  literal is typed.** Its ratified spec says *"Neither the rest bore
  centre nor the journal position SHALL be written as a literal anywhere
  in the project"*. Show the overlay's diff in full and show that the site
  `carries=` is the project's own derived expression, not a number; and
  show that `spin`'s new anchor is `BORE_AXIS_POINT`, the project's own
  spec literal. Record the diff in `evidence.md` verbatim, because it is
  what a reviewer of that project's stage B will check first.
- [ ] 8.3 **For OpenCycloid, prove the derived numbers stayed derived.**
  Grep the overlay for the radii (2.5), the phases (∓90, and the six
  60-degree steps) and the eccentric offsets: none may appear as a new
  literal. Record the four site declarations' full text.
- [ ] 8.4 **The five axes and the four subclasses-for-metadata, against
  this cycle's own base (0.4).** Prusa3-vanilla (both guide pairs),
  hangprinter (`MotorGear`, `RollerBearing`), openvmp (`Wheel`,
  `CameraArm`, `Leg`), open_manipulator (`LeftFinger`, `RightFinger`),
  Inmoov-sim's wrist axle. **Required result: maximum deviation 0.**
  Record, per project, the classes and attributes the overlay DELETED —
  that count is the migration's own measure.
- [ ] 8.5 **openvmp's data-built parts — a CYCLE-2 overlay, run here to
  prove the claim.** This cycle adds nothing for them
  (`evidence/sightings.md` §6). In the overlay add a project-side
  `TurningPart(StepPart)` with `spin_axis`/`spin_point` parameters and
  ADR-088's callable, build it from the existing loop at the eight
  `spin()` sites, delete `spin()`, `axis_of` and `transform_of`, and
  compare. **Required result: maximum deviation 0** over all 82 placed
  parts. If it cannot reproduce `spin()` exactly, say so and stop: the
  design's decision 9 would be wrong and the data-built case would need
  an API after all.
- [ ] 8.6 **Every other project on the motion layer, unchanged, at this
  cycle's base and head.** No overlay, no rewrite: the change touches
  `joints.py`, `declarative.py` and one signature in `base.py`, and every
  declaration in the catalogue passes through the last two, so the
  no-regression guard is the whole catalogue. **Required result: maximum
  deviation 0** on every model of every project the tracker lists. A
  non-zero deviation on a project this cycle does not touch is a defect in
  the change and stops the cycle.
- [ ] 8.7 Run
  `Robots-Bipedal/YouCanBuildBiPed/simulation/test_assembly.py::test_motion_uses_current_revolute_joints_at_measured_pivots`
  against its overlay: it is the only test in the catalogue that reads
  `.axis` and `.at` off realized joints. It must stay green unedited.
- [ ] 8.8 Record in `evidence.md`, per project: which base the reference
  came from (0.4), the model list, the pose and leaf counts, the maximum
  deviation, and the exact diff of the rewrite. That diff is the migration
  guide the projects' own stage-B cycles will follow.

## 9. Documentation and the record

- [ ] 9.1 `docs/driving.rst`, the joints section: the second half of the
  frame rule, with the two defaults side by side and the sentence a reader
  will get wrong stated plainly — at a site, a child the parent translates
  SWINGS about the parent's origin. A worked example of each of the three
  shapes: the shared catalogue class, the `.repeat()`, and the `Orbit`
  whose carried point is defaulted.
- [ ] 9.2 `docs/changelog.rst`, Unreleased: the entry, addressed to the
  catalogue. It must state which frame each site means, what a defaulted
  `at` and a defaulted `carries` mean, that a site joint replaces a class
  joint of the same name in that name's slot, and that a site joint needs
  a numerically evaluable rest placement where a class joint does not.
- [ ] 9.3 The ADR: a new NODE ADR, "A joint may be declared where a child
  is placed". It must record: the innermost-versus-outermost choice and
  the five reasons (design decision 3), with the equivalence `J·M ≡
  M·(M⁻¹JM)` stated so a later reader knows the choice was not about
  geometry; the return of `_carry` and of ADR-094's sentinel, and exactly
  how far each returns; the slot rule as an extension of ADR-093; the
  callable's one argument and the deliberate absence of the copy; the
  refusal that returns for site joints only; the specialization —
  why the qualified name is copied deliberately (a joint is not
  identity), what it costs (`type(x) is C`, the class-keyed caches, model
  discovery), and why every slot, clash, descriptor, enumeration and path
  rule is then delivered by machinery that already exists; the rejected
  instance-level machinery and its four extra public surfaces; and the
  measurement that the data-built case needs no new API at all.
- [ ] 9.4 Update `docs/adrs/README.md` and `docs/architecture.md` where
  they describe where a joint is declared.
- [ ] 9.5 `openspec validate --strict declaration-site-joint`;
  `openspec archive` when the pilot says so.
- [ ] 9.6 File in `workflow/warts.md`:
  - close the declaration-site finding with this cycle's name, its
    fourteen sightings and the four subclasses deleted;
  - correct the plan note's record: two of §3.3's three example sentences
    and two of its four validation projects are cycle 2's
    (`evidence/sightings.md` §5), and its fourth sentence is short of a
    `carries=`;
  - file NEW: **a parent's hand-written `self.child.rotate(...)` in its
    own `simulate()` is read in the CHILD's frame, while a site joint the
    same parent declares is read in the PARENT's** — the frame does not
    follow the declarer for hand-written motion, and after this cycle a
    project can write both on one child and get two frames from one
    author. State it in those words; it is a finding this cycle exposes
    and does not fix;
  - file NEW: **a relation cannot name a child a loop builds from data**
    (openvmp, with its own written-down sentence), which no cycle in this
    campaign closes — and record that the OTHER half of that sighting,
    giving those 82 parts real coordinates, is a cycle-2 migration
    (`evidence/sightings.md` §6);
  - file NEW: **`type(x) is C` no longer holds for a child whose
    declaration site gave it a joint**, with `internal.py:166`'s
    own-type guard named as the one place in the framework it reaches
    (task 5.6).
