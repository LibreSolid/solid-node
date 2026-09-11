

# snappy-reprap

- The shared .venv broke at 00:00 UTC while my first build ran: something else pip-installed ocp_vscode, cadquery-ocp-novtk and downgraded build123d, and import cadquery now fails there. I did not touch it. All builds and tests ran in a
  private venv in the session scratchpad with the same editable framework and molejo checkouts. The repair is a forced reinstall of cadquery-ocp 7.8.1.1.post1, which is your call.
- Framework gap: the faceted test path refuses these OpenSCAD 2021.01 STLs as non-watertight before Manifold ever sees them, though Manifold ingests them without error. The project's contracts therefore call manifold3d directly. That is
  a candidate wart; I have not filed it.


# kossel

- Framework quirks met, not filed: perturbation directions are read in the frame before a node's first translation, so the tests say so; assertClose is unusable for a screw in a hole, so the tests carry gap and hole helpers.
  Out of scope and stated: the retractable Z probe, the FSR glass frame, the spool, wiring, and a length-true Bowden tube.

# fender-bender

- The upstream geometry has no rigid interference-free bracket release, and its guide-wall click bumps overlap the frame at rest. The contracts carry stated, measured allowances for those two things (release path and snap) and say so in
  the specs and README. If you would rather have them red, say so.
- The framework's watertight gate refuses seven upstream STLs that Manifold accepts. That blocked assertNoSolidInterference and the faceted kernel, so the project checks interference pairwise on exact solids, and the
  support-under-gravity contract is unverified. A candidate wart, not filed.

# openvmp

- The blueprint nests each foot 11.5 mm short of the thigh's knee shaft, and the shaft sits inside the foot's hubs at rest. The simulation bends about the shaft and records the offset.
- No pose in this blueprint rolls on level wheels, and the foot fouls the thigh's knee motor past 45° of bend where ROS allows 126°. Duct is therefore a 45° cambered brace. A direct Crouch to Hug ramp swings the hooks through each
  other, so the scenario routes such moves through Rest. Look is limited to the quadrant clear of the hip's vision beams.
- The base's "worm collar" is actually on the gear shaft, two stepper drivers are placed through the battery, and 379 within-link overlaps are the blueprint's own placements. All of it is in the design record.
- Framework gaps, recorded in the design and in memory but not filed: the spatial assertions' watertight gate rejects 21 of 67 vendor pieces, so clearance is measured by a project engine; the exact export keeps degenerate triangles;
  tessellation precision is not declarable per node; a bare file path in solid test builds every node class, so run it with robot.py:Don1.

# Execution plan (2026-09-06)

Triage of the findings above, pilot-ratified. Items 1-4 are framework fixes
run as standalone framework-change cycles; 5 and 6 are deferred until a
second project asks. Once each fix is on solid-node main, the projects that
carried a workaround for it drop the workaround.

## Fix now

1. **The watertight gate.** `_cached_local_bounds` in `solid_node/test.py`
   demands trimesh's `is_volume` before any spatial assertion, even on
   exact-kernel runs and even for the broad phase, and the per-binding check
   below it demands `is_watertight`. Manifold accepts the meshes trimesh
   refuses. Let Manifold build the mesh and judge by its own status, keeping
   trimesh's verdict only as diagnostic text. Evidence: snappy-reprap,
   fender-bender, openvmp.
2. **Exact export keeps degenerate triangles.** The exact-leaf STL export
   calls `exact.write_stl` with degenerate removal off while the fusion path
   turns it on. Turn it on for leaves. Evidence: openvmp (shafts, standoff,
   stepper, servo frame close on this alone). Same cycle as item 1.
3. **Perturbation frame.** The perturbation is inserted before the node's
   first Translation, so a node whose only op is a rotation is displaced
   after it, in the parent frame, while the API skill promises directions
   are local. Insert before every operation so the code matches the skill.
   Evidence: kossel, abacus. Own cycle.
4. **Bare-path `solid test file.py` builds every class.** A sub-assembly
   whose ports are bound by its parent crashes standalone. Default the bare
   path to the manifest's declared models, or the file's main class, instead
   of every class. Evidence: openvmp. Own cycle.

## Deferred

5. **Per-node tessellation precision.** openvmp's stored triangulation in
   render() is a legitimate workaround; one project asks. Propose when a
   second one does.
6. **A clearance contract for a screw in a hole.** kossel's gap and hole
   helpers are the evidence for a new contract, not a fix.

## Not framework fixes

- The venv breakage is repaired; the workspace venv imports cadquery.
- fender-bender's release-path and snap allowances are a pilot decision
  (keep the measured allowances, or make the contracts red).
- The openvmp blueprint findings and kossel's out-of-scope list are design
  record about the upstream machines.

## Project follow-ups after integration

- snappy-reprap: replace the private manifold3d assertions with the
  framework's spatial contracts.
- fender-bender: use assertNoSolidInterference and the faceted kernel;
  verify the support-under-gravity contract.
- openvmp: drop the project clearance engine and the render()-time
  tessellation where degenerate removal now suffices; run `solid test` on
  the bare file.
- kossel, abacus: state perturbation directions in the node's own frame.

## Status (2026-09-06, end of day)

Items 1-4 are on solid-node main, each a two-commit standalone cycle,
nothing pushed:

- 1+2 `trust-manifold-over-trimesh`: 5ed122e + 395769f, ADR-074.
- 3 `perturb-in-the-nodes-own-frame`: b2809b9 + 2fa03ff, ADR-075.
- 4 `test-a-bare-file-by-its-tests`: 811966b + 66f6bee, no ADR.

