=======
History
=======

0.6.0 (2026-08-30)
------------------

The release that makes a model a *machine*. Until now a solid-node model
moved as a function of one looping ``$t``; it can now declare named inputs,
be stepped deterministically in Python, and be driven by hand in the viewer.
Alongside that, three new kinds of part — laser-cut sheets, imported STL
meshes, and flexible parts whose shape is a function of machine state — and
an assembly assertion that knows about gravity.

Breaking changes
~~~~~~~~~~~~~~~~

* **Reinstall required.** ``cadquery`` moves from 2.5 to 2.7 and
  ``build123d`` 0.10 joins it, so the shared ``cadquery-ocp`` binding moves
  from 7.7 to 7.8. Both libraries bind the same ``OCP`` module and the
  previous pin admitted no current build123d. Because ``cadquery-ocp`` is a
  large binary wheel and the two versions cannot coexist, upgrade by
  reinstalling the environment rather than in place. No project source
  changes.
* The published document schema moves from version 1 to version 2: every
  document now carries a ``drivers`` table, and operation expressions may
  name qualified driver ids as well as ``$t``. A document containing a
  flexible part declares version 3 instead — the producer emits the lowest
  version its content needs, so a model with no flexible part is the version
  2 it would otherwise have been. The bundled viewer renders versions 1, 2
  and 3, so documents published by earlier releases keep working; what does
  not work is the other direction. A 0.5.x viewer has no version gate at
  all, so pointed at a 0.6 document it will silently render part of a
  machine it cannot evaluate rather than refusing. Hosts pinning their own
  copy of the bundle must upgrade it with the framework. The declared viewer
  API version is 5, and this release's viewer refuses an unreadable schema
  version by name.
* ``export_node`` now leaves the node in symbolic time rather than in
  whatever pose the caller left it. ``solid export`` and the build and
  snapshot paths produce byte-identical output to before, so only a host
  calling ``export_node`` itself and then reusing the node sees the
  difference; such a host re-applies ``set_keyframe`` if it wants a numeric
  pose. See below for what this fixes.

New features
~~~~~~~~~~~~

* **Named drivers.** An assembly declares its inputs as class attributes —
  ``x = Driver(default=0, range=(0, 200), unit='mm')`` — and reads them back
  as attributes: ``self.x``, exactly as a port is read. A driver's value
  belongs to a bound snapshot, so assigning to one raises and names
  ``set_state``, reading an unbound one raises and names the driver, and
  declaring a driver whose name would shadow a node member (``render``,
  ``color``, ``time``, …) fails at class-definition time. ``time`` is now one
  driver among several rather than the only one.
* **Instance-qualified driver ids.** A printer whose X and Y axes are two
  instances of one ``Axis`` class addresses them separately:
  ``set_state(**{'x_axis.motor': 12.5})``. The qualified dotted id is one
  string by construction — the same id appears in the document's driver
  table, the simulation's state bank, and an instruction's targets — and a
  tree that cannot be qualified fails loudly instead of silently sharing one
  value between siblings.
* **Domain-typed ports.** ``Port`` with ``RotationalPort``,
  ``TranslationalPort`` and ``SignalPort``: unit-tagged value slots a node
  re-binds on every render, with declared unit conversion and a causal
  ``connect()`` for wiring one node's output to another's input.
