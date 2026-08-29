## 1. Dependency wiring (development)

- [x] 1.1 Install molejo editable into the workspace venv from the molejo
      checkout; link the molejo npm package into the widget's
      `node_modules`. Record both as development-time steps; the
      committed dependency entries (`pyproject.toml`, widget
      `package.json`, license banner) name the published forms and are
      verified in section 7, which is gated on the pilot's publication
      decision.

## 2. FlexibleNode: a non-rigid leaf fed by ports

- [x] 2.1 Red: a flexible leaf reports `rigid = False`; a `FusionNode`
      rendering one rejects it naming both nodes; `time` access still
      raises; reading `stl` raises as on any non-rigid node.
- [x] 2.2 Red: ports declared on a flexible leaf are connectable by the
      parent assembly's `connect()`; an evaluation with an unbound port
      fails naming the node and the port; two instances of a no-arg
      flexible leaf class share one `uniq_id`.
- [x] 2.3 Implement `FlexibleNode` in `solid_node/node/flexible.py`:
      non-rigid leaf semantics, declared-port parameter surface, the
      port/parameter name-set check (both directions, loud), and the
      snapshot evaluation entry point.
- [x] 2.4 Rewrite the `leaf.py` `time` exception message to point at the
      flexible leaf instead of the roadmap.

## 3. MolejoNode: mesh path

- [x] 3.1 Red: a `MolejoNode` whose `render()` returns a molejo `Shape`
      with parameters matching its ports assembles; a non-`Shape` render
      result is rejected by namespace validation; a parameter/port
      mismatch fails naming the node and both name sets.
- [x] 3.2 Red: under a bound numeric snapshot, the node's mesh equals
      molejo's Python evaluation of the same spec and values (vertex
      count and analytic volume within tolerance); two different
      bindings give different meshes; repeated identical bindings give
      bitwise-identical meshes.
- [x] 3.3 Implement `MolejoNode` in `solid_node/node/adapters/molejo.py`
      (namespace `molejo`, export from `solid_node/node/__init__.py`),
      with mesh evaluation through molejo.
- [x] 3.4 Red: `as_scad()` writes a snapshot STL named with the binding
      hash and imports it; re-assembly at the same binding does not
      re-evaluate (mtime rule within one binding); a different binding
      produces a different artifact; the post-build sweep collects the
      unreferenced snapshot.
- [x] 3.5 Implement the snapshot artifact path.
- [x] 3.6 Red: a flexible leaf whose port is bound over animation time
      assembles without raising, contributes no geometry to the
      assembled SCAD, and writes no snapshot artifact; the published
      document still carries its spec and its symbolic `params`; an
      unbound port still fails loudly. Reproduction: v8-engine's valve
      spring, whose lift follows the crank through `$t`.
- [x] 3.7 Implement the symbolic case in the camera path only, leaving
      `bound_values()` strict for the mesh and exact paths.
  - `as_scad()` declines when `_time_fed_ports()` is non-empty,
      keyed on solid2's `$t` token rather than on symbolic-ness, so a
      raw driver token still fails loudly (the pre-existing
      `test_a_symbolic_binding_on_the_scad_path_fails_loudly` keeps
      passing unchanged). Framework suite: **990 passed, 0 failed**
      (985 + 5). v8-engine rebuilt: version-3 document with 16 molejo
      springs, each carrying its full `$t` expression.

## 4. Exact path

- [x] 4.1 Red: `MolejoNode.exact` is `True`; `shape()` at a bound
      snapshot returns a closed OCCT solid whose volume matches the
      mesh volume within molejo's fixture tolerance; an exact assertion
      between a spring instant and a rigid exact part decides exactly.
- [x] 4.2 Implement `shape()` over `molejo.brep`, surfacing molejo's
      declared approximation tolerance.

## 5. Document schema (producer)

- [x] 5.1 Red: serializing a tree containing a flexible leaf produces a
      `flexible` node (`tech`, embedded `spec`, `params` expression
      strings), declares `version: 3`, and lists every qualified id
      referenced by `params` in the `drivers` table; a keyframed/
      snapshot-bound tree still serializes expressions, not constants;
      a tree with no flexible leaf serializes byte-identical version-2
      output; serializing with an unbound flexible port fails naming
      the node and port.