Shop skills corrected (25e6a93). Projects refactored, each committed in
its own repository: abacus 52e180e and kossel 70e7269 (directions in the
node's frame); snappy-reprap 02561fd (framework pair contracts; the
engine kept only for summed and slab volumes); fender-bender eb672d1
(framework interference and support contracts; the support-under-gravity
requirement is now verified, 18 passed exact); openvmp (bare-path test
run, 30 passed; the engine admits 63 of 67 artifacts, up from 46; the
cross-link clearance engine stays for the four it still refuses and for
the blueprint's within-link overlaps, which are placements, not motion).
Items 5 and 6 remain deferred.

# Expression math and mechanisms (2026-09-06)

Findings from lifting the project `kinematics.py` helpers into the
framework: two standalone cycles, `expression-math` (`solid_node.math`
grows abs, floor, ceil, sign, min, max, clamp, clamp01, ramp, lerp, wrap,
piecewise, bump, polar, turn, rotate_x/y/z) and `mechanisms`
(`solid_node.mechanisms`: gears, screws, cranks, deltas, linkages). Both are on
solid-node main as of 2026-09-06 (main at e28cd3a, nothing pushed):

- `expression-math`: d0688b1 + 2369bd5, ADR-022 revised.
- `mechanisms`: ebe874b + e28cd3a (rebased onto the first; four
  documentation files conflicted additively), ADR-076.

Viewer fixture committed in solid-node-viewer at 616ed9b. Cycle worktrees
torn down; branches kept. Not triaged yet; the items below are candidates.

## Framework

7. **`%` on a symbolic value disagrees across runtimes.** solid2's
   `OpenSCADConstant.__mod__` emits `(a % b)`, which OpenSCAD and the viewer
   evaluate C-style (sign of the dividend), while a numeric render uses
   Python's `%` (sign of the divisor). A project writing `angle % 360` on a
   driver gets two answers for a negative operand, and neither the parity
   corpus nor anything else catches it. Candidate fix: export a remainder
   from `solid_node.math` whose numeric face is `math.fmod` and whose
   symbolic face is the `%` operator, add it to `SYMBOLIC_BUILTINS` and the
   parity corpus, and document that bare `%` is not expression-safe.
   Evidence: found while refusing `mod` in `expression-math` (design D4).
8. **No way to spell a dimensioned literal in the algebra.** `180` and
   `360` are dimensionless, `Angle` is its own axis, so every law carrying a
   degree literal has no declared face: `meshed_angle(theta, ...)`,
   `screw_travel`, `wrap(angle)` with its default period, and the
   trigonometric `bump` all raise at class definition. The escape hatches
   are `.value` (unchecked) and an inline anonymous declaration
   (`wrap(angle, Angle(360.0))`), which works but is a parameter, not a
   constant. Candidate fix: an Angle-typed (and Length-typed) literal in
   `solid_node.parameters`. Evidence: `expression-math` (bump, wrap, turn),
   `mechanisms` (design D3, ADR-076 open question).
9. **`tools/generate_parity_fixture.py` cannot run from a worktree.** Its
   default output path resolves to `ROOT/../solid-node-viewer/...`, which
   from `solid-node/WTs/<name>/` is a directory that does not exist. Resolve
   through the Git common directory, as the shop contract prescribes for
   workspace paths, or require the output argument. Evidence:
   `expression-math` task 5.4.
10. **Non-reproducible flake in `tests/test_exact_geometry.py`.**
    `ExactArtifactTest::test_a_shape_without_file_identity_is_not_cached`
    failed once in a full run and passed alone and in two further full
    runs. It asserts `assertIsNot` on two `placed_shape` results, so an
    object-identity or GC-recycling assumption is the likely cause. Seen
    once during `mechanisms`.

## Deferred

11. **The openflexure four-bar decomposition** (`leg_lean`, `lever_rise`)
    as a mechanism law. One project asks; propose when a second flexure
    stage does (ADR-076 open question).
12. **`piecewise` expression length.** ~~A sum of clamped ramps puts n-1
    `min(max(...))` terms on the wire with the driver repeated in each;
    `bump` repeats its clamp four times. Accepted in `expression-math`
    (no common-subexpression pass); revisit only if a published document
    grows past what the viewer parses comfortably.~~ **Fixed 2026-09-07**,
    after `wall_clock_53_grasshopper` published 31.6 MB of expressions
    (seven million pasted nodes over 263 distinct subexpressions) and
    animated at two frames per second. Three cycles: the viewer's
    `share-expression-subtrees` (ADR-043, a hash-consed DAG evaluated
    once per distinct subexpression per pass: 633 ms to 0.36 ms per
    frame, 569 MB to 69 MB of heap on documents already published), the
    framework's `expression-bindings` (ADR-080, integrated into main at
    0f210ab: the serializer interns expressions structurally and
    publishes each shared subexpression once in an ordered `bindings`
    table, document version 4; the clock's document is now 32 KB), and
    the viewer's `read-expression-bindings` (ADR-044, viewer API 7).
    The `viewer` extra's version floor is still unpinned, because the
    viewer is unreleased.

## Not framework fixes

- Viewer: `npx vitest` at the `solid-node-viewer` root runs a stale copy
  under `build/lib/` that fails on a missing `jokenizer`; the widget's own
  runner is the entry point. Clean or ignore `build/`.
- Viewer: the regenerated `parity-fixture.json` (266 to 421 cases) sits
  uncommitted in `solid-node-viewer` and needs its own commit there.
- Shop: the dev-env manifest carries an `exact-geometry` row pointing at an
  old workspace path and a `release-0-5` row with no directory;
  `solid-node/WTs/exact-geometry/` is an unregistered leftover checkout.
- Shop: `shop-skills/solid-node` and `solid-node-api` still let the false
  belief stand that the viewer's expression language has no `min`, `max`,
  `abs` or `floor`; four projects copied a `sqrt` clamp kit on that basis.
  Correct once the cycles are on main.
- Workspace: `cq_gears` is absent from the venv, so `sandbox/gearbox`'s
  own tests cannot run; Sphinx is absent, so the documentation cannot be
  built to check new `.rst`.

## Project follow-ups after integration

Run every project suite with `solid test --faceted`.

- abacus, fender-bender: commit the uncommitted migrations to the new
  `solid_node.math` names (both ran green; abacus's four failures are the
  pilot's own `count` edit).
- pascaline, snappy-reprap (`cable_chain.py`): drop the `sqrt` clamp kit and
  `smooth_min`/`smooth_max` for `clamp01`, `min`, `max`, `wrap`.
- 3DPrintedClocks (four designs): drop the private `OpenSCADConstant`
  `floor`/`min`/`max` wrappers for `solid_node.math`; replace the depthing
  functions with `meshed_angle`/`driving_angle` over MrBunsy's references;
  the grasshopper's `nib_position` with `circle_intersection`.
- gearbox: `conjugate_angle` becomes `meshed_angle(theta, z1, z2, alpha,
  180 / z1, 0)`; retire `KinematicAssembly`, which `simulate()` made
  obsolete.
- v8-engine: the three `_at` functions become the crank family.
- kossel: the delta functions become `delta_carriage`/`delta_rod`.
- openflexure, Inmoov: `column_travel`/`elbow_reach` over `screw_travel`,
  `stage_drop`/flexed reach over `link_rise`; `polar` and `rotate_x` from
  `solid_node.math`.
- Delete the uncommitted `probe_mechanisms.py` left in gearbox, v8-engine,
  kossel, 3DPrintedClocks, openflexure-microscope and Inmoov-sim.

# Internal-Cycloidal-Actuator (2026-09-06, STEP import cycles)

- Item 5 (per-node tessellation) is fixed and on main (ADR-077, integrated
  with StepNode ADR-078 and import-step ADR-079), with a finding on the way: a stored triangulation only
  partly survives the framework export (Output_Shaft 3.35 MB, not 1.8 MB),
  so the workaround openvmp relies on is weaker than recorded; and the
  BREP had to be written before the STL or the mesher's triangulation
  leaked into it.
- `StepNode` (ADR-078) is on main too. Finding, not filed as
  a cycle: a `StepNode` whose `step_source` is absent constructs fine and
  fails later inside `mtime_ns` with a bare `FileNotFoundError` naming
  only the path. The actuator project calls its own `source.require()`
  at import to keep the extract command in the failure. A leaf that
  validated its declared file at construction, naming the class and the
  path, would be the better failure; `StlNode` has the same gap.

## Status (2026-09-06, project refactor pass)

All thirteen designs migrated, each committed in its own repository,
nothing pushed: abacus 98dc357, fender-bender 2a6ac61, pascaline 87b1242,
snappy-reprap 18fd943, kossel b7f4317, v8-engine 3740f6a, openflexure
c077810, Inmoov-sim 20ad316, 3DPrintedClocks 6ec0ff2 (four designs, one
depthing mapping: wheel = driver described by its gap centre, pinion =
driven described by its tooth tip), sandbox/gearbox 4e4efb2 (mesh wrapper
and `KinematicAssembly` retired for `simulate()`). Every snapshot compared
byte- or pixel-identical except fender-bender's intended pulse change.
Probe files deleted. pascaline's `wrap` had a latent edge bug at
-period/2 that the framework's ceil-based `wrap` fixes.

New framework candidates from the pass:

13. **The faceted kernel fails on noise at its default epsilon.** With
    `solid test --faceted` and no `--volume-epsilon`, interference
    assertions fail on volumes of -2e-14, -4.7e-17, 1e-7 and similar in
    abacus (3 tests), openflexure (4 of 6), fender-bender (4 of 18),
    pascaline (3) and every 3DPrintedClocks design (2-3 each), all
    identical before and after the migration and all green on the exact
    kernel or at the clocks' documented epsilon of 1e-3 mm³. A negative
    volume is not an interference. Candidate fix: treat |volume| below a
    tessellation-scaled floor as zero by default, or make the default
    epsilon nonzero and say so in the summary line.
14. **`solid snapshot --preview` passes a bare `--preview` to OpenSCAD
    2021.01**, which rejects it with a usage dump
    (`OpenScadRenderer.build_command` emits it unconditionally). Seen in
    3DPrintedClocks.

Project follow-ups still open: gearbox's four test files need a
`node = <Class>` declaration the framework now requires (its two
migration-covering suites ran only under a temporary edit); `cq_gears`
is still absent from the workspace venv; pascaline's package files are
mostly untracked in its repository; Inmoov's `elbow_angle` stays local
(an arcsine over squared reaches, not the law of cosines). Shop
follow-ups: the two shop skills still claim the viewer lacks min/max/
floor; the session scratchpad is shared across parallel agents, and
four of ten clobbered each other's `before.png` (each caught it and
redid the comparison under a distinctive name).
- Phase 4 of the actuator (make-the-actuator-turn) found two more, not
  filed as cycles: (a) an exact Boolean between Output_Shaft and the
  50x65x7 bearing fails in a ~0.18 deg window at exactly 270 deg of input
  (RuntimeError, or a wrong or zero volume) while every other sampled
  angle answers the same constant press-fit volume — a kernel-robustness
  gap at a coincident configuration, recorded in the project as an
  expected failure; (b) no exact minimum-distance assertion exists, so a
  0.05 mm roller clearance had to be measured on a fine private
  tessellation (0.01 mm / 0.1 rad) rather than through the framework's
  spatial contracts, and there is no way to measure an overlap volume
  without asserting on it.
- (c) `solid test`'s runner has no skip and no expected-failure concept:
  it calls each method in a loop under a bare `except Exception`, so
  `self.skipTest()` and `@unittest.expectedFailure` both count as plain
  failures. The actuator guards exact-only volume bands with an early
  `return` and records the kernel gap as a canary asserting the wrong
  value, which is the honest equivalent it has; a runner that honoured
  `SkipTest` and expected failures would let a project say these things
  plainly.

# AlbertPro (2026-09-07, simulate the Albert quadruped)

Found while building `projects/Robots/AlbertPro/simulation/` directly
from this conversation: an eighteen-body print plate assembled into the
quadruped `RL/dog.xml` describes, driven by the five trained
trajectories the ESP32 replays.

## Framework

- **`self.children` is empty during `simulate()`, and iterating it fails
  silently.** `LowerLeg.simulate()` was written as `for piece in
  self.children: piece.rotate(self.knee.value, AXIS)`. The port was
  bound and correct, the list was empty, the loop applied nothing, and
  nothing raised — the shin simply never turned about its knee, and the
  published model was a robot whose knees did not bend. Every contract
  passed, because a test calls `set_state` before measuring and by then
  the children are linked; only a snapshot showed it. The workaround is
  to address the declared attributes (`self.near`, `self.far`), which
  works in both phases, and that is what
  `projects/Robots/AlbertPro/simulation/leg.py` does. A documented
  empty-during-simulate contract, or a `.children` that raises there
  rather than reading as empty, would turn a silent wrong model into an
  error. This is the one worth filing.

- **A driver's `range` is presentation metadata and nothing enforces
  it.** `height` has a hard geometric range — outside it the machine has
  no pose — and there is no per-driver validator or clamp hook. The
  project guards inside its own `stance_angles()`, which can only act
  when handed a plain number, so the guard fires in tests, snapshots and
  exports but not in the viewer, where a driver is symbolic. Workaround
  in `simulation/layout.py`.

- **No absolute value, min or max in `solid_node.math`.** This project
  needs all three symbolically: to clamp a commanded joint angle into
  its declared range (which the MJCF's own `ctrllimited` actuators do,
  and 30% of the published commands need), and to split a two-sided
  slider into its positive and negative halves without a conditional.
  All three are reachable as `|x| = sqrt(x*x)`, `max(a,b) =
  (a+b+|a-b|)/2`, `min(a,b) = (a+b-|a-b|)/2`, so nothing is blocked —
  but every project that needs a clamp will re-derive this. Workaround
  in `simulation/layout.py:clamp`.

- **A deep expression silently loses subexpression sharing.** Summing
  3659 terms left to right built an expression the bindings pass refused
  ("too deeply nested ... published verbatim and unshared"), giving a
  333 KB `viewer.json` with 27 KB unshared expressions. Summing the same
  terms as a balanced tree fixed it completely: no warning, 167 KB, 1656
  shared bindings. The warning is good and said exactly what happened;
  what is missing is that association order is load-bearing for
  published size and viewer cost, which nothing tells you until you hit
  it. Workaround in `simulation/gaits.py:balanced_sum`.

- **There is no `solid import-stl`.** `solid import-step` scaffolds a
  whole document into declarative source; the equivalent for a
  multi-body mesh pack does not exist, and a pack's inventory is
  reachable only by provoking a build failure. For an eighteen-body
  plate that is enough friction to be worth a committed probe
  (`simulation/tools/probe.py`). Not a blocker — `StlNode`'s `body`
  index and its per-body inventory did the actual job cleanly, and this
  is the smallest of the five.

## Not framework fixes

- `solid test` needs a node class, so a module that defines only
  constants (`layout.py`, `gaits.py`) cannot carry a companion test
  file. Its contracts live in the root's companion instead. Reasonable
  as it stands; noted because it shapes where a project puts its drift
  tests.
- `sim.every(period, ...)` requires the period to be a whole number of
  `dt` ticks and says so clearly. Correct behaviour, easy to trip over.
- `set_state` refuses a `numpy.float64`, naming the driver and the
  value. Correct and clearly reported.

## Project follow-ups

None open. The change is archived in the project's own
`openspec/changes/archive/`; nothing about AlbertPro is staged here.


# YouCanBuildDog

Simulating James Bruton's `dog02_9g` (51 solids, Fusion/AP214 export)
and then fitting the M3 hardware its bores ask for hit three framework
things worth fixing. None is filed.

- **`StepNode` cannot select between products that share a name.**
  `part` is a name, and this export carries **three** products called
  `COMPOUND` — the two chassis halves and the electronics tower, 150 003
  of the machine's 359 786 mm³. The framework refuses correctly and its
  error is excellent, listing all three with distinct bounds, solid
  counts and volumes:

      dog02_9g.stp has 3 products named 'COMPOUND'; the name is
      ambiguous between: ... 7 solids, volume 46025.752 / 4 solids,
      39867.637 / 6 solids, 64813.221

  So they *are* distinguishable — there is simply no way to say which
  one is wanted. A one-based occurrence index alongside `part`, or
  selection by the document entry `StepAssembly` already exposes, would
  close it. Workaround:
  `projects/Robots/YouCanBuildDog/simulation/tools/split_step.py` writes
  one single-product STEP per solid into an ignored directory, which the
  project wanted anyway (see the next paragraph), so the gap cost
  nothing extra here — but a project that only wanted the three
  compounds would have to build the same machinery.

  Worth noting the related shape: an upstream *product* is routinely not
  a printed piece. In this export 20 products hold 51 solids, and two
  toe blocks are filed under a *chassis* product rather than the leg
  they sit on. Per-solid selection — a `solid` index beside `part`, or a
  `solid import-step --per-solid` — would be the general answer, and
  would make the framework's own printed-solid unit reachable from a
  STEP document without a project-local splitter.

- **`assertNoDisconnectedSolids` splits each solid's STL rather than
  reading an exact node's solid count.** The API skill says the verdict
  is "the exact geometry's solid count for an exact solid, a split of
  the node's own STL otherwise", but on a tree of 51 exact `StepNode`s
  it went to `cached_base_mesh(solid.stl_file).split(...)`, which
  reaches trimesh's `fill_holes` on a mesh that is not closed, which
  imports `networkx` — absent from the workspace venv:

      ModuleNotFoundError: No module named 'networkx'
      ... trimesh/repair.py:261 in fill_holes
      ... solid_node/test.py:1505 in assertNoDisconnectedSolids

  Two things: the exact path looks not to be taken for exact nodes, and
  `networkx` is an undeclared transitive need of the mesh path. The
  project counts face-connected components itself instead
  (`simulation/test_dog.py:test_solid_integrity`), which needs no closed
  mesh and covers all 51 solids including the two the helper cannot
  read. Connectivity does not require watertightness, so the mesh path
  need not go near `fill_holes` at all.

- **An exact intersection returns empty for two solids that plainly
  overlap, and `assertAssemblySupported` silently loses a support edge
  for it.** Fitting the fasteners, the battery holder hangs under the
  lower plate on two countersunk screws driven up into it. Dropped one
  millimetre along gravity the holder demonstrably encloses the screw's
  head, and the framework's support graph should therefore hold the
  holder up. It does not, because `_placed_intersection` takes the exact
  branch for the pair and `intersect_shapes` comes back with zero
  solids. On the same two placed shapes, at the same drop:

      BRepCheck_Analyzer(holder).IsValid()          True
      BRepCheck_Analyzer(screw).IsValid()           True
      BRepExtrema_DistShapeShape(holder, screw)     0.00000
      BRepClass3d_SolidClassifier(holder), a point
        inside the screw head                       TopAbs_IN
      BRepAlgoAPI_Common(holder, screw)             0.00000 mm3
      BRepAlgoAPI_Common(holder, primitive cone
        in the screw's place)                       4.65116 mm3
      BRepAlgoAPI_Common(holder, box there)        16.01830 mm3
      trimesh.boolean.intersection of the two
        placed meshes                               7.41455 mm3

  Every other reading says they overlap; only the boolean of those two
  particular solids says otherwise, and it says so at drops of 0.5, 1,
  1.5, 2 and 3 mm alike. The screw is a `CadQueryNode` built by a loft
  and two unions, the holder a `StepNode` from the export; the same
  screw class intersects three other STEP solids in this machine
  correctly, so it is the pair rather than either shape.

  It matters because the exact branch is *chosen* for exact/exact pairs
  and a missing verdict there is indistinguishable from "no contact":
  the assertion reports a solid unsupported and gives no hint that a
  boolean failed. A cross-check against the mesh branch when the exact
  one reports empty but the two placed bounds overlap would have caught
  it. The project works around it by declaring the battery's hold
  through `supports=`, which is honest but hides a kernel failure behind
  a modelling exemption.

  Reproduction is in
  `projects/Robots/YouCanBuildDog`; the scripts that produced the table
  above are throwaway, but the pair is
  `moving.battery.holder` and `moving.battery_fore` at rest with the
  drivers zeroed.

## Environment

- `networkx` is missing from the workspace `.venv`, and trimesh needs it
  for `fill_holes`. Anything that reaches trimesh's repair path — the
  connectivity assertion above, `mesh.is_volume`, `mesh.split` on an
  open mesh — raises `ModuleNotFoundError` rather than a mesh verdict.
  Your call whether to add it; I did not touch the shared venv.

## Not framework fixes

- `assertAssemblySupported` on the exact kernel gave exactly the right
  answer for this machine — nothing above the feet is supported —
  because the export draws no fasteners at all. The framework is not at
  fault; the CAD is. On the faceted kernel it refuses first, on the
  export's two non-manifold tower panels, which is also correct.
- Six pairs in this export are drawn in exact face contact, so their
  exact booleans return 0 at some states and slivers of 1e-16 to 1e-13
  mm³ at others, flipping with nothing but transform composition order.
  That is coincident-face geometry behaving as coincident-face geometry
  does; the project holds those pairs below a stated floating-point
  floor and records the missing clearance as a design finding.
- The test runner aliases the node under test onto the snake-case of the
  test class name, so a class called `LegTest` silently shadows a
  `leg()` helper on the same class with the node itself
  (`TypeError: 'Dog' object is not callable`). Documented behaviour,
  easy to trip over; renaming the class fixed it.
- The runner collects the `TestCase` classes a companion module
  *defines*, not the ones it imports. A suite split across files has to
  mix contracts in rather than import assembled test classes, or they
  run silently as zero tests — which is how nine leg contracts sat
  unexecuted here until the count looked wrong.

## Project follow-ups

- The `standing-stance` support requirement was met on 2026-09-07 by the
  `fasten-the-dog` change: thirty M3 screws read off the export's own
  bores, and `assertAssemblySupported` now proves the moving half —
  plate, brackets, both legs, battery and its own six fasteners — both
  reachable and in frictionless static equilibrium. Over the whole
  machine it reaches 99 of 101 solids; the two it does not are the
  tower's shelves, which the export draws attached to nothing. That
  residue is the design's, not the model's, and is recorded as its own
  contract rather than papered over.
- `dog02_large` is unmodelled: its export fuses each whole leg into one
  product of eight solids, so the hip cannot be articulated without
  cutting upstream geometry.
- The design findings (a stale back-left leg, no fasteners, no running
  clearance, two non-manifold panels) are in the project's README and
  its archived change. Telling James Bruton is your call; I have not
  contacted anyone.

# 3DPrintedClocks (2026-09-07, shared simulation package)

- No public way to give a declared child an instance-specific tree name.
  Mantel clock 34's `TrainArbor` (one class, six instances) set
  `part.name` and the private `_explicit_name` on its `wheel` and `rod`
  children so the viewer tree and interference failures said which wheel
  was which. The refactor dropped the private and relies on the hierarchy
  (`train.centre.wheel`); an interference failure still names the leaf
  only (`wheel should not interfere with wheel`). A public per-instance
  name, or failure messages that print the qualified path, would close
  it.

# Robots/Thor (2026-09-07, full simulation with fasteners)

507 printed and bought solids, six joints and a gripper, every part exact.
Four framework findings, each met while building it and worked around in
the project rather than fixed there.

- **`assertNoDisconnectedSolids` answers on the STL even when the node is
  exact.** `Art1Top` is a single solid of 530398.4 mm³ — `len(shape.Solids())
  == 1` — and its 0.1 mm tessellation splits into five bodies: the part,
  three two-triangle patches of zero volume and 5.0 × 23.4 in extent, and a
  detached lug of 3220.9 mm³. The assertion reports "5 connected bodies"
  for a part whose B-rep is one, and there is no way to ask it for the
  exact answer. The exact answer is the cheaper one, too: no tessellation,
  no mesh engine.

  The project's `test_solid_integrity` walks the tree itself and counts
  `Solids()` per exact leaf (`simulation/test_thor.py`), which is the
  question the assertion is named for. Reproduction: `Art1Top` in
  `projects/Robots/Thor/step/`.

- **The faceted kernel raises instead of answering, and one bad mesh takes
  the whole run with it.** Seven of Thor's parts tessellate non-manifold
  (`Art1Body`, `Art1Top`, `Art1GearMotor`, `Art2BodyB`, `Art2MotorGear`,
  `Art3Body`, `Art4BodyBot`); their exact geometry is sound. Every faceted
  comparison touching one of them raises

      ValueError: ... the mesh engine refuses this mesh (NotManifold)

  so `solid test --faceted` cannot run this machine at all — not "reports
  a worse verdict", cannot run. Six of twenty-eight contracts died on it,
  including both integrity contracts, before any of them compared
  anything. The faceted kernel is the loop kernel the craft skill asks for,
  and a machine assembled from vendor STEP is exactly where it is most
  wanted.

  A verdict of "cannot decide this pair" that the assertion could report
  and skip, or a per-pair fallback to the exact branch, would leave the
  other 493 solids testable. The project runs exact for both the loop and
  the certification, which is affordable here (194 s) only because of the
  next item.

- **There is no public way to ask which pairs of an assembly interfere,
  and by how much.** `assertNoSolidInterference` raises on the first pair
  it finds. A machine whose own design overlaps — this one, and every
  simulated upstream so far — needs the whole set, because the honest
  contract is an inventory of the overlaps the design has, not "none".

  Writing that walk by hand is a trap: `projects/Robots/Thor`'s first
  version composed placements and culled bounds itself and took **over an
  hour** for one pose, where the framework's own path takes **116 seconds**
  for the same 507 solids. `simulation/seats.py` therefore imports
  `_placed_assembly_solids`, `_bounds_candidates` and
  `_candidate_intersection` — three private names — and says so in its
  docstring. A public `solid_interference(node)` returning the pairs and
  volumes, with `assertNoSolidInterference` built on it, would make the
  inventory pattern first-class instead of a raid on the internals. It
  would also let it follow the run's kernel, which the hand-rolled version
  could not.

  Related: neither the assertion nor the pair helpers can name a solid by
  its path. `seats.qualified_names()` walks the tree to build
  `{id(node): 'shoulder.art2.art3.art4.art56.gt2x40_pulley_1'}`, because
  `solid.name` is `gt2x40_pulley_1` and this machine has two. Same gap as
  the 3DPrintedClocks entry above, from the other side.

- **A leaf's artifact is imported into its parent's `.scad` by bare
  filename, so an assembly in a different Python package renders it as
  nothing — silently.** Artifacts live under `_build/<package path>/`. An
  assembly in `simulation/tools/` holding a `MolejoNode` declared in
  `simulation/` emitted

      union() {
        color(...) { import(file = "flexibles-ElbowBelt-...stl", ...); }
        import(file = "beltview-Disc,...stl", ...);
      }

  from `_build/simulation/tools/`, where the belt's STL does not exist —
  it is in `_build/simulation/`. OpenSCAD renders the discs and no belt,
  with no error, and `solid snapshot` reports success. I lost a snapshot
  cycle to a belt I thought was broken.

  Observed with a molejo leaf; nothing about it looks specific to
  flexibles, since the import is written the same way for every leaf.
  Reproduction: put an `AssemblyNode` under `simulation/tools/` whose
  children include a node class defined in `simulation/`, and snapshot it.
  Moving the assembly beside the leaf fixes it, which is why
  `projects/Robots/Thor` has no belt-viewing helper under `tools/`.

## Environment

- `networkx` — the missing package recorded under YouCanBuildDog above —
  is now installed in the workspace `.venv` (3.6.1, `pip install --no-deps`
  so nothing else moved). `assertNoDisconnectedSolids` reaches a verdict
  again rather than raising `ModuleNotFoundError`. I installed it; say if
  you would rather it came out.

## Not framework fixes

- A `clear_state()` inside a test helper un-binds the declared driver
  defaults for the rest of the run: the runner binds them once before the
  first render, and the next test's `set_keyframe(0)` then renders with no
  drivers bound and raises `driver 'art1' ... is not bound`. Documented
  behaviour — state merges, and clearing clears — but the failure surfaces
  in a later test, in framework code, naming a driver the later test never
  touched. Every contract here names every driver instead.
- `solid test <file.py>` on a companion test module maps to the node file
  of the same name, so a pure measurement suite with no node class
  (`test_layout.py` → `layout.py`) fails with `No node class found`. Those
  two suites run under pytest. This is the bare-path item already fixed for
  `openvmp` seen from the other end: the mapping is right, there is just no
  way to say "this test file has no node".

# science-jubilee (2026-09-08)

- Exact OCCT intersection reports a `BRepAlgoAPI` not-done operation for at
  least one valid threaded-ball/fastener pair imported from
  `sonicator_tool_assembly.STEP`. Both leaves are valid exact shapes and
  publish as single watertight bodies, but the exact operation cannot produce
  the source assembly's required seat inventory. The project therefore
  measures the exact pair set on solid-node's published meshes with the
  manifold boolean engine in `simulation/seats.py`; `solid test --exact`
  still covers exact source evaluation and placement. Candidate wart, not
  filed: expose an explicit indeterminate pair verdict or a supported
  exact-to-faceted fallback for interference inventory contracts.

# 3DPrintedClocks wall clock 01 and Thor (2026-09-09, motion layer refactors)

Found while moving the two originating projects onto `solid_node.motion`
(cycles `motion-package`, `joints`, `couplings`, branch `motion`). Poses
were bit-identical before and after in both projects.

- **A joint cannot be anchored at a design-placed part's own origin.**
  `resolve_declared_joints()` runs in `AbstractBaseNode.__init__`, before
  the parent's `render()` has placed the node, so a joint's `at` has no
  way to say "the line through this part's own placed origin". Thor's
  thirteen catalogue parts that spin on their own bearings (pinions,
  pulleys, optodisk, ball cage, bevels) therefore keep one hand-written
  `rotate` each with the sign from `placing.axis_sign`; every sub-assembly
  freedom became a joint. Candidate fix: an anchor mode meaning the node's
  own placed origin (resolved at first bind from the rest placement), or
  lazy resolution of joint arguments at first bind with the eager pass
  kept for tokens and callables that do not touch the placement.

  **Still OPEN after `orbit-joint` (ADR-094).** That cycle gave the
  own-placed-origin mode to ONE argument of ONE joint — an `Orbit`'s
  `carries`, whose default is the body's own placed origin, settled at
  the first binding and costing nothing because in the body's own frame
  that point is exactly the origin. It does NOT give `Revolute`'s `at`
  the same mode: an anchor has to be carried through the inverse of the
  rest placement, which is a different answer, and Thor's thirteen parts
  need it at realization time. This finding is unchanged.
- **FIXED (cycle `whole-tree-fixpoint`, ADR-099). A relation chain must
  be stated in one class body.** Relations are
  solved per instance at the end of its own simulate phase, and a child's
  relations solve after its parent's. Clock 01 binds `escape.turn` in
  `Movement.simulate()`; stating `centre.drives(third)` inside `Train`
  while `power.drives(train.centre)` stays in `Movement` is refused with
  `UnreachedCoordinate` at `Movement`'s end, because `Train`'s relations
  have not run yet. The message names both ends, so the constraint is
  visible, but it forces every chain into the class that binds its known
  end. Candidate fix: let a parent's fixpoint defer an unreached relation
  until its descendants have solved, then re-run once.
  **What shipped:** exactly the candidate fix — an unresolved relation
  defers to the enumeration's own whole-tree fixpoint, resolved once
  every assembly's phase has run, and refused only then. Proven on this
  exact shape
  (`tests/test_couplings.py::TreeFixpointTest::test_a_chain_stated_one_level_down_solves`).
  Wall clock 01's own two-arbor chain (task 9.4 of the change) is NOT
  proven here: 3DPrintedClocks' working tree was under the pilot's own
  session throughout this implementation, and the overlay is left for a
  follow-up that can read it.
- **FIXED (cycle `whole-tree-fixpoint`, ADR-099). A node's own derived
  coordinate is unbound inside its own `simulate()`.** `clear_solved()`
  runs before the author's `simulate()`
  and the fixpoint after it, so `Art4.left = art56.wrist + 2 * tool` reads
  as an unbound slot in `Art4.simulate()` and a hand-written rotate from it
  silently turns nothing (Thor's two motor pulleys, caught by the pose
  comparison). Coordinates bound by an ancestor's relation are fine.
  Candidate fix: refuse the read by name rather than yield an empty slot,
  or state the two-phase order in the read's error.
  **What shipped:** the read is recorded while it is unbound and judged
  at the end of the enumeration by what actually bound the coordinate
  afterward — a relation, a derived formula or a wiring: refused, naming
  both classes and the two-phase order. Bound afterward by the reading
  class's OWN `simulate()` instead: not refused, which is the ordinary
  rest-default guard and stays exactly as unremarkable as it was.
  Proven on Thor's own shape
  (`tests/test_couplings.py::ReadRefusalTest::test_a_class_reading_its_own_derived_coordinate_is_refused`).
- Thor's exact suite has two failures that pre-exist this work on this
  framework tree (`seats.assert_inventory`: 260 of 272 overlapping pairs
  not in the seats inventory, in `test_assembly_integrity` and the
  scenario test); byte-identical with the unrefactored model, and the
  same 29/2 on the primary checkout at main cb474e3 with Thor's committed
  code, so it predates the motion branch (an exact-boolean or seats change
  since Thor's last green run, not investigated here).

# Motion catalogue refactor (2026-09-09, every project onto `solid_node.motion`)

Found while moving the rest of the project catalogue onto joints and
couplings after the ports move broke every unmigrated import. Tracker:
`libresolid-studio/docs/motion-general-refactor.md`. Pilot's rule for this
campaign: a missing primitive defers the project and is recorded here first,
with the sentence the project wants to write, so the primitive is built
before the project is refactored around its absence.

- **A joint's axis and anchor belong to the declaration site as often as
  to the class.** Two more sightings of the first 2026-09-09 finding, from
  the opposite side: not a design-placed part whose origin is unknown, but
  a shared or catalogue class whose placement is the PARENT's knowledge.
  Poseidon's `ThreadedRod` and `ShaftCoupling` are bought-hardware
  envelopes; to turn on the drive axis each must now carry
  `turn = Revolute(axis=(1, 0, 0), at=(LEADSCREW_START_X, *DRIVE_AXIS_YZ))`
  with the pump's layout constants inside the hardware module, even though
  both anchors are exactly the rods' own placed origins.
  OpenMANIPULATOR-X's seven mesh packs share one `VisualPack` class; the two
  gripper fingers slide on mirrored axes, so the project needs two
  three-line subclasses whose only content is one `Prismatic` each, and
  every arm link writes its URDF origin twice — in the parent's
  `render().translate()` and again as the joint's `at`. The sentences the
  projects want:

      leadscrew = ThreadedRod(turn=Revolute(axis=(1, 0, 0), at=(LEADSCREW_START_X, *DRIVE_AXIS_YZ)))
      left_finger = VisualPack('gripper_left_palm.stl', travel=Prismatic(axis=(0, 1, 0), range=(-11, 20), unit='mm'))
      base_yaw = Revolute(axis=(0, 0, 1), unit='deg')      # anchored at my own placed origin, no `at`

  Neither project is deferred: the motion is fully stated either way, and
  the cost is duplication and ceremony, not hand-written motion. Candidate
  fixes, complementary: (a) the own-placed-origin anchor mode already
  proposed above, which removes every `at` that repeats the parent's
  translate; (b) a joint passed as a declaration keyword, resolved on the
  child like a wiring is today but declaring a freedom rather than binding
  one, so a shared class can be given a joint where it is placed.

- **FIXED (cycle `joint-composition-order`, ADR-093). Two joints on one
  body compose in binding order, which a relation cannot see.** OpenCycloid's cycloidal disks orbit the main axis at the
  eccentric radius while spinning at the reduced rate about their own
  centre: `R(in)·T(d)·R(out−in)`. Two `Revolute` joints on the disk state
  it — `orbit` about the parent's axis and `spin` about the disk's own
  placed origin — but the pose is right only when `spin` is applied inside
  `orbit`, and the joints spec composes joint motion in the order the
  coordinates were BOUND. Bound by relations, that is the solver's pass
  order, which the couplings spec fixes as declaration order within a pass
  but which a reader of the class cannot see and a derived coordinate
  would silently change. The sentences the project wants, either:

      orbit = Orbit(axis=(0, 0, 1), radius=ECCENTRIC_RADIUS, phase=-90.0, unit='deg')
      eccentric_shaft.spin.drives(stage_one.orbit)
      eccentric_shaft.spin.drives(stage_one.spin, ratio=-1.0 / REDUCTION)

  (a carried body whose attitude the orbit leaves alone, so the spin is
  absolute and the `-1` term vanishes), or a stated contract that the
  joints of one class compose in their DECLARATION order, innermost first,
  whatever order they are bound in. OpenCycloid is deferred at stage A
  until one exists.

  The second form is now the contract: the joints declared on one class
  compose in declaration order, innermost first, whatever order they are
  bound in (ADR-093, cycle `joint-composition-order`). **The first form
  is now the contract too** (ADR-094, cycle `orbit-joint`): `Orbit` is
  built, and OpenCycloid writes `spin` first and then
  `orbit = Orbit(axis=(0, 0, 1), unit='deg')` with no `carries` at all —
  its plan moves the eccentricity into the rest placement, so the disk's
  own placed origin IS the eccentric centre and the DEFAULT carried point
  derives both the `ECCENTRIC_RADIUS = 2.5` and the `-90.0` phase the
  sentence above typed. The `- 1.0` in `ratio=-1.0 / REDUCTION - 1.0`
  goes with them. OpenCycloid still waits on ONE finding: the fan-out
  over a repeated child below. Its deferral stands on that alone.
- **A relation cannot fan out over a repeated child.** The same actuator's
  four eccentric bearings and six output pins are `.repeat()` children with
  a per-copy sign or phase; the couplings spec refuses a path through a
  repeated declaration and advises stating the relation inside the repeated
  class, which cannot read the parent's coordinate. They stay bound in a
  `for` loop in `simulate()`. Wanted:

      eccentric_bearings = RadialBearing(...).repeat(4, orbit=eccentric_shaft.spin)
      eccentric_shaft.spin.drives(eccentric_bearings.orbit, law=per_copy_sign)

  where the law is handed the copy (its index) as the driven node. Second
  reason OpenCycloid is deferred.

  **FIXED (cycle `repeat-fan-out`, ADR-096).** A relation whose DRIVEN end
  passes through a repeated child now resolves to one relation per
  realized copy, `law=` called once per copy with the copy as its second
  argument, so `eccentric_shaft.spin.drives(eccentric_bearings.orbit,
  law=per_copy_sign)` states it in one line and `per_copy_sign` reads the
  copy's own `index` with no new argument. No `.repeat(n, orbit=...)`
  keyword was built: an identity wiring over a repeat already worked
  (measured, `evidence/probe_wiring_repeat.py`), and what it could not do
  — take its source from a path — is exactly what a broadcast relation
  states. OpenCycloid becomes refactorable at stage B in its own
  repository's own cycle; nothing in the framework waits on it.
- **FIXED (cycle `whole-tree-fixpoint`, ADR-099). Two smaller sightings
  from OpenTorque (planetary reducer, not
  deferred).** (a) The one-class-body rule again: the root cannot say
  `reducer.planet_1.orbit.drives(output_stack.planet_carrier_b.turn)`
  because the reducer's own relations have not run when the root solves,
  so the 1:8 carrier ratio is stated twice from one constant, once in the
  reducer and once at the root. (b) Relations are additive through
  inheritance, so a preview subclass that wants the same coordinate driven
  from a different source (`motor_rotor.spin = input_angle + 360 * time`)
  cannot restate the base's relation; the base binds the rotor in one
  `simulate()` line instead of stating `input_angle.drives(motor_rotor.spin)`.
  Wanted: a subclass may replace a NAMED relation of its base, the way a
  redeclared port wins.
  **What shipped:** (a) is the same whole-tree fixpoint as the two
  entries above. (b) is exactly
  the wanted mechanism: a subclass assigning a relation to a name a base
  already used REPLACES it, at the base's position in the enumeration
  (the rule a redeclared joint already obeys, ADR-093); a bare statement,
  or a name no base used, stays additive. Proven directly, on OpenTorque's
  own two-relation shape, as a unit test
  (`tests/test_couplings.py::SubclassReplacesRelationTest`). An overlay
  proving BOTH (a) and (b) on OpenTorque's own project code (task 9.6 of
  the change) is NOT proven here, deferred for time; the project's own
  base-against-head pose comparison, unmodified, is 0.000e+00
  (`evidence.md` §9).
- **FIXED for the composition half (cycle `joint-composition-order`,
  ADR-093). A floating body's attitude is the same composition gap, from
  the other side.** The hexapod's chassis has four freedoms against the
  ground — roll, pitch, yaw, lift — and its inverse kinematics hand-invert
  exactly `R_roll · R_pitch · R_yaw · T_height`. Four joints on the chassis
  would put that composition at the mercy of binding order. Wanted:

      class Chassis(AssemblyNode):
          roll  = Revolute(axis=(1, 0, 0), unit='deg')
          pitch = Revolute(axis=(0, 1, 0), unit='deg')
          yaw   = Revolute(axis=(0, 0, 1), unit='deg')
          lift  = Prismatic(axis=(0, 0, 1), unit='mm')

  composed innermost-first in DECLARATION order whatever order the
  coordinates are bound in — or the `Free` joint the design note listed
  for later. Second sighting of the OpenCycloid finding; the hexapod is
  deferred at stage A on it, so one primitive unblocks both. Its eighteen
  leg joints are statable today and wait with it.

  The four-declaration form above is exactly what the contract now
  guarantees, so the hexapod is unblocked by ADR-093.

  **FIXED, the other half too (cycle `free-joint`, ADR-095).** `Free` is
  now a declaration: `pose = Free(angle_unit='deg', length_unit='mm')`,
  one joint owning six coordinates reached as `chassis.pose.roll` …
  `chassis.pose.z` and reported by the port enumerator under those dotted
  names, composing `R(roll) · R(pitch) · R(yaw) · T(x, y, z)` innermost
  first — the product `Chassis._to_chassis` hand-inverts, measured
  against the hexapod's own four calls at seven poses before the cycle
  was written. The chassis binds four of the six and the other two place
  nothing. The refactor itself is the project's own stage B, in its own
  repository; nothing in the framework waits on it.
- **Fan-out over a repeated child, second sighting: the abacus.** Each
  column's five beads are one `Bead` class repeated; the heaven bead is
  one relation with a clamp law, but the four earth beads each need the
  column's `earth` value clamped against their own rank in the stack, so
  the law must read the copy's index. Wanted:

      earth.drives(earth_beads.travel, law=earth_lift)   # law(column, bead) reads bead.index

  With the relation refused through `.repeat()`, all four stay bound in
  a loop in `Column.simulate()` and a joints-only refactor would be
  cosmetic; the abacus is deferred at stage A on the same primitive as
  OpenCycloid's bearings and pins.

  **FIXED (cycle `repeat-fan-out`, ADR-096), the same primitive as
  OpenCycloid's.** `earth.drives(earth_beads.travel, law=earth_lift)`
  now states it in one line, and `earth_lift(column, bead)` reads
  `bead.index` for the rank — the abacus's own real shape
  (`FrameHalf(count=count, ...).repeat(2)`, where `FrameHalf` declares a
  `count` of its own) is what decided the copy carries `index` and not
  `count`. The abacus becomes refactorable at stage B in its own
  repository's own cycle.
- **A carried body: the orbit primitive, second sighting.** YouCanBuildDog's
  five lower-leg parts per leg translate by `R(θ)·s − s` with their
  attitude fixed — one coordinate, but not one coordinate on one axis.
  With the API as it stands each would need two prismatics and two trig
  laws with no inverse (forty joints and forty laws for four freedoms).
  Wanted, exactly OpenCycloid's:

      carried = Orbit(axis=(1, 0, 0), radius=40.0, phase=-55.0, unit='deg')
      swing.drives(carried.orbit)

  The dog's `MovingHalf` also turns about the joint centre and slides
  along the channel — two joints on one body whose order matters
  (`T(slide)·R(turn)`), the third sighting of the composition-order gap.
  Deferred at stage A on both. **That third sighting is FIXED** (cycle
  `joint-composition-order`, ADR-093): `pivot` declared before `slide`
  now composes `T(slide)·R(turn)` whatever binds them. The carried
  lower-leg parts still want `Orbit`, which is NOT built, so
  YouCanBuildDog's deferral stood on the orbit finding alone.

  **FIXED (cycle `orbit-joint`, ADR-094).** `Orbit` is built, and it
  takes neither a radius nor a phase: the dog writes
  `carry = Orbit(axis=(1, 0, 0), at=(0, *SHORT_PIVOT),
  carries=(0, *KNEE_PIVOT), unit='deg')`, and the framework derives the
  per-leg 40.0000 and 39.9239 mm and the -55.000 and -55.1033 degrees
  from the two pivot positions `layout.LINK_SPANS` already measures —
  the 0.076 mm short back-left leg included, and its phase corrected
  from the -55.104 the project's proposal typed. The default carried
  point is not enough here: five bodies per leg, five rest placements,
  one shared offset, so the knee pivot is named. YouCanBuildDog now
  waits on nothing and becomes refactorable at stage B.
- **A path on one body, per repeated copy: fender-bender's bracket
  release.** One freedom, `lift`, realized as `T(dx, dz, 0)·Rz(-tilt)` in
  each channel's own frame from nine measured waypoints, on five channels
  held by `.repeat()`. It hits three of the findings above at once —
  several joints composing on one body, an anchor at the copy's own
  placed origin (`channel_y(index)`), and a relation fanning out over a
  repeated child with a per-copy law. Wanted, either three joints with a
  stated composition order, or

      release = Path(RELEASE_WAYPOINTS, at=OWN_PLACED_ORIGIN, unit='mm')

  Deferred at stage A. The two motions the API states today — the
  filament wheel's spin and the lock pin's draw — wait with it; the
  loop's `drop` port feeds molejo geometry and is not a forwarder.
  One of its three blockers is gone — several joints on one body now
  compose in declaration order (ADR-093) — and a second is now gone too:
  **FIXED (cycle `repeat-fan-out`, ADR-096)**, the per-copy fan-out over
  `.repeat()`. The own-placed-origin anchor is the one blocker still
  untouched, so fender-bender's deferral stands on it alone.
- **A joint on a child built from data, not from a class body.** OpenVMP
  Don1's links realize their parts in a loop from PartCAD `.assy`
  blueprints, one generic `StepPart` per entry named by the file. A joint
  is class metadata and a relation path is checked against declared
  children, so none of the 82 drive-train parts that visibly turn — worms,
  worm gears, shafts, sprockets — can carry a joint or be reached by a
  relation; nine `spin()` call sites stay hand-written, each with its own
  frame inversion. Wanted:

      front.yaw.drives(base['motion-front-wormgear/worm'].spin, ratio=WORM_GEAR_TEETH)

  a joint declared on a child a parent realized from data, and a relation
  that can reach it by name. The 24 declared freedoms are statable today,
  so the project proceeds; this is transmission, not dressing, and a
  later primitive adds to the refactor rather than redoing it. The same
  project is the fourth sighting of the declaration-site joint: two `Link`
  subclasses exist only to carry a joint, and `CameraArm` needs callables
  because its anchor's sign is the PARENT's handedness times its own.
- **A relation reads one coordinate; the Pascaline's pawl reads two.**
  The pawl's swing is `PAWL_DEFLECTION * (climbing(count) + ratchet(next_count) * (1 - pushing(count)))`,
  bilinear in this digit's drum and the next one's. Wanted:

      (count, next_count).drives(sautoir.pawl.swing, law=pawl_deflection)

  a relation with several sources, its law handed all of them. Today the
  pawl is a declared joint bound from that expression in one line of
  `Digit.simulate()`; the project proceeds. The same machine adds the
  sharpest own-placed-origin sighting yet — `Pawl.swing`'s anchor must
  re-evaluate the `profiles.hinge(...)` formula `Sautoir.render()`
  already computed — and a fan-out over LIST-HELD children where each
  copy gets a structurally different expression (the root's eight-way
  carry binding), which no single per-copy law would state either.
- **FIXED (cycle `joint-composition-order`, ADR-093). Composition order,
  fourth sighting, and the minimal unblocker.** The
  Internal Cycloidal Actuator's two disks each want `orbit` (about the
  drive axis, 1:1 with the eccentric shaft) and `spin` (about their own
  bore, `ratio=-1/8` with a mesh-phase offset) on ONE body: the tree is
  `solid import-step` output mirroring the document one-for-one, so there
  is no carrier body to hang the orbit on and inventing one would break
  the one-to-one reading and sixteen tests. It is blocked on the
  composition-order contract alone — joints of one class compose in
  declaration order, innermost first — which is therefore the smallest
  primitive that unblocks it, OpenCycloid and the hexapod at once. Its
  preferred `Orbit` form, if one is built, anchors the carried point
  (`Orbit(axis, at=<carried point>)`) rather than taking a radius and a
  phase, because the eccentricity is a derived value there.

  The contract exists: `spin` declared before `orbit` is applied inside
  it, whatever order the two relations solve in. This project is
  unblocked by ADR-093 alone and is the sighting that named it the
  minimal unblocker. Its `Orbit` preference was an open want, not a
  blocker.

  **That want is now FILLED (cycle `orbit-joint`, ADR-094)**, with one
  keyword renamed: the carried point is `carries=`, not `at=`, because
  `at` may not mean the line for a `Revolute` and the carried point for
  an `Orbit` — so the disk reads
  `spin = Revolute(axis=(0, 1, 0), at=DISK_1_BORE_CENTRE)` then
  `orbit = Orbit(axis=(0, 1, 0), carries=DISK_1_BORE_CENTRE)`, `at`
  keeping its default because the actuator axis runs through the parent's
  origin. Nothing is typed that the project's spec forbids: the 2.000 mm
  eccentricity and the -79.0959 degree phase are derived from the bore
  centre and the axis. The project's own algebraic identity between that
  form and today's `_simulate_disk()` is a framework fixture
  (`tests/test_joints.py::ProjectAlgebraTest`), measured at a rotation
  deviation of exactly 0 and a position deviation of 4.4e-16 mm. Its
  proposal lists `orbit` before `spin`, which was written before ADR-093
  fixed first-declared-innermost: at stage B the two transpose.
- **FIXED for the composition half (cycle `joint-composition-order`,
  ADR-093). Composition order, fifth sighting: a delta printer's rods.** The Mini
  Kossel's six rods each hang between a carriage and the effector; a rod's
  pose is a spin, a lean, a swing and a rise — four joints on one body
  whose order is the whole of its attitude and which a reader of the class
  cannot see. The effector's three prismatics commute and the carriages
  and pulleys are one joint each, so the composition contract is again the
  one thing missing; the delta law itself (three drivers to each rod) is
  the multi-source relation already recorded. Deferred at stage A.
  The four joints on one rod now compose in declaration order (ADR-093);
  the multi-source relation the delta law needs is a SEPARATE finding and
  is still open, so kossel waits on that one.
- **A bare number cannot be added to a dimensioned token.** The
  Pascaline's slide span, `CHANNEL_Y[1] - CHANNEL_Y[0] - SLIDE_WIDTH - 2 * clearance`
  with `clearance` a declared `Length`, is refused at class definition
  (`DimensionError: 27.0 is dimensionless and <L> is L`): the parameter
  algebra lets a number MULTIPLY a token but not add to or subtract from
  one, so a layout constant in millimetres must be wrapped as
  `Length(...)` before it meets a token. Met writing a `ratio=` and a
  joint `range=`; not a motion-layer gap but the first time the algebra
  was asked this in a class body rather than in `render()`.
- **Declaration-site joint, sharpest form: the Prusa i3's Z screws.** Each
  screw's anchor is `(±17, 0, 0)` by the PARENT's `left` flag, so neither
  an own-placed-origin mode nor a callable of the realized child can
  state it, and giving `ZScrew` a parameter for it would mint a second
  cached exact ISO thread. The two screws keep a port and one `rotate`
  each. Wanted, as before: `screw = ZScrew(turn=Revolute(axis=(0, 0, 1), at=(side * 17, 0, 0)))`
  resolved against the declaring parent's parameters.

  **CORRECTED (cycle `joint-frame-follows-declarer`, ADR-097).** This
  entry's claim that no recorded candidate fix reaches the Z screws was
  wrong once the frame itself is the fix rather than a mode within it.
  `ZScrew` is drawn along its own `+Z` from its own origin and each side
  is placed by a pure `translate([±17, 0, 75])`; under the new rule
  `turn = Revolute(axis=(0, 0, 1), unit='deg')`, own-frame, no anchor at
  all, states BOTH sides with one declaration — the project's own
  reviewed proposal already conceded the own-origin mode "would" reach
  this case, and the survey confirms it. The declaration-site keyword
  below is still wanted for the five axes decision 3 of that cycle
  found, which this Z-screw case is not one of.
- **OpenFlexure: two lighter sightings.** (a) Fan-out over `.repeat()`
  with the IDENTITY law: the three stage nuts and the gear lock screws
  simply follow one coordinate each, so a `.repeat(n, travel=column.travel)`
  wiring would do without any per-copy law — the weakest form of the
  fan-out finding, worth building first.

  **FIXED (cycle `repeat-fan-out`, ADR-096).** Measured, not assumed:
  `Bead(travel=earth).repeat(4)` already binds every copy through the
  existing per-instance wiring mechanism
  (`evidence/probe_wiring_repeat.py`), because a wiring is downward-only
  and needs no PATH for its source — `shaft_pin.turn.drives(gear_screws.orbit)`
  is the case a wiring cannot state, and it is exactly a broadcast
  relation with the default ratio of one. No `.repeat(n, travel=...)`
  keyword was built; it would have given the identity case a second
  spelling and the path case nothing. (b) The third 2026-09-09 limit
  again: a coordinate a class's own relation binds is unbound inside that
  class's own `simulate()`, which forced the actuator's thread ratio up
  one level into `Axis`. The four flexure legs (two rotations each, on
  repeated bodies, from a multi-source law) stay hand-written as
  followers; the principal chains are statable and the project proceeds.
- **FIXED for the composition half (cycle `joint-composition-order`,
  ADR-093). Composition order, sixth sighting, and a joint under a
  conditional placement: the InMoov hand.** Eight phalanx bodies (middle phalanges,
  fingertips, thumb tip, the `dip` fasteners) each carry two
  non-commuting rotations, and the fingers are `.repeat(4)`; nesting the
  phalanges or naming the fingers one by one would state the motion
  today but renames every leaf and breaks six tests, which is refactoring
  around the gap. New form of the declaration-site joint: `Forearm.render()`
  applies `present()` conditionally to its direct children, so the wrist
  group's parent-frame axis depends on a flag the gear, clevis and bolt
  cannot see from their own classes. Deferred at stage A on the
  composition contract; the tendon ratios (`-50/FINGER_CLOSED` and
  siblings) and the 11:20 wrist train are ready to be sentences.
  The two non-commuting rotations per phalanx now compose in declaration
  order (ADR-093). The conditional-placement form of the
  declaration-site joint recorded in the same entry is UNTOUCHED and
  still open, and Inmoov-sim waits on it.
- **FIXED for the composition half (cycle `joint-composition-order`,
  ADR-093). Composition order, seventh sighting: the V8's connecting
  rods.** Each
  rod is `T(crank pin)·R(rod angle)` on one body, eight of them on
  `.repeat()` units driven through a per-unit phase; the pistons, valves,
  camshafts (`cam = crankshaft.turn / 2`, a derived coordinate) and the
  crank itself are statable today. The rod reads as `Orbit(axis, at=<the
  pin>)` plus its own `Revolute`, or as two joints under the declaration
  order contract. Deferred at stage A. The four timing gears are the
  eighth own-placed-origin sighting (one class, four anchors).
  The two-joint form is now statable (ADR-093), and the orbit half is
  built too (ADR-094, cycle `orbit-joint`): the rod reads
  `swing = Revolute(axis=(1, 0, 0))` then
  `orbit = Orbit(axis=(1, 0, 0), carries=(0, 0, CRANK_RADIUS))` — the
  carried point spelled `carries=`, and `at` keeping its default because
  the crank axis runs through the cylinder unit's own origin, which its
  class docstring states. The rod MUST name `carries`: it is not placed
  by `CylinderUnit.render()`, so its own placed origin is the unit
  origin, which is ON the crank axis, and the framework refuses a
  carried point there by name. Its listing writes `orbit` before
  `swing`; at stage B the two transpose. The own-placed-origin finding
  the four timing gears carry is untouched and still open, and the V8's
  deferral stands on that.
- **FIXED (cycle `whole-tree-fixpoint`, ADR-099). An ancestor's relation
  cannot SOURCE from a coordinate a descendant's relations solve.** The
  mirror of reaching by path: OpenFlexure's root
  stated `z_axis.actuator.column.travel.drives(body.lower_strut.swing, law=...)`,
  but the column's travel is bound by `Axis`'s own relations, which run
  after the root's, so the root's solve found it unreached at every
  pose. The four flexure laws had to be re-sourced from the root's
  `z_motor` driver with the step-to-travel conversion composed into each
  law. Same root cause as the one-class-body rule (no whole-tree
  fixpoint); the candidate fix already listed — defer an unreached
  relation until the descendants have solved, then re-run once — would
  make the sentence as written work.
  **What shipped:** the same whole-tree fixpoint as above. Proven on
  this exact shape
  (`tests/test_couplings.py::TreeFixpointTest::test_an_ancestor_sources_from_a_descendant_solved_coordinate`).
  An overlay restoring openflexure's own root sentence as written (task
  9.5 of the change) is NOT proven here, deferred for time; the
  project's own base-against-head pose comparison, unmodified, is
  0.000e+00 (`evidence.md` §9).