* **A stepped simulation layer**, ``solid_node.simulation``. ``Driver``
  declarations and ``RampProgram``; ``Instruction``, naming driver targets in
  design units plus a duration; and ``Sim``, a fixed-``dt`` loop whose
  instants are integer tick counts, with events at ticks, deferred ``at(t)``
  actions, an ``every(period, fn)`` cadence, per-tick snapshot binding and
  trajectory recording. Integer-typed drivers ramp integer-exactly
  (``start + delta*k//n``) and land on target. Under a simulation
  ``self.time`` reads the stepped clock in seconds; the normalized 0..1
  ``$t`` animation path outside simulations is unchanged. ``ScenarioTest``
  runs scenarios under plain pytest and under ``solid test`` alike.
* **A driveable viewer.** The widget evaluates driver expressions, not just
  ``$t``, and the mount handle gains ``drivers()``, ``instructions()``,
  ``driver(id)``, ``setDriver(id, value)``, ``onDriverChange(fn)`` and
  ``trigger(name)`` returning ``{done, cancel()}``. A trigger runs the
  instruction's ramp client-side over its declared duration, landing exactly
  on target, with a later trigger replacing an active ramp. Which operations
  re-evaluate is decided by the free variables read off the parsed
  expression, so moving one driver does not recompute the rest of the tree.
  Cross-runtime agreement between the Python producer and the JavaScript
  evaluator is now pinned by tests rather than merely measured.
* **On-screen driver controls.** The widget shows one button per instruction
  and one slider with a numeric readout per driver declared at the focused
  assembly layer, labelled relative to that layer and shown in design units.
  A breadcrumb moves focus down into subassemblies that declare controls and
  back up. Scoping is strict: the root of a machine that declares everything
  on its children shows no controls, which is pressure to declare
  machine-level instructions on the machine. A host building its own UI on
  the programmatic API suppresses the chrome with ``driverControls: 'none'``.
  A document with no drivers looks exactly as it did before.
* ``Build123dNode``, a fifth leaf adapter backed by `build123d
  <https://build123d.readthedocs.io/>`_. Like ``CadQueryNode`` it is a front
  end over OCCT, so it produces exact geometry, persists a ``.brep`` beside
  its STL, and needs no OpenSCAD binary. ``render()`` may return a ``Part``,
  ``Solid`` or ``Compound``, or a ``BuildPart`` builder whose finished
  ``.part`` is taken; a sketch or curve is rejected naming the node, since a
  leaf is one part. Exact composition does not require one backend: a fusion
  may mix ``CadQueryNode`` and ``Build123dNode`` children and still fuse
  exactly into a single solid.
* **Sheet parts.** ``SheetLeafNode``, with ``Build123dSheetNode`` as its
  first concrete backend, authors a laser-cut part as a 2D ``profile()`` plus
  a declared ``thickness``. The base owns ``render()`` — the extrusion of
  that profile — so the solid you preview and the outline a cutter consumes
  cannot drift apart. Each sheet leaf writes a nominal, kerf-free ``.dxf``
  beside its STL and BREP, under the same freshness guard, with arcs
  preserved. A profile that is not exactly one planar face, one outer
  boundary with holes strictly inside, is rejected naming the node. Kerf
  compensation, SVG import, engraving, nesting and a production-export
  command are deliberately left out; the persisted exact profile keeps them
  all additive.
* **Imported meshes.** ``StlNode`` wraps a committed ``.stl`` declared by
  ``stl_source``, so a design published only as a mesh can be assembled under
  source control and a new part can be designed to fit it. A non-watertight
  mesh fails at build naming the file and the defect, with
  ``require_watertight = False`` to admit one knowingly. A multi-body file is
  a part pack: ``body`` selects one component by index, and leaving it unset
  reports the count with a per-body inventory of centroid, bounds and volume.
  An optional ``adjust(self, mesh)`` hook corrects the mesh in code —
  scale, recentre, any trimesh operation — instead of via constructor knobs.
  ``StlNode`` participates in ``FusionNode``, which makes the enclosing
  fusion faceted and routes it through OpenSCAD and CGAL; that cost is the
  documented price of designing a part that fits a downloaded one.
* **Flexible parts.** ``FlexibleNode``, the non-rigid leaf that ADR-003 and
  ADR-008 deferred and ``LeafNode.time`` has been naming as roadmap work,
  with ``MolejoNode`` as its first adapter. A valve spring, timing belt, cable
  loom or filament path is a part whose *shape* is a function of machine
  state, not only of its placement: its geometry is a pure function of its
  declared ports' bound values. It never caches a rigid artifact, because its
  representation in the document is a `molejo <https://molejo.readthedocs.io>`_
  shape spec plus one expression per parameter rather than a mesh. The widget
  evaluates that spec into reused buffers, and only on frames where a free
  variable of those expressions actually changed. Exact geometry comes from
  molejo's OCCT evaluator, and the OpenSCAD path gets per-binding snapshot
  meshes.
* **Assemblies are checked against gravity.** ``assertAssemblySupported(node,
  gravity=(0, 0, -1), max_drop=1.0, ground=None, supports=None,
  stability_margin=0.0)`` selects the same topmost rigid solids
  ``assertNoSolidInterference`` compares and proves two things about them.
  First, support reachability: displaced by ``max_drop`` along gravity, every
  solid lands on another with positive volume, and every solid reaches a
  grounded seed through those "rests on" edges — so a part left floating in
  space fails. Second, static equilibrium: a distribution of unilateral
  push-only contact forces over the detected contacts must balance every
  solid's gravity wrench, force *and* torque, for the whole assembly at once,
  decided by one deterministic linear program. A bar supported at one end
  only fails; a tall solid toppling off a small footprint fails. On failure
  the assertion names which solids could not be balanced and whether force or
  torque balance failed. ``ground`` anchors named solids with bolted
  semantics, ``supports`` declares press-fit or glued holds the geometry
  cannot prove, and ``stability_margin`` shrinks each contact patch so
  knife-edge balances can be rejected. Friction, adhesion and dynamics remain
  out of scope, and the docstring says so.

Correctness and reliability
~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Artifact freshness no longer goes through floating-point mtimes. Source
  times are read as integer nanoseconds and artifacts stamped with them, so
  the value the framework writes is the value it read. The float detour lost
  a sub-quantum remainder that the filesystem then truncated, leaving the
  artifact *below* the stamp it was given: on a millisecond-resolution
  filesystem caching stopped working altogether and every build rebuilt
  everything. Measured natively, 50 of 100 whole-millisecond stamps lost a
  millisecond through the round trip; a 25-generation probe under Pyodide's
  MEMFS failed freshness 13 times, always by exactly one millisecond, against
  0 of 25 on ext4. Freshness stays *exact equality* — no tolerance window is
  introduced, because the failure being fixed is a spurious rebuild and a
  tolerance would trade it for a stale artifact reported as current.
* ``manifold3d`` became a conditional dependency of the faceted mesh path,
  resolved at the operation that needs it with one error naming what needed
  it and why, on the model ADR-046 already established for the OpenSCAD
  binary. It was imported at module scope in ``solid_node.test``, so a
  project whose model is entirely exact — every comparison decided by the
  OCCT kernel, never reading a mesh — could not run *any* geometric
  assertion without the compiled wheel, and on a platform with no wheel
  (WebAssembly) lost ``assertNotIntersecting``, ``assertJoined`` and
  ``assertNoDisconnectedSolids`` too.
* ``clear_keyframe()`` joins ``set_keyframe(time)`` as its explicit inverse,
  returning an assembly subtree to symbolic ``$t``. ``set_keyframe`` was a
  one-way door: once ``time`` was a float, ``76.0 * self.time - 38.0``
  evaluated inside user ``render()`` code and the symbolic form no longer
  existed anywhere for the serializer to recover.

Packaging, documentation, and maintenance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* solid-node now depends on `molejo <https://pypi.org/project/molejo/>`_ with
  its ``brep`` extra, and the bundled viewer on the ``molejo`` npm package.
  ``MolejoNode`` reaches for molejo's OCCT evaluator at import and
  ``solid_node.node`` imports the adapter, so ``brep`` is required rather
  than optional. Both are pinned to molejo's minor, because a molejo minor
  carries the shape-spec version it implements and this framework's documents
  name that version.
* Internal: the exact-adapter contract (``exact``, ``shape()``,
  ``as_scad()``) moved to a shared ``ExactLeafNode`` base rather than being
  duplicated in ``CadQueryNode`` and ``Build123dNode``. No project-visible
  effect: both adapters keep their name, import path and behaviour.
* The driver readout in the viewer holds still under a drag: fixed decimal
  places, a fixed-width right-aligned number column with room reserved for a
  minus sign, tabular figures, and the unit in its own segment. Previously
  the string was written with trailing zeros stripped, so the number and
  everything laid out beside it jumped horizontally while the maker was
  trying to land a value.

0.5.1 (2026-08-18)
------------------

Packaging, documentation, and maintenance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* The project's ``Homepage`` metadata pointed at
  ``github.com/lfagundes/solid_node``, which returns 404. It now names the
  repository, ``github.com/LibreSolid/solid-node``. The 0.5.0 page on PyPI
  keeps the dead link, since release metadata is immutable once published.
* The Read the Docs build ran the V8 example export with the ``root``
  argument that 0.5.0 removed, so every documentation build since has failed
  with ``Error loading node: No module named 'root'``. The export now
  resolves the model from the example's ``[tool.solid-node]`` manifest, as
  the GitHub Actions workflow already did.
* Added ``context7.json`` so Context7 indexes the repository with the npm
  viewer trees, OpenSpec records, tests, and generated exports excluded.

0.5.0 (2026-08-17)
------------------

Breaking changes
~~~~~~~~~~~~~~~~

* A project now declares its model in a ``[tool.solid-node]`` table of its
  ``pyproject.toml``, and the framework discovers the project root from the
  nearest ancestor ``pyproject.toml`` carrying that table instead of assuming
  the current working directory. Commands consequently give the same answer
  from a subdirectory as from the root, where ``source_closure`` used to
  truncate silently and report stale artifacts as current.
* Node-scoped commands take an optional *reference* — a qualifier
  (``package.module:Class``), a Python file path, or a path plus class — and
  fall back to the manifest's model when it is omitted. The fixed
  ``root/__init__.py`` entry point, the directory-to-``__init__.py``
  coercion, and the ``NODE`` marker are all removed: a caller that can name a
  class never needed the file to name it. ``solid new`` scaffolds the new
  layout and manifest.
* ``solid test`` now loads *every* ``TestCase`` in a companion file rather
  than the first. Existing single-node projects are unaffected, but a
  multi-node module needs work: a case beside one **fails the whole run
  before any test executes** unless it declares its node, which is a hard
  error rather than a test failure::

      from .valve import ValveMotion

      class ValveMotionTest(TestCase):
          node = ValveMotion

  Without it: ``Error: ValveMotionTest must declare node; candidates: Valve,
  ValveRetainer, BucketLifter, ValveMotion``. Migrating the V8-engine example
  took two lines in each of seven files. Expect cases that were silently not
  running to run for the first time, and to fail: one of them had been
  asserting a design that its own guard rejected, unnoticed.
* Geometric questions are answered exactly wherever both compared nodes are
  exact. Every ``CadQueryNode`` is exact, so verdicts change in both
  directions: real sub-facet interference the mesh path missed now fails, and
  nominally exact fits that failed only on facet phase now pass. Projects can
  retire their tessellation epsilons; ``volume_epsilon`` is ignored, with a
  warning, when every comparison in the call routed exact.
* A failed build now leaves a partially updated model in ``_build`` rather
  than the previous complete artifact set. The 0.4 guarantee that the last
  successful set survives a later failure is withdrawn (ADR-030 reversed by
  ADR-038); in exchange, every individual artifact is written whole or not at
  all, and a successful build sweeps artifacts its manifest no longer
  references.
* A fused solid's STL bytes change, because an all-exact fusion is now
  tessellated by OCCT rather than compiled through OpenSCAD and CGAL.
* ``assertNoPairwiseIntersections`` is deprecated in favour of
  ``assertNoSolidInterference``; it still works and now warns about its
  leaf-based quadratic behaviour. Removal is deferred to a later release.

New features
~~~~~~~~~~~~

* ``solid build [reference]`` runs the ordinary build pipeline once,
  publishes, and exits — no viewer, no watcher. An unresolvable model exits
  with status 66 (``MODEL_NOT_FOUND``).
* ``solid develop --no-web`` runs the watch-and-rebuild loop with no viewer,
  leaving ``SOLID_NODE_PORT`` free for a host that renders the published
  build directory itself, and ``--callback URL`` POSTs that URL after the
  initial build and every later successful rebuild. Callback delivery is best
  effort and never stops development.
* ``solid snapshot --renderer web`` renders through the packaged viewer in
  headless Chromium and captures a real alpha channel, for hosts that
  composite the image onto their own surface. Install with
  ``pip install "solid-node[web-snapshot]"`` and ``playwright install
  chromium``. The OpenSCAD renderer remains the default and the fast
  inspection path; the web renderer never silently falls back to it, and
  rejects by name the options a browser cannot honour.
* ``solid viewer`` reports the installed viewer bundle's path and declared
  API version, so another program can obtain a viewer from an installation.
* Nodes expose exact geometry: a read-only ``exact`` property, a ``shape()``
  accessor returning the node's own OCCT solid in its local frame, and a
  ``.brep`` artifact written beside the ``.stl`` for every exact rigid node.
  A ``FusionNode`` whose subtree is exact composes its children with an OCCT
  fuse instead of launching OpenSCAD.
* Published documents carry a ``pieces`` inventory: one entry per distinct
  *printed piece*, identified by a content fingerprint of its built STL, with
  display name, contributing source files, instance count, bounding extents,
  volume and watertightness. Every rigid node in the tree carries a ``piece``
  reference. Geometrically identical solids are one piece however the code
  was factored; mirrored parts stay distinct. Purely additive.
* New geometric contracts: ``assertNoDisconnectedSolids(node)`` proves each
  printed solid is one connected body, ``assertNoSolidInterference(node)``
  proves the assembled solids do not occupy the same material, and
  ``assertJoined(node1, node2, min_weld_volume=0.0)`` proves two features
  genuinely reach each other. ``solid new`` scaffolds ``test_solid_integrity``
  and ``test_assembly_integrity`` so every new project has both from the
  start.
* OpenSCAD is now a conditional dependency, required only by the paths that
  invoke it — Solid2/OpenSCAD leaves, faceted fusions, symbolic Solid2
  values, the OpenSCAD GUI viewer, and the OpenSCAD snapshot renderer. An
  all-exact CadQuery project builds, tests and publishes without it, and a
  path that does need it reports what needed it and why instead of raising a
  bare ``FileNotFoundError``. (``JScadNode`` carries the same problem with the
  ``jscad`` binary; that is left to a later release.)
* One reusable viewer package now serves every surface — static exports, the
  Sphinx directive and ``solid develop`` — replacing three separate copies of
  the renderer. ``mount()`` returns a handle (``dispose()``, ``view()``,
  ``reload()``, ``apiVersion``) with targeted updates, assembly metadata, and
  subtree focus and visibility controls. The declared viewer API version is
  4. The published bundle, its global, its auto-mount attribute and its query
  parameters are unchanged.
* The development viewer gains inherited colours, lights, a fitted camera and
  the shared animation controls, because it renders through that same
  package. Exported models with no explicit or inherited colour are rendered
  with the development viewer's normal-based material rather than appearing
  untextured.
* Every successful build publishes a complete viewer-readable snapshot,
  including the animation cadence (``fps`` and ``frames``), so a host can
  serve the model straight from the build directory with no source import.

Correctness and reliability
~~~~~~~~~~~~~~~~~~~~~~~~~~~

* A node now tracks the project modules its source imports, not just its own
  file (ADR-033). Editing a module that holds shared geometry but defines no
  node — the conventional ``kinematics.py`` — used to move no tracked mtime,
  so every artifact went on reporting up to date and ``solid develop`` never
  saw the edit; it now invalidates exactly the nodes that import it. Two
  consequences worth knowing: ``assemble()`` may call ``render()`` zero times
  rather than exactly once, so anything relying on a render side effect is
  affected; and a node whose geometry depends on something a static import
  walk cannot see — a data file read at runtime, a module reached through
  ``importlib``, an environment variable — can look current when it is not,
  where the old unconditional render hid it. An existing build directory
  rebuilds once as the corrected source set takes effect.
* Every process that renders artifacts for a project takes an advisory
  ``flock``, so exactly one build runs at a time per project and a build
  finishing late can no longer overwrite a newer model. A second builder
  queues rather than failing; one that finds the project already current, or
  its own source superseded while it waited, stands down. The lock covers the
  build only — ``solid develop`` releases it before waiting for the next
  edit, and ``solid test`` before running tests.
* A self-contained export now renders when served from anywhere but a server
  root. A document URL with no directory component resolves models beside the
  document rather than at the domain root, which is why the V8 engine example
  embedded in the published documentation returned 404 for every mesh.
* An explicit reference can name a node class defined in another project-local
  module, so a package facade no longer needs a meaningless local subclass.
* ``FusionNode`` rejects a non-rigid child instead of silently flipping itself
  non-rigid and producing no STL.
* The viewer no longer refetches geometry an artifact update has just
  fetched, and a failed targeted update leaves the previously rendered model
  on screen with the handle still usable.
* ``solid snapshot`` holds the project build lock while preparing its node,
  releases it before rendering, and defaults ``-o`` from the resolved node
  rather than ``snapshot.png``.

Performance
~~~~~~~~~~~

* The up-to-date check now runs *before* ``render()``, so caching finally
  pays: a no-op rebuild of a CadQuery-heavy project cost the same as building
  it from scratch (19.8 s either way) and now costs 3.2 s. ``CadQueryNode``
  and ``JScadNode`` no longer rewrite an artifact that is already current.
* The viewer updates in place instead of rebuilding the scene. A changed
  artifact is refetched alone and swapped into every node referencing it, and
  a document change reconciles the tree, fetching geometry only where
  ``(model path, mtime)`` genuinely moved — so an operations-only or
  colour-only edit costs no fetch at all. On a 113 MB, 55-STL assembly the
  old full reload re-parsed and re-uploaded everything to show a
  one-leaf difference.
* ``assertNoSolidInterference`` dropped its global batch-union volume
  certificate, whose cost scaled with total assembly triangle count whether or
  not anything was wrong. On a clean 125-solid, 1.02M-triangle assembly the
  certificate cost 273 ms against 2 ms for the sweep-and-prune plus exact
  narrow phase that actually finds and names the interference. The broad
  phase's conservatism is now proved differentially in the framework's own
  suite instead of being re-tested at every project's expense.
* The exact geometry path costs about 2× the mesh path on assertions
  (6.15 s via Manifold against 12.2 s via OCCT on the full V8 engine at one
  instant, identical verdicts), but its cached artifact is cheaper than the
  STL beside it: 4 ms write, 2 ms read, 165 KiB, against 112 ms, 9 ms and
  469 KiB.

Packaging, documentation, and maintenance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* The built viewer bundle now ships inside source distributions and wheels,
  so a fresh installation has a viewer: ``solid export`` can copy one and the
  Sphinx extension can complete a ``--no-widget`` export.
* New optional extra ``solid-node[web-snapshot]`` for the browser snapshot
  renderer, whose Chromium download stays separate.
* The development loop's per-node HTTP API under ``/node`` and the browser
  modules that consumed it are removed, along with the dependencies they
  carried (``three``, ``jokenizer``, ``re-resizable``, ``react-ace``,
  ``ace-builds``, ``react-router-dom``). No published document, URL or CLI
  surface changes.
* Projects scaffolded by ``solid new`` ignore ``__pycache__/`` and ``_build*``.
  An existing project gets ``_build*`` recorded in ``.git/info/exclude`` on
  its next build, leaving its tracked ``.gitignore`` untouched; because that
  file is per-clone, an older project may need the pattern added to
  ``.gitignore`` when cloned elsewhere.
* ``README.rst`` states OpenSCAD as conditional on the backends a project
  uses, documents working on solid-node itself, and the hosted documentation
  builds its embedded exports from source in CI. The obsolete Read the Docs
  configuration is removed.

0.4.0 (2026-07-20)
------------------

* Relicensed from AGPL-3.0 to Apache-2.0, with consent from all contributors
* CLI grammar flip: commands come first, ``solid <command> <node>`` (breaking change)
* New ``solid new`` command to scaffold a starting project structure
* Added static ``solid export`` manifests, STL exports, an embeddable viewer
  widget, and Sphinx embedding support
* Added symbolic degree-aware math and expanded kinematic-fit assertions
* Improved animation correctness, node identity, test-runner behavior, and
  developer reload resilience
* Improved mesh and assertion performance through caching, single-matrix world
  transforms, and AABB broad-phase culling
* Migrated packaging to ``pyproject.toml`` and expanded API and tutorial
  documentation

0.3.0 (2026-01-14)
------------------

* Snapshot CLI for headless PNG rendering (enables AI agent workflows)
* Lean architecture: removed broker, git, refactor modules (ADR-018)
* Full license attribution in CREDITS.md
* License headers on all source files

0.2.0 (2025-02-25)
------------------

* JScadNode adapter for JSCAD backend, plus further work on OpenScadNode
* API reference documentation building on Read the Docs

0.1.0 (2025-02-01)
------------------

* Stable multi-backend architecture (SolidPython2, CadQuery, OpenSCAD)
* Web-based 3D viewer with React/Three.js
* Development server with filesystem monitoring and hot-reload
* Test runner for CAD projects
* STL generation with background optimization

0.0.8 (2024-12-15)
------------------

* Pre-release with improved documentation
* Bug fixes and stability improvements

0.0.1 (2023-07-13)
------------------

* First release on PyPI, with basic structure:
  * Develop using SolidPython and CadQuery combined
  * Filesystem monitoring triggering transpilation to openscad and stl building
  * Background optimization
  * Spatial calculations with trimesh