- [x] 5.2 Implement serializer and export support (inline spec, no
      `models/` entry, piece inventory unaffected); mirror the schema in
      the widget's `types.ts`.

## 6. Widget (consumer)

- [x] 6.1 Red (vitest): the loader accepts version 2 and 3, renders a
      flexible node's geometry at driver defaults, refuses a `flexible`
      node with an unknown `tech` naming it, and refuses a version the
      package does not declare.
  - Red: 12 failures across `document.test.ts` (5 new) and the new
      `flexible.test.ts` (10). The version gate had no prior
      counterpart at all -- `assertRenderable` did not read
      `document.version`, so a schema this build cannot read was
      rendered as far as it happened to parse. The delta's "accept 2
      and 3" is recorded as an accepted SET, `[1, 2, 3]`, and anything
      else is refused naming the version and the ones rendered.
  - `params` is held to the drivers table exactly as an operation
      expression is: an id the table does not declare is refused. The
      producer already guarantees it (section 5.1); this is what makes
      a broken producer loud about a wrong SHAPE as it already is about
      a wrong pose.
- [x] 6.2 Red (vitest): driving a driver named in a `params` expression
      re-evaluates that node's geometry into the same buffers (no
      reallocation, unchanged vertex count); driving an unrelated driver
      does not re-evaluate it; `$t` in a `params` expression animates.
  - The gating tests watch the REAL molejo through a spy, so the
      numbers are molejo's and only the call count is under test.
      Object identity is asserted on the `THREE.BufferAttribute` and on
      its backing `Float32Array`, not merely on the count.