- **FIXED (cycle `whole-tree-fixpoint`, ADR-099). An author-bound joint
  keeps its value but loses its motion between
  runs.** A standalone root that binds its own joint in `simulate()` as a
  rest default with `if value is None: bind` stands correctly once, then
  at rest forever: the joint's operations are swept at the start of the
  next run as every simulate-phase motion is, but the coordinate's VALUE
  survives, so the guard skips the rebind and nothing re-applies the
  motion. Prusa i3's X and Y axes and extruder showed it as 37.5 mm,
  70.4 mm and 0.05 mm pose deviations on a second render; the fix is to
  rebind unconditionally. The hangprinter's winches carry the same guard,
  masked by a zero default. Candidate fixes: clear an author-bound
  joint's value with its swept motion, or refuse the read of a stale
  value by name.
  **What shipped:** clear, chosen over refuse (design.md §6 of the
  change): the value and binder of every coordinate an assembly bound
  during its PREVIOUS phase are dropped at the start of its next one,
  the author's own binding included. Measured live against Prusa i3's
  and hangprinter's OWN current, already-defensive code (an unconditional
  rebind pattern that works around this exact gap): both now measure
  0.000000 mm on a second render, on the base commit BEFORE this cycle's
  code changed anything (`openspec/changes/whole-tree-fixpoint/evidence.md`
  §0.6) — the fix keeps that true rather than needing to make it true.
  A synthetic reproduction of the naive (bind-inside-guard) shape those
  projects no longer write is proven directly
  (`tests/test_joints.py::StaleAuthorBoundJointTest`). A second, more
  severe defect surfaced only once the fix was measured against the
  FULL tree rather than a project in isolation: two assemblies
  alternating which one binds ONE coordinate across runs (Prusa's root
  relation `x.drives(xaxis.carriage.travel)` racing `XAxis`'s own
  rest-default guard) let the later one's stale record of its own past
  binding erase the value the earlier one had ALREADY correctly produced
  THIS run; fixed by scoping the clear to `_enum_marker`, the
  enumeration a slot was last bound in, not merely to which assembly
  bound it last time. Proven on Prusa i3's and abacus's own trees, base
  against head, from an unmodified `git archive HEAD` snapshot of each:
  0.000e+00 over every pose
  (`openspec/changes/whole-tree-fixpoint/evidence.md` §9).

