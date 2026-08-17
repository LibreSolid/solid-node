=======
History
=======

Unreleased
----------

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