- [x] 6.3 Implement: bundle molejo, evaluate `params` in the existing
      scope, per-node reused buffers, change-set gating by free-variable
      union; raise `solidNodeViewerApi` to 5 and add molejo to the
      license banner.
  - New `src/flexible.ts` (`FlexibleShape`) and `src/molejo.d.ts`;
      `tree.ts` mounts a flexible node's mesh from it, gates its
      geometry on the `params` free-variable union through the shared
      `touchedBy` helper the operations gate now also uses, and
      reconciles it (spec unchanged ⇒ expressions rebound, buffers
      kept); `viewer.ts` grew the version, `tech` and `params` gates.
  - molejo's buffer contract, read from `js/src/evaluate.js`: the
      first call allocates `{positions: Float32Array(V*3), index:
      Uint32Array(T*3), vertexCount, triangleCount}` and writes the
      index; a later call handed that object refills `positions` in
      place, never touches `index`, and returns the same object. It
      emits no normals, so the mesh is shaded FLAT -- which is also the
      look an STL already has, since STLLoader delivers non-indexed
      geometry whose computed normals are per-face. Colour inheritance,
      the operations matrix and disposal are the ordinary node paths.
  - `solidNodeViewerApi` 4 → 5 (red: `version.test.ts`; the Python
      reader `tests/test_viewer_bundle.py` moved with it). molejo added
      to `package.json` dependencies and to the `build.mjs` banner
      (Apache-2.0, copyright per molejo's NOTICE). `dist/` was NOT
      rebuilt: it is a symlink into the pilot's primary checkout, so
      the shipped bundle still declares 4 until section 7.
  - `npx tsc --noEmit`: clean. `npx vitest run`: 11 files, 165 tests
      passed (145 baseline + 15 flexible + 5 flexible parity).
- [x] 6.4 Extend the producer-generated parity fixture with a spring
      binding case (expression → molejo value, Python vs client) and run
      it against the shipped evaluator module.
  - The generator gained a `flexible` section built from
      `tests/flexible_project/spring.py`: the spec and the symbolic
      `params` expression from one serialization, and four numeric
      bindings (lift 0, 3.75, 6, 12 mm) each carrying the value the
      producer bound and molejo-python's evaluation at it -- 7 sentinel
      vertices spread over the array plus the bounding box. Counts and
      sentinel indices are stored ONCE, as molejo's own fixtures store
      them: the claim is that they never follow a parameter, and the
      format should not be able to express its violation.
  - Tolerances are declared per side: 1e-9 for the binding (float64
      both sides) and molejo's own 1e-6 JavaScript coordinate budget
      for the geometry, compared by molejo's formula
      `|actual - expected| <= tol * (1 + |expected|)`.
  - The case runs through `FlexibleShape` -- the shipped module -- so
      the expression parse, the binding and the buffer reuse are all
      the mounted path. Proven non-vacuous: perturbing the fixture by
      1 mm in a bound value and by 1 mm in one sentinel coordinate
      fails exactly the two tests that own those claims.
  - BLOCKER FOUND AND CLEARED: the generator had been unrunnable since
      commit 316f50e ("read a declared driver as an attribute"), which
      removed the `state` mapping without migrating
      `spike/expressions/machine_model.py`. The one-line migration
      (`self.state['motor']` → `self.motor`) is that commit's own rule
      applied. Verified value-neutral: regenerating leaves
      `generated_by`, `corpus`, `drivers`, `cases` and `conversions`
      byte-identical and only adds `flexible`; two consecutive runs are
      byte-identical.
- [x] 6.5 Live headless-browser proof (as in stage 3c): a spring
      document served to a real browser animates its geometry when a
      driver moves, against a fresh temp bundle.
  - Harness under `/tmp/flexible-6.5/`, where the stage 3c one lives
      and for the same reason (D11 of that change): the widget's
      `node_modules` and `dist` are symlinks into the pilot's primary
      checkout, so the bench builds a fresh bundle to /tmp and never
      writes `dist/` or runs npm. `build.mjs` esbuilds an stdin entry
      that re-exports the SHIPPED `src/widget.ts` and adds one
      observation hook (a record of the scenes the viewer builds), so
      the drive reads the spring's own `BufferGeometry` rather than
      inferring it from pixels; `export_spring.py` exports the fixture
      engine with `widget=False` and `SOLID_BUILD_DIR` under /tmp;
      `drive.py` serves it on an ephemeral port, drives headless
      Chromium through the shipped handle API, and exits non-zero on
      any failed check.
  - 16/16 checks passed, zero console or page errors. Mounted at API
      5 from a `version: 3` manifest declaring `valvetrain.lift`; the
      spring at rest holds 3858 vertices and stands 50.749 mm (the
      inscribed 16-gon profile just under the analytic 50.8);
      `handle.setDriver('valvetrain.lift', 12)` compresses it to
      38.776 mm with the position digest changed, the vertex count
      (3858), the index (23136) and the BACKING Float32Array all
      unchanged -- the no-reallocation claim observed on the live
      object -- and the canvas hash moving 55f2d054a7b0 → 0e5fa057fa17;
      `setTime(0.5)` moves no vertex, since no `params` expression of
      this spring names `$t`. Screenshot at
      `/tmp/flexible-6.5/driven.png`.

## 7. Packaging (gated on molejo publication — pilot decision)

- [ ] 7.1 With molejo published: a clean-venv install of solid-node
      resolves `molejo[brep]`; `npm ci && npm run build` in the widget
      resolves the npm package; packaging builds carry the bundled
      evaluator. Until publication, this section blocks and says so
      rather than being faked with local paths in committed metadata.

## 8. Docs, ADR, sync

- [x] 8.1 Extract the ADR (non-rigid leaf, port-fed parameters, spec-in-
      document, snapshot artifacts, version rule); pointers from
      ADR-003/ADR-008 consequences; update `docs/architecture.md`.
  - `docs/adrs/NODE/ADR-057-the-flexible-leaf-and-spec-carried-geometry.md`
      — **ADR-057: The flexible leaf, whose geometry travels as a spec**,
      Accepted, 2026-08-28, change `flexible-leaf-node`. Eight decisions
      with their reasoning: the third rigidity case (the non-rigid leaf,
      composing with ADR-003/039 rather than relaxing them); port-fed
      parameters rather than constructor kwargs (ADR-026 identity, the
      ADR-056 guardrail extended from pose to shape, structural knobs
      staying constructor args); `render()` returning the backend object
      (with the sheet adapter's `profile()` weighed and rejected — that
      base derives TWO products from one source); per-binding snapshot
      artifacts (`<basepath>-<binding_hash>.stl`, mtime deciding source
      currency within one binding, the sweep reading `snapshot_file` off
      the assembled tree because the symbolic document cannot name it,
      and the recorded nuance that a binding-only change republishes no
      document so one superseded snapshot survives); exact geometry
      computed on demand and never persisted (the `.brep` requirement is
      rigid∧exact, the composition path fuses returned shapes, the sweep
      spares every `.brep` by extension so per-binding ones would
      accumulate forever, and `(path, mtime)` keying is currency for a
      source not a binding — an in-memory `binding_hash` memo instead,
      with `shape_tolerance` surfacing molejo's 1e-6 / 0.0); the document
      (`flexible` as the third node shape read off `node.flexible` like
      `node.rigid`, `type` staying `LeafNode`, version 3 iff flexible
      content, `params` carrying the operation-expression verbatim
      guarantee structurally); the widget (bundled evaluator, buffers
      allocated by molejo's first call and refilled in place, ONE
      `touchedBy` rule over two dependency sets, flat shading chosen
      against `computeVertexNormals`, `[1, 2, 3]` accepted with loud
      refusal filling a gap where no version check existed, both
      refusals in the prepare phase); and the pilot-gated dependency
      entries, including the live `package.json` 5 / stale `dist/` 4
      drift the rebuild resolves.
  - Dated forward pointers added in the house amendment style:
      ADR-003 "Amendment: The Non-Rigid Leaf (2026-08-28)" and ADR-008
      "Amendment: Morphing Leaf Geometry, Without Time (2026-08-28)",
      each naming ADR-057 and stating that the deferral's own concerns
      are answered rather than the restriction weakened.
  - `docs/architecture.md` rewritten as reference prose in the affected
      sections rather than appended to: the node-model rigidity
      taxonomy now has three cases and gains a flexible-leaf paragraph;
      the identity paragraph names `binding_hash` as a fourth key beside
      — never inside — `uniq_id`; the build pipeline carries the
      per-binding skip guard, the no-`.brep` reasoning and the
      tree-driven sweep; the export section gains the schema-version-3
      paragraph and the widget's per-frame geometry paragraph, and its
      API version reads 5; two load-bearing invariants and the subsystem
      map are updated. The "Known gaps and tensions" list never carried
      a FlexibleNode entry, so nothing was removed there.
- [x] 8.2 Update `docs/leaf-nodes.rst`, `docs/animation.rst`,
      `docs/status-and-roadmap.rst` (roadmap item 3 done), and the ADR
      index.
  - `docs/leaf-nodes.rst`: a `MolejoNode` section at the depth of the
      sheet and STL sections — why a flexible part exists, the shape
      with `P.height` left open, ports as the whole parameter surface
      (both-directions name check, loud unbound port, why a constructor
      value would mint a part per frame), what the viewer and the
      OpenSCAD snapshot camera each do, exactness with
      `shape_tolerance` stated honestly, what it is not (fusible, a
      printed piece, time-reading), and the caveat that molejo must be
      `pip install -e /path/to/molejo[brep]`'d until publication. Listed
      in the leaf-kind roll-call at the top.
  - `docs/animation.rst`: "Animating a shape, not just a placement",
      after the non-linear-kinematics section — the driver → port →
      shape chain in the page's existing voice, showing a `connect()`
      and a `rotate()` side by side as the same kind of unevaluated
      statement carried into the viewer.
  - `docs/status-and-roadmap.rst`: roadmap item 3 removed from the list
      and its delivery described in a prose paragraph above the version
      paragraphs, which is how the previously-delivered item (animation
      scrubbing, commit b50bbf2) was treated. Marked honestly as
      unreleased, and honest that the delivery differs from the roadmap
      wording: no keyframes entered the leaf, because it reads no time.
  - ADR index (`docs/adrs/README.md`): ADR-057 added in chronological
      order as **Accepted**; ADR-003's and ADR-008's status lines note
      the new pointer.
- [x] 8.3 Full framework suite green; v8-engine 33/33 unchanged; record
      evidence. Consumer-side validation (v8-engine valve spring,
      Metamaquina2 belt) is project work consuming this change and is
      recorded in molejo's `define-swept-shape-spec` section 8, not
      here.
  - Framework suite, from the worktree root:
      `PYTHONPATH="$PWD" <workspace venv>/bin/python -m pytest -q` —
      **982 passed, 44 subtests passed, 0 failed** in 276.88s, matching
      the batch-A–C baseline exactly.
  - Widget, from `solid_node/viewers/widget`: `npx vitest run` —
      **11 files, 165 tests passed**; `npx tsc --noEmit` — **clean,
      exit 0**. `dist/` was NOT rebuilt (it is a symlink into the
      pilot's primary checkout), so the shipped bundle still declares
      API 4 until section 7.
  - v8-engine caller validation, the way prior cycles ran it (`solid
      test`, never plain pytest), from `projects/v8-engine` with
      `PYTHONPATH` at this worktree:
      `PYTHONPATH=<worktree> <workspace venv>/bin/python -c "from
      solid_node.cli import manage; manage()" test
      v8_engine/v8_engine.py` — **Ran 33 tests in 216.24 seconds: 33
      passed, 0 failed**, exit 0. The project's working tree is
      unchanged: the same two untracked files (`screenshot.png`, an
      emacs autosave) before and after, and its artifacts land in its
      gitignored `_build/`.
  - Note on the submodule: `docs/examples/v8-engine` is a git submodule
      and is UNINITIALIZED in this worktree (`git submodule status`
      reports `-d02ef4f4…`). It was not initialized, because it is not
      what the recorded "v8-engine 33/33" evidence refers to — every
      archived change ran the caller validation against the project
      repository at `projects/v8-engine`. The submodule is the docs
      example export used by CI and Read the Docs, not a test suite.
  - Docs build, the CI command minus its `-W` and its submodule
      prerequisite: `PYTHONPATH="$PWD" <venv>/bin/python -m sphinx -b
      html docs <tmp>` — **build succeeded, 5 warnings**, none from any
      file this batch edited. All five are pre-existing and
      environmental: four autodoc import failures from a scipy/numpy
      mismatch in the workspace venv, and one `examples.rst` error for
      the missing v8-engine export, which is exactly the uninitialized
      submodule above. CI runs this with `-W` after checking out
      submodules and generating that export.

## Deviations and judgment calls

- **The design's document illustration was wrong about `type`.**
  `design.md` sketched `"type": "ValveSpring"`, while the ratified
  `export` delta requires a manifest tree with "the same observable
  schema" as `viewer.json`. The normative text governed and the
  implementation follows it: `type` publishes the framework node KIND,
  `LeafNode`, exactly as the rigid CadQuery sibling beside it does.
  Recorded in ADR-057 rather than silently reconciled.
- **`docs/status-and-roadmap.rst` had no established marker for a
  delivered-but-unreleased item.** The one precedent (commit b50bbf2)
  deletes the bullet and describes the delivery in a version paragraph.
  With no release to attribute this to, the bullet is deleted and the
  delivery described in a paragraph that says plainly it is not yet
  released — extending the existing shape rather than inventing a
  status marker.
- **Nothing in section 7 was touched**: no `molejo` entry was added to
  `pyproject.toml`, no `dist/` rebuild, no publication. The widget
  `package.json` entry and the `build.mjs` banner were already added in
  batch C and are left as they stand.

## Consumer validation (2026-08-29, after batch D)

The pilot directed both validation projects onto `molejo` branches,
closing the consumer-side cases this change deferred to molejo's
`define-swept-shape-spec` section 8:

- **v8-engine** (`projects/v8-engine`, branch `molejo`, `8046064` +
  `ef0b046`): 16 valve springs as `MolejoNode` leaves at `ValveMotion`,
  heights driven by the released cam kinematics through `$t`. Suite 33 →
  36 green. The exact-shape headline passes: at full lift, all 16
  springs assert non-intersection against valve, retainer and head on
  OCCT solids, with AABBs proven overlapping first so the broad phase
  cannot answer. The pairwise sweep also caught a real error in
  increment 7's own figures (a solid seat pad the prose said was
  annular: real clear span 8.8 mm, not 9.8), superseded by the
  project's increment 9 without touching the released spec.
- **Metamaquina2** (`projects/Metamaquina2`, branch `molejo`,
  `480ed1f`): real GT2 belts on X (404 teeth) and Y (477 teeth), wrap
  circles from the design's own numbers, anchors fed by the same
  qualified driver expressions that move the carriages; document
  version 3 with two `flexible` nodes. Suite 12 → 21 green. The belt
  at its true riding radius exposed a 1 mm height error the old
  placeholder ring had hidden.

**Defect found by the belts, fixed here red-first:** the
intersection assertions' mesh path (`_fast_geometry`) read
`node.stl_file` for any node carrying the attribute, so a flexible
leaf paired with a faceted node raised `FileNotFoundError` — or,
when a rigid predecessor's artifact was still on disk, silently
answered from the WRONG geometry. Three red tests
(`MolejoMeshPathPairTest`: missing artifact, stale artifact answering,
per-binding caching) then `_flexible_manifold` in `solid_node/test.py`:
a Manifold built from `base_mesh()` cached per
`(uniq_id, binding_hash)`, routed before the `stl_file` read. Exact
pairs are checked first and unaffected; only previously-crashing mixed
pairs change behaviour. Framework suite after the fix: **985 passed,
0 failed** (982 + 3). Metamaquina2 re-run against the fixed bench:
21/21.

**Residual findings recorded for the pilot** (none blocks this change):

- ~~A `$t`-animated project cannot `solid build` a flexible leaf~~ —
  **resolved by the pilot on 2026-08-29 and folded into this cycle.**
  The symbolic SCAD assembly needed one numeric instant and `$t` has no
  `set_state` binding, so v8-engine's valve spring aborted the build at
  `assemble()` — which also blocked `viewer.json`, the path a flexible
  part is actually delivered through. The pilot first chose `$t = 0`,
  then reconsidered on the ground that the spring is not meant to be
  built at all: the camera now emits no geometry for a time-fed leaf
  instead of inventing an instant. `$t = 0` was also the costlier
  option — no evaluator for `OpenSCADConstant` expressions exists
  (`math.py:14-16`), so it would have meant writing one or re-rendering
  the parent assembly at time 0 mid-assembly. Specs, design and tasks
  3.6-3.7 revised; commit 1 amended. Tests and `solid snapshot --time`
  were never affected.
- The api-4/5 drift ADR-057 already records (`package.json` declares 5,
  the symlinked `dist/` bundle declared 4) had a second consequence the
  ADR does not name: because `dist` symlinked into the PRIMARY checkout,
  every test touching the built bundle -- the widget e2e suite -- was
  exercising main's api-4 bundle rather than this change's. That hid a
  literal `assertEqual(result['apiVersion'], 4)` in
  `tests/test_widget_e2e.py`, which passed against the stale bundle and
  failed the moment the bench was rebuilt. Resolved here: dist
  de-symlinked, widget rebuilt in the bench, and the test now reads
  `api_version()` the way `version.test.ts` already reads package.json.
  A literal version inside the test whose subject IS the declared
  version is a rot trap. Worth checking whether other benches carry the
  same symlink.

- **Merge blocker for framework primary, recorded 2026-08-29.**
  `solid_node/node/__init__.py:21` imports `MolejoNode` unconditionally
  and `node/adapters/molejo.py:28` does `from molejo.brep import
  evaluate` at module scope, so `import solid_node.node` raises
  ImportError wherever molejo is absent. molejo is on neither PyPI nor
  npm (`pip index versions molejo` and `npm view molejo` both fail);
  the pilot has pushed LibreSolid/molejo publicly but not released it.
  The widget's committed `"molejo": "^0.0.1"` therefore 404s on a clean
  `npm ci`. ADR-057's dependency-gate section also states that committed
  `pyproject.toml` entries name published forms -- pyproject names
  molejo nowhere, so no Python dependency is declared at all. Merging as
  ratified would leave framework primary unimportable without a source
  checkout of molejo, against the v0.4 usefulness commitment. Returned
  to the pilot rather than resolved here: making the import optional
  would contradict the ratified "stated, not faked" decision.

- A consumer that predates the `flexible` node shape cannot refuse what
  it cannot evaluate. `tech` exists so a consumer can decline a spec and
  name the evaluator, but a bundle built before this change has no
  branch for `flexible` at all and simply renders nothing — which is how
  Metamaquina2's belts went missing while its document was correct. The
  document's version rule catches a consumer reading a NEWER version;
  nothing catches a stale bundle served beside a current document.
  Recorded for the pilot as a consumer-contract gap, not fixed here.

- molejo API findings, candidates for molejo issues: consumers
  anchoring a belt must re-derive the external-tangent stations
  (a public `wrap_stations()` would remove the duplication);
  `tessellation.path` is spent per element, so the longest span sets
  the count and short arcs over-sample; the helix-axis offset is now
  stated in `docs/leaf-nodes.rst` but molejo's own authoring docs could
  say it earlier.
- Pairwise B-rep assertions over 16 springs cost the v8-engine suite
  ~8x (211 s → 1627 s) — a project-level cadence choice, recorded, not
  a framework defect.