# 3DPrintedClocks wall clock 02 (2026-09-09, exact sweep cost)

Measured on `solid test wall_clock_02` under the exact kernel, at the
primary's 1822221: 1175 s for 16 tests, of which the two sweeps
(`@testing_steps(48)` over the swing, `@testing_steps(32)` over the great
wheel's turn, each calling `assertNoUnintendedSolidInterference`) are
~18.5 min. A sweep instant costs ~19 s, essentially all of it in
`BRepAlgoAPI_Common`: 53 topmost rigid solids, ~118 candidate pairs from
the world-AABB broad phase, ~110 booleans re-run per instant, every one
of them empty. Placement, BREP copies and keyframe binding are under
0.3 s per instant. Findings, in order of leverage:

- **The verdict memo misses co-moving pairs on float noise. Fixed** by
  cycle `quantise-verdict-memo` (ADR-090, amending ADR-070). The key was
  the exact bytes of `inv(M1) @ M2`. Of the 118 pairs, 30 are carried
  together (pendulum, motion works, weight and its line) and differ
  between instants by ~1e-13 — the noise of composing a rotation through
  a parent — so a question the memo already held was re-asked at every
  instant. The key now quantises the relative matrix to a run-level
  placement quantum (default 1e-9 mm, `--placement-quantum`/
  `SOLID_TEST_PLACEMENT_QUANTUM`, `0` restoring the exact-bytes key).
  Measured on the same test (`wall_clock_02`,
  `test_movement_runs_free_through_a_swing`, `@testing_steps(48)`, exact
  kernel): booleans 3820 → 2526 (33.9% fewer, exactly the rise in memo
  hits, 1823 → 3117) and wall time 779.37 s → 533.39 s (31.6% faster,
  keeping the same test verdict). Full counts and the quantum-0 control
  run in `evidence.md` of the `quantise-verdict-memo` OpenSpec change.
- **A common rigid turn inflates every world box. Fixed** by cycle
  `broad-phase-indexing-frame` (ADR-091, extending ADR-029). The clock
  declares `facing` on each child of its root — `Clock.render()` applies
  `rotate(self.facing, Z)` to each direct child, not to the root, which
  carries no placement of its own — so every topmost rigid solid shares
  one outermost rigid turn, and the movement's AABBs, taken on world
  axes, all grow by up to √2 and pairs that never meet overlap. At
  `--set facing=0` the same model yields fewer candidate pairs (see
  below). The broad phase now takes its boxes in a chosen INDEXING
  FRAME instead of always on world axes: the world frame, or the
  placement frame of one of the assembly's `K = 3` largest topmost
  solids by local-bounds diagonal, whichever scores the smallest total
  (padded) box volume — a fix that reaches the turn wherever it was
  declared, not only on a root that carries no placement of its own.
  Measured on `wall_clock_02` at the first swing-sweep instant: 116
  candidate pairs at the declared `facing=45` before, 67 at
  `--set facing=0`; after, 67 at `facing=45` (chosen frame: `standoffs`,
  tied with `plates` — the fused frame this bullet is about, both among
  the top two candidates by diagonal) and 67 at `facing=0` (world frame,
  unaffected) — the chosen frame recovers the un-turned candidate count
  exactly. Over the full 48-instant swing sweep
  (`test_movement_runs_free_through_a_swing`, exact kernel, default
  `facing=45`, measured against the tree after `quantise-verdict-memo`):
  booleans 2526 → 1089 (56.9% fewer) and wall time 533.39 s → 265.99 s
  (50.1% faster), same test verdict. Full counts, the chooser's own
  ranking and scores, and the honest comparison against the finding's
  3x forecast are in `evidence.md` of the `broad-phase-indexing-frame`
  OpenSpec change.
- **One enclosing solid defeats whole-solid boxes. Fixed** by cycle
  `face-box-broad-phase` (ADR-092, extending ADR-029 and ADR-091). One
  correction to this bullet's own wording first: "the fused frame (both
  plates and their pillars, one solid) sits in 40 of the 118 pairs" was
  never quite right — `broad-phase-indexing-frame`'s own evidence had
  already shown `standoffs` and `plates` are two separate topmost solids,
  not one fused one, and this cycle's own measurement (67 candidate pairs
  at the first swing-sweep instant, the tree after
  `broad-phase-indexing-frame`) shows neither one dominates the pairs a
  face-box tier cannot decide: of the 57 pairs the tier declines (it
  decides the other 10 without a boolean), `wheel` (the train's five
  wheels) appears in 24, `rod` — a 3-face cylindrical shaft the wheel
  train is mounted on — in 23, `plates` in 9 and `standoffs` in only 3.
  The wheel train's mounting rod, not the frame, is what the tier cannot
  separate from the wheels bored onto it — a genuinely close fit, not a
  spurious enclosure.

  A second exact-negative tier now runs after the AABB cull and before
  any boolean, for a pair of EXACT solids: each solid's face boxes
  (`BRepBndLib.Add_s(face, box, False)`, cached once per shape identity)
  are compared in one solid's own frame, and if none of one solid's
  meets any of the other's, a containment guard — one representative
  vertex of every solid of each shape classified against every solid of
  the other, in both directions — tells a genuine disjoint pair from one
  solid wholly inside the other before reporting it empty. Measured over
  the 48-instant swing sweep
  (`test_movement_runs_free_through_a_swing`, exact kernel, default
  quantum, `facing=45`, against the tree after `broad-phase-indexing-frame`):
  booleans 1089 → 708 (35.0% fewer — the tier decided 381 of the 1089
  memo-misses without a boolean) and wall time 265.99 s → 216.50 s
  (18.6% faster), same test verdict; keyed asks and memo hits are
  unchanged at 3210/2121, as expected since this tier does not change
  which pairs are emitted. At the first instant the tier's own cost was
  0.955 s (its containment-guard share 0.770 s across 10 classifier
  calls) against 10.04 s of boolean time for the 57 declined pairs —
  smaller than the ~8 s this bullet once attributed to plates × wheel
  booleans alone, because the dominant surviving cost turned out to be
  the mounting rod, not the plates. Full counts, the surviving pairs'
  solids, and the tier's own cost are in `evidence.md` of the
  `face-box-broad-phase` OpenSpec change.
- **An exact solid's index bounds are inscribed, not conservative.**
  `_solid_geometry` takes every topmost solid's local bounds from the
  STL mesh even for an exact solid; a tessellation's vertices lie ON the
  exact surface, so those bounds fall up to the declared linear
  deflection (0.1 mm default) short of the exact extents on a curved
  face, and a sub-deflection overlap at a box boundary could in
  principle be culled by the whole-assembly index. The fix: an exact
  solid's local bounds become the union of the exact face boxes
  `face-box-broad-phase`'s `cached_face_boxes` already computes; faceted
  solids keep mesh bounds. Left for a separate cycle for three reasons
  (design.md section 8 of `face-box-broad-phase`): it reverses two
  ratified sentences of `Accelerated intersection evaluation` ("The
  bounding boxes the broad phase transforms SHALL come from the cached
  base mesh for every solid, exact or faceted" and "The candidate pairs
  a given assembly emits SHALL NOT depend on whether its solids carry
  exact geometry"); it must not fire under the faceted kernel, where a
  run may not read any solid's `shape()` at all; and it moves WHEN an
  exact solid's faces are measured, from "when a candidate pair reaches
  the face-box tier" to "at selection", including solids no candidate
  pair ever compares. **Filed:** cycle `exact-solid-index-bounds`.
- **A mesh-distance exact-negative tier** (distance above twice the
  declared linear deflection proves the exact solids disjoint) and
  **parallel pair booleans** (the run used 225 % of 1600 % CPU; OCCT's
  `SetRunParallel` thread pool deadlocks under `fork`, so workers must
  spawn) are the two remaining framework levers. The three cycles this
  bullet once deferred them behind — `quantise-verdict-memo`,
  `broad-phase-indexing-frame`, `face-box-broad-phase` — have all landed
  and are measured above.
- Not a framework fix: fusing the plates and pillars into one solid is
  the project's choice, and `cProfile` over `solid test` reports garbage
  totals (instrument directly).

# Inmoov-sim stage B (2026-09-10, first project on ADR-093)

Found resuming the InMoov hand and forearm on the composition-order
contract. Stage B went through unchanged: eighteen `Revolute`s on twelve
classes, twenty relations, poses max deviation 0 on both models, both
suites green with no test edited. Two findings, neither blocking.

- **A subclass cannot put its own joint INSIDE an inherited one.** ADR-093
  orders a class's joints base-first and a redeclaration keeps the base's
  slot, so a `ThumbFingertip(Fingertip)` inheriting `dip, pip, mcp` in
  slots 0-2 gets its own `tj` in slot 3 — outside `mcp`, which is the
  wrong side of the knuckle — and redeclaring cannot move it. The project
  restructured: both tips now subclass a jointless `GluedTip` and declare
  their own stacks. Same node names, children and paths, so the cost was
  one class, not a hack; but a body whose subclass adds an INNER freedom
  has no way to say so short of re-parenting. Candidate fix, if a project
  ever needs it: an explicit slot keyword, rejected by ADR-093 for lack of
  a sighting — this is the first, and it was absorbed.
- **Declaration-site joint, third direction: a parent whose own frame is
  conditional.** `Forearm.render()` applies `present()` to its direct
  children only when `self.presented` is true, so the wrist group's
  parent-frame axis (gear, clevis, axle, hand) depends on a flag none of
  their classes can see; they stay hand-written in `Forearm.simulate()`
  with `_about_axis`. Wanted, as the earlier sightings:

      gear = WristGear(turn=Revolute(axis=wrist_axis, at=wrist_anchor, unit='deg'))

  with the callables evaluated against the realized PARENT. The wrist
  pinion did escape (`wrist.drives(drive.pinion.spin, offset=...)`)
  because `WristDrive` is built in the pinion's frame. `Hand.simulate()`'s
  ten `connect()` calls were carried on the `.repeat()` fan-out finding;
  **moved to the tuple-source cycle instead** now that fan-out is FIXED
  (cycle `repeat-fan-out`, ADR-096), because a broadcast has one SOURCE
  and `Hand` drives each of its four repeated fingers from a DIFFERENT
  driver. That is a per-copy source, not a per-copy law, and closes with
  a future cycle's tuple source (`(driver_a, driver_b, ...).drives(...)`),
  the law picking by `finger.index`.

# hexapod_spiderbot_model stage B (2026-09-10, first project on Free)

Found resuming the SpiderBot on ADR-093 and ADR-095. Stage B went through
unchanged: `pose = Free(...)` on the chassis driven by four root
relations, three `Revolute` declarations for eighteen leg freedoms, the
root's `simulate()` gone; poses bit-identical over 28 poses and 172
leaves, 34/34 green, no test edited. One finding, not blocking.

- **A dotted coordinate name can be written but not read by name.**
  `declared_ports(Chassis)` reports a `Free`'s six coordinates under
  dotted keys (`pose.roll`, ...), and `set_coordinate(node, 'pose.roll',
  value)` binds one; but there is no reader: `getattr(node, 'pose.roll')`
  raises `AttributeError`, so every consumer that iterates
  `declared_ports` and reads each name — the shop's own
  `capture_poses.py` was the first — records an error for all six. Exactly
  the consequence ADR-095 predicted, arriving on the primitive's first
  use. Wanted, the read counterpart of the writer:

      get_coordinate(node, 'pose.roll')      # the bound slot, or None

  exported beside `set_coordinate`, and the ports spec saying that a
  name the enumerator reports is a name the framework can read back.
  Nothing in the project needs it (`self.pose.roll.value` reads fine).

  **FIXED (cycle `repeat-fan-out`, ADR-096).** `get_coordinate(node,
  name)` is exported from `solid_node.motion.ports` beside
  `set_coordinate`, mirroring it segment for segment, returning the
  bound slot — `None` value for an unbound one — and refusing a name
  `declared_ports` does not report by name rather than answering `None`
  for that case too. The ports spec now states the pairing as a
  requirement.
- The "own-placed-origin" anchor sighting again: `Femur.lift` and
  `Tibia.knee` restate the parent's `translate` as `at`.

# joint-frame-follows-declarer (2026-09-10, closing the own-placed-origin finding)

**CLOSES the "a joint cannot be anchored at a design-placed part's own
origin" finding**, open since wall clock 01/Thor (2026-09-09) and
re-sighted in the hexapod, the V8, Poseidon, OpenMANIPULATOR-X, the
Pascaline, fender-bender, the Prusa i3 and InMoov. ADR-097 answers it
directly rather than adding a mode: a joint written in a class body is
now read in that body's OWN rest frame, `at` defaulting to the body's
own origin, so the mode this finding kept asking for is simply the
frame, not a special case within the old one. Measured over the whole
catalogue (`evidence/survey.md`, the change's own evidence): 23
projects, 249 class-body joint declarations, 133 of them exactly this
shape (69 restating a placement, 64 already anchorless) plus roughly 30
hand-written rotations the rule newly makes declarable. A 24th project,
OpenCycloid, joined the catalogue mid-cycle (see below). Of the 24, 23
compare at maximum deviation 0 against a mechanical rewrite (three
grasshopper clocks and one hangprinter roller first deviated and were
each traced to a cause and closed at 0 -- the entries below); the one
real nonzero is wall clock 48's own already-migrated source, carried to
the pilot. OpenCycloid's own default-only rewrite now REFUSES to bind
rather than building silently wrong (see "OpenCycloid" below). Seven
clocks show a residue under 8 microns on a wound-string port that two
captures of the SAME tree reproduce against each other and
`PYTHONHASHSEED=0` removes: capture-process nondeterminism, not this
change (last entry below). Full numbers: `evidence.md`
§7 of `joint-frame-follows-declarer`.

Two things the finding did not anticipate, filed as their own entries
rather than folded into the closure:

- **Five axes lose their literal.** Where one class is placed at
  several sites with OPPOSED rotations — Prusa `XGuide`/`YGuide`
  (`.repeat(2)`, `along_y`/`along_minus_y`), hangprinter's mirrored
  `MotorGear` and its `RollerBearing` pair, OpenVMP's two `Leg`s — one
  parent-frame axis literal served every site; the own-frame axis is
  different per site and cannot be written as one literal. Two of the
  three projects state the choice as a deliberate design decision in
  their own source (`hangprinter/simulation/winch.py:57-64`). Two
  bridges exist and neither is new machinery: a callable of the
  realized node reading the body's own parameter or a `.repeat()`
  copy's `index` (from `repeat-fan-out`, ADR-096), or the parent
  supplying the sign in the relation (`ratio=-1`, or `law=` under a
  broadcast) — which is what Thor already does. Neither is built by
  this cycle; the literal is wanted back at a declaration site, which is
  `declaration-site-joint`'s open question: whether that keyword should
  itself be repeatable, since three of these five really want it on a
  `.repeat()` copy.
- **3DPrintedClocks disagrees with itself, and the rule settles it in
  clock 48's favour.** Clocks 19, 21, 22, 41, 49 and 51 (six, each with
  its OWN local `TurningArbor(Arbor)` class -- `Arbor` there is the
  plain-geometry `parts.Arbor`, not the motion-composing
  `shared.TrainArbor`) write `at=lambda node: arbor_bearing(node)` on a
  leaf `place_train_arbor` has already translated by that same bearing
  (as one of `FixedRodArbor.render()`'s CHILDREN, unlike the shared
  module's own `TrainArbor.turn`, whose placement of ITSELF is the
  identity and needs no change); wall clock 48's `TurningArbor`/
  `TurningPalletPin` write NO `at` at all, with a source comment
  (`wall_clock_48/clock.py:135-140`) explaining that the plate-frame
  bearing "applies that offset twice." Under the OLD rule exactly one
  of the two families was wrong wherever the bearing is not the
  origin; wall clock 48 already reads as the new rule wants, unedited
  -- its source was written for a rule the framework did not have yet.
  The six unmigrated clocks were fixed the same way wall clock 48's own
  source already reads (delete the `at=`); a first pass at this fix
  left them unpatched and the pose overlay caught it immediately (166.2
  mm on wall clock 49, 177.2 mm on 51, present even at `defaults`, on
  `movement.train.*`). Wall clock 48 itself is the one place in the
  whole survey that does NOT compare at zero: `AnchorArbor`'s wheel
  (index 5) and its two pallet pins move, by construction, towards what
  the clock's own comment already asks for -- measured peak 3.985 mm at
  `time@0.5`, flat 2.841 mm at every pose that does not vary `time`.
  Carried to the pilot as a question in the change's evidence, not
  accepted here as a difference: this file's job is to record that it
  is exactly the disagreement predicted, not to
  judge whether the corrected pose is right.

- **A `.repeat()` copy's `index` does not exist yet when a joint's own
  `axis`/`at`/`carries` resolves, so "a callable of the copy's index"
  is not actually a working bridge for a JOINT argument.** Found
  applying decision 4's Bridge A to Prusa3-vanilla's `XGuide`/`YGuide`,
  hangprinter's `RollerBearing`, and OpenCycloid's `RadialBearing`/`Pin`
  in this cycle's own pose overlay: `axis=lambda node: (0, 0, 1 if
  node.index == 0 else -1)` on a `.repeat(2)` class raises
  `AttributeError: '<Class>' object has no attribute 'index'` at
  REALIZATION, every time, because `resolve_declared_joints` runs
  inside the copy's own `__init__` (ADR-088) while
  `RepeatDeclaration.realize()` assigns `child.__dict__['index'] =
  index` on the line AFTER that construction returns
  (`solid_node/node/declarative.py:391`, whose own comment already says
  "no sighting needs `index` during construction" — true for a LAW
  resolved later, false for a joint argument resolved eagerly).
  `MotionWorksPart`'s existing `at=lambda node: ... node.index ...`
  works today only because `index` there is a DECLARED PARAMETER
  (`Count(min=0, max=2)`, passed as a constructor kwarg), not a
  `.repeat()`-assigned attribute — the working and the broken case look
  identical at the call site and are easy to conflate, which the
  overlay did once. Worked around, three times over, by deriving the
  axis from the copy's ACTUAL placement in the PARENT's `render()`
  instead of a class-body callable — the overlay's own
  `derive_helper.axis_from_placement`, `_carry`'s own arithmetic reused
  for one run. Candidate fix: resolve a REPEATED class's joint
  arguments once per copy, after `index` is assigned, rather than
  inside the copy's own `__init__` — or let `resolve_declared_joints`
  defer a `NameError`/`AttributeError` from a callable and retry once
  the realization path can say why, naming which attribute was missing
  rather than failing opaquely. This closes the axis half of decision 4
  as WRITTEN (Bridge A does not work as stated for the five axes); the
  parent-supplies-the-sign bridge (Thor's own `ratio=`) is unaffected,
  since a relation's `law=`/`ratio=` resolves later, after `index`
  exists.

- **Two more sites in the shared clock module needed the same
  restates-to-zero treatment as `MotionWorksPart.turn`/`Pendulum.swing`/
  `Escapement.frame_turn`, found by the SAME pose overlay.**
  `ZDayPart.turn` (`wall_clock_52`, `wall_clock_54`, the day-of-week
  complication) restates `DayComplication.render()`'s
  `part.translate(positions[0 or 1])` for either branch of its own
  `node.index in (0, 1)` conditional -- own-frame anchor is `(0, 0, 0)`
  either way, so the whole conditional callable is removed. Fixing it
  did not close either clock's whole residual: `wall_clock_52` still
  shows 1.069e-03 mm (a floating-point residue on a wound-string port,
  present on several other clocks too, none of them exceeding 5
  microns) and `wall_clock_54` still shows 3.477 mm on an UNRELATED
  leaf (see the grasshopper `entry_arm` finding, below).
- **CLOSED. Three grasshopper-escapement clocks (`wall_clock_21`,
  `wall_clock_53_grasshopper`, `wall_clock_54`) showed a deviation
  confined to `movement.escapement.entry_arm`, zero at `defaults` and
  growing with `time` (0.681/2.321/3.954 mm on `wall_clock_21`;
  1.162/3.477 mm on the other two) -- traced to a missed citation, not
  a new framework finding. Each clock's OWN `parts.py` declares
  `PalletArm.turn = Revolute(axis=Z, at=lambda node: (*node.built.
  grasshopper.drawn_position('G' if node.exit_side else 'P'), 0.0))`,
  a RESTATES site `evidence/survey.md` §1.3 (line 142) already names
  correctly for `wall_clock_53_grasshopper` and `wall_clock_54` --
  `assemblies.Escapement.render()` translates each arm by exactly that
  same pivot -- but `wall_clock_21` has the identical class and was
  missing from that row's citation list, so `patch_3DPrintedClocks.py`
  implemented every other row but this one. Only the entry arm ever
  deviated because the exit pivot `'G'` is at the origin, matching
  every measured number exactly. Fixed by deleting the `at=` in all
  three clocks' overlay `parts.py`; re-captured sequentially, all three
  now compare at 0.000e+00.
- **CLOSED, by using the cheaper bridge. hangprinter's
  `RollerBearing.spin` axis derivation had an unexplained residual on
  exactly one roller** (`ceiling.winch_d.rollers-0`, up to 1.986 mm,
  growing with driven angle): a runtime-injection workaround (deriving
  the axis at the end of each winch's `render()`, because a `.repeat()`
  copy's `index` is not available at eager joint-argument resolution --
  the entry above) correctly reached `winch_c`'s roller but left
  `winch_d`'s roller-0 reading the class's own placeholder axis
  literal, unfixed -- an ordering race in the workaround itself, never
  identified further. `evidence/survey.md`'s own row 241 already states
  the two per-site literals this joint actually needs
  (`(0, 0, -1)`/`(0, 0, 1)`, one per `BELT_ROLLERS` entry a roller is
  zipped against, the SAME pair for `WinchABC` and `WinchD` alike) --
  cycle 2's simplest bridge, a plain per-site value, not a callable of
  an unavailable `index` and not a runtime derivation either. Fixed by
  replacing each winch's `rollers = RollerBearing().repeat(2)` with two
  NAMED, non-repeated leaves (`roller_a`/`roller_b`), each a trivial
  `RollerBearing` subclass carrying its own literal `spin` axis -- no
  `.repeat()`, no `index`, no injection, no race to have a bug in.
  Re-captured once: every roller, on every winch, at every pose,
  compares at exactly 0.000e+00 (checked leaf-by-leaf against the
  renamed nodes directly, since the compare tool's own path-matching
  reports a rename as one node missing and one new rather than a
  diffable pair).
- **OpenCycloid (added to the survey mid-cycle, its own stage B landing
  on `d07b14c` while this survey was being read) shows the same
  `at`/`carries` asymmetry as the Internal Cycloidal Actuator, but
  because its OWN source already declares both `Orbit`s fully
  defaulted -- no `at=lambda ...` to delete -- a plain default-only
  mechanical migration does not go silently wrong here: it REFUSES.**
  `CycloidalDiskStageOne.orbit`/`StageTwo.orbit` and
  `RadialBearing.orbit`/`Pin.orbit` all default both `at` and `carries`
  to the body's own origin under the new rule (where the old rule's
  asymmetric defaults -- `carries` to the sentinel own-placed-origin,
  `at` to the literal parent origin -- gave every one of them a real
  eccentricity for free); with both at the same point the derived
  radius is zero and `Orbit.placement` refuses at first bind, by name:
  `ValueError: stage_one (CycloidalDiskStageOne): joint 'orbit' carries
  a point that lies ON its own axis, so binding it would move nothing.
  ... the radius they derive is 0.0.` This was confirmed directly
  against the UNPATCHED project. The overlay's own DERIVED fix (parity
  with the Internal Cycloidal Actuator's `BORE_AXIS_POINT`) reaches
  0.000e+00 over 7 poses once each disk's own-frame anchor is restated
  as the NEGATION of its own placement translate -- a first attempt
  used the same sign as the placement rather than its negation and the
  pose overlay caught it immediately (9.961 mm on
  `drive.stage_one`/`stage_two`).
- **The 1-8 micron `movement.string.*` residues on seven clocks
  (`wall_clock_23`/`24`/`25`/`26`/`28`/`49`/`52`) are capture-process
  nondeterminism, not a source difference this cycle made.** Captured
  `wall_clock_24` TWICE from the SAME already-patched overlay tree (no
  file touched between the two runs): the two captures differ from
  each other by the exact same magnitude and on the exact same ports
  as the original before/after comparison (4.828e-03 mm max, on
  `movement.string.{coil_height,entry_*,pulley_*,tie_*,wraps}`).
  Re-running the same two captures with `PYTHONHASHSEED=0` fixed
  (rather than Python's default per-process random hash seed) makes
  them match EXACTLY. The string-wrap computation (molejo's wrap
  solver, reached through `movement.string`) iterates something whose
  order depends on Python's hash-randomized dict/set ordering, and a
  non-associative floating-point sum over that ordering gives a
  run-dependent last few digits -- comparing a `before2/` capture (one
  process) against an `after/` capture (a separate, later process)
  always carries this noise, independent of whether `joints.py`
  changes at all. Not a framework defect and not something this
  overlay methodology can avoid without pinning `PYTHONHASHSEED` for
  every capture; recorded here so a future comparison at this
  precision knows to pin it rather than chase phantom regressions.

# v8-engine (2026-09-10, stage B on ADR-093 + ADR-097)

- **A bound coordinate's VALUE is never cleared between simulate passes,
  so the `if self.turn.value is None: self.turn = ...` fallback idiom
  silently freezes.** The v8-engine's stage B (its `docs/move-onto-motion.md`,
  commit a25b074) needed nodes that bind their own coordinate when run
  standalone but defer to an ancestor's relation when assembled; the
  campaign's suggested idiom tests `value is None`. Measured with
  `solid test`: the operations a binding produced are swept between
  passes but the value is not, so after the first standalone bind the
  guard is never true again and every later `set_keyframe` / pose
  re-capture of the same instance keeps the first value. The project's
  bridge: an unconditional re-bind where the fallback formula equals what
  the ancestor would set anyway, and a structural `hasattr(self, 'index')`
  guard (ADR-096's per-copy stamp) where the fallback genuinely differs
  (`CylinderUnit.crank`, `ValveMotion.lift`, per-copy phase offsets).
  This is the stale author-bound value `whole-tree-fixpoint` proposes to
  CLEAR with the sweep, sighted from the other side: the fix is that
  cycle, and the `hasattr` guard should go when it lands. Filed here;
  triage: cycle 4.
- **Tooling.** `openspec validate` refuses a change with no spec delta
  ("Change must have at least one delta"), so a project migration whose
  whole point is zero behavioural change (every ADR-097 stage B: poses
  0.000e+00, no requirement touched) cannot be validated at all and is
  archived with `--yes` past a warning. Not a framework matter; noted so
  nobody fabricates a delta to satisfy the tool.

# declaration-site-joint (2026-09-10, ADR-098)

- **CLOSED: the declaration-site finding.** ADR-097 named the second
  declarer and built none of it; ADR-098 builds it. Fourteen live
  sightings in eight projects, all reproduced at maximum deviation
  0.000e+00 in a read-only overlay: OpenCycloid's twelve orbiting
  bodies (four site `Orbit`s, ten of them `.repeat()` copies, all
  REFUSED by ADR-097 alone, now binding again); the Internal Cycloidal
  Actuator's two disk `Orbit`s; InMoov-sim's seven finger `Revolute`s
  and (recorded separately) its wrist axle; openflexure-microscope's
  `GearLockScrew.orbit` on a `.repeat(2)`; Prusa3-vanilla's two belt
  guide pairs; hangprinter's roller pair; openvmp's `Leg` (two sites)
  and `CameraArm`; open_manipulator's two gripper fingers. Four
  subclasses-for-metadata are deleted in their overlays: openvmp's
  `Wheel` and `CameraArm` (with `CameraArm`'s `__init__` override and
  its two instance attributes), OMX's `LeftFinger` and `RightFinger`.
- **CORRECTED: the plan note's record.** `workflow/docs/motion-catalogue-2.md`
  §3.3 gave three example sentences and named four validation projects;
  measured against the source (`declaration-site-joint/evidence/sightings.md`
  §5), two of the three examples are ADR-097's work, not this cycle's
  (Poseidon's `ThreadedRod`, Prusa's Z screw, both already clean
  own-frame declarations with no anchor needed), the third
  (InMoov's wrist gear) is three-quarters ADR-097's (the axle is the
  one piece this cycle actually serves, and for a different reason
  than the note gives — shared catalogue hardware, not a conditional
  frame), and the fourth (the actuator's `disk_one = CycloidalDisk(orbit=
  Orbit(axis=(0, 1, 0)))`) is short by a `carries=` whose absence is a
  2 mm error and a wrong phase with NO refusal to catch it. Poseidon is
  not a validation project for this cycle at all. The corrected list of
  eight — OpenCycloid, the Internal Cycloidal Actuator, Inmoov-sim,
  OMX, openvmp, Prusa3-vanilla, hangprinter, openflexure-microscope —
  is what `declaration-site-joint`'s own proposal and evidence.md
  actually measure.
- **NEW: a parent's hand-written motion and its own site joint read two
  different frames on one child.** A parent's `self.child.rotate(...)`
  in its own `simulate()` is inserted inside the child's rest placement
  and is therefore read in the CHILD's frame; a site joint the SAME
  parent declares on the SAME child is read in the PARENT's. After
  ADR-098 a project can write both on one child and get two frames from
  one author, with nothing in the framework to catch the mismatch. No
  sighting in the catalogue is harmed by it today. Filed, not fixed;
  triage: needs its own sighting before a direction is chosen (state
  hand-written motion in the parent's frame too, at the cost of
  carrying it always; or refuse the combination by name; or leave it,
  documented, as the one seam where "declares" and "writes by hand" do
  not agree).
- **NEW: a relation cannot name a child a loop builds from data.**
  openvmp's own written-down sentence
  (`archive/2026-09-09-move-onto-motion/proposal.md:225-231`):
  `front.yaw.drives(base['motion-front-wormgear/worm'].spin, ratio=...)`.
  A relation is class metadata whose every segment is checked at CLASS
  DEFINITION against the class the previous segment names; a child
  built from a `.assy` file at construction time has no class-level
  name to check against. `declaration-site-joint` measured the OTHER
  half of this sighting — giving such a child a real, bindable
  coordinate — and found it already answered by ADR-097 and ADR-088
  alone (a project-side `TurningPart(StepPart)` subclass with a
  declared parameter and a class-body callable, built by the project's
  existing loop): no cycle in this campaign closes the relation-naming
  half, and openvmp does not get the sentence it asked for. Triage:
  needs its own cycle if a project ever needs it for real; openvmp's
  eight sites stay hand-bound in its own `simulate()` until then.
- **NEW: `type(x) is C` no longer holds for a child whose declaration
  site gave it a joint.** The specialization (ADR-098) copies the
  written class's `__name__`, `__qualname__`, `__module__` and source
  file, deliberately (a joint is not identity), so `isinstance` holds
  but an identity check against the exact class does not.
  `solid_node/node/internal.py:166` is the one place in the framework
  that makes this check — a guard against a render returning its own
  type, `type(child) is type(self)` — and a site-jointed child of a
  parent's own class would slip past it. Pinned for the ordinary case
  (`SpecializationOwnTypeGuardTest`), not fixed; no sighting in the
  catalogue reaches this guard with a site-jointed child of its own
  parent's class today.

# Inmoov-sim (2026-09-10, stage B on ADR-098)

- **A site joint's value is the line in the parent's frame where the
  child FINALLY rests, after every rest operation the parent applies to
  it — and when one of those is conditional, a plain value is silently
  wrong for the other branch.** `Forearm` places its wrist `axle` with
  `_in_wrist` and then, when `presented` is true, `present()`'s turn;
  the site joint `Bolt(turn=Revolute(axis=..., at=...))` written as the
  plain pre-presentation numbers reproduced the reference poses only
  with `presented=False`, and with the project's own default missed by
  622 mm³ of palm/axle interference at rest and 14.2 mm at full wrist
  travel, with no refusal. Correct: a callable of the realized parent
  (`_presented(vector)` rotating the value through `PRESENTATION` when
  `forearm.presented`), which is the ADR-098 contract working as
  designed — the parent's frame is where the child ends up — but nothing
  in the docs says a plain site value should be treated as suspect
  whenever the parent's own rest placement of that child is conditional.
  Triage: one sentence in `docs/driving.rst`'s site paragraph and in the
  shop craft skill; no framework change.
