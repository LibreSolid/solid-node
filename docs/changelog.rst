
.. _changelog:

=========
Changelog
=========

v0.5.0
------

Released on 17/Aug/2026

**Breaking changes**

* A project declares its model in a ``[tool.solid-node]`` table of its
  ``pyproject.toml``. The project root is discovered from the nearest
  ancestor manifest instead of the current working directory, so commands
  behave identically from a subdirectory.
* Node-scoped commands take an optional reference — ``package.module:Class``,
  a file path, or a path plus class — defaulting to the manifest's model.
  The fixed ``root/__init__.py`` entry point, the directory argument, and the
  ``NODE`` marker are removed.
* ``solid test`` loads every ``TestCase`` in a companion file instead of the
  first. A case beside a multi-node module MUST declare ``node = <Class>``:
  an undeclared one aborts the whole run before any test executes, naming the
  candidates. Single-node modules are unaffected. Cases that were silently
  not running will run — and may fail — for the first time.
* Intersection and connectivity assertions answer exactly when both compared
  nodes are exact, so verdicts change in both directions: real sub-facet
  interference now fails, and nominally exact fits that failed on facet phase
  now pass. ``volume_epsilon`` is ignored, with a warning, on a fully exact
  call.
* A failed build leaves a partially updated model rather than the previous
  complete artifact set; in exchange each artifact is written whole or not at
  all, and a successful build sweeps artifacts its manifest dropped.
* An all-exact ``FusionNode``'s STL bytes change — it is tessellated by OCCT
  rather than compiled through OpenSCAD.
* ``assertNoPairwiseIntersections`` is deprecated in favour of
  ``assertNoSolidInterference`` and warns about its quadratic leaf sweep.

**New features**

* ``solid build [reference]`` builds and publishes once, then exits; an
  unresolvable model exits with status 66 (``MODEL_NOT_FOUND``).
* ``solid develop --no-web`` runs the watch-and-rebuild loop with no viewer,
  and ``--callback URL`` announces each successful publication.
* ``solid snapshot --renderer web`` renders through the packaged viewer in
  headless Chromium with a real alpha channel. Optional install:
  ``pip install "solid-node[web-snapshot]"`` plus ``playwright install
  chromium``. It never falls back to OpenSCAD silently.
* ``solid viewer`` reports the installed viewer bundle's path and API version.
* Exact geometry: a read-only ``exact`` property, ``shape()`` returning the
  node's OCCT solid in its local frame, and a cached ``.brep`` artifact beside
  each exact rigid node's ``.stl``. Exact fusions compose with an OCCT fuse.
* Published documents carry a ``pieces`` inventory keyed on a content
  fingerprint of each built STL, with display name, source files, instance
  count, bounding extents, volume and watertightness, plus a ``piece``
  reference on every rigid node. Additive; no existing field changes meaning.
* New assertions ``assertNoDisconnectedSolids``, ``assertNoSolidInterference``
  and ``assertJoined``. ``solid new`` scaffolds ``test_solid_integrity`` and
  ``test_assembly_integrity``.
* OpenSCAD is required only by the paths that invoke it; an all-exact
  CadQuery project builds, tests and publishes without it, and a path that
  needs it says so instead of raising ``FileNotFoundError``.
* One reusable viewer package serves exports, the Sphinx directive and
  ``solid develop``. ``mount()`` returns a handle with targeted updates,
  assembly metadata, and subtree focus and visibility. Declared viewer API
  version 4; the published bundle, global, auto-mount attribute and query
  parameters are unchanged.
* The development viewer gains inherited colours, lights, a fitted camera and
  the shared animation controls; uncoloured exported models render with the
  normal-based material.
* Every successful build publishes a viewer-readable snapshot including the
  animation cadence (``fps``, ``frames``), so a host can serve the model from
  the build directory with no source import.

**Correctness and reliability**

* A node tracks the project modules its source imports, not just its own file
  (ADR-033), so editing a shared geometry module invalidates the nodes that
  import it. Note that ``assemble()`` may now call ``render()`` zero times,
  and geometry depending on something a static import walk cannot see can look
  current when it is not.
* Concurrent builds of a project are serialized with an advisory ``flock``,
  so a late-finishing build cannot overwrite a newer model. ``solid develop``
  and ``solid test`` release the lock before waiting and before testing.
* Self-contained exports resolve models beside their document rather than at
  the server root, fixing embedded examples served under a subdirectory.
* An explicit reference may name a node class defined in another
  project-local module.
* ``FusionNode`` rejects a non-rigid child instead of silently becoming
  non-rigid and producing no STL.
* A failed targeted viewer update leaves the rendered model on screen and the
  handle usable; geometry just fetched is not refetched.
* ``solid snapshot`` holds the build lock only while preparing its node, and
  defaults ``-o`` from the resolved node.

**Performance**

* The up-to-date check runs before ``render()``: a no-op rebuild of a
  CadQuery-heavy project fell from 19.8 s to 3.2 s.
* The viewer updates in place instead of rebuilding the scene, refetching
  geometry only where ``(model path, mtime)`` moved — an operations-only or
  colour-only edit costs no fetch.
* ``assertNoSolidInterference`` dropped its global volume certificate: 273 ms
  against 2 ms for the spatial path on a 125-solid, 1.02M-triangle assembly.
* Exact ``.brep`` artifacts cache far more cheaply than the STLs beside them
  (4 ms write, 2 ms read, 165 KiB against 112 ms, 9 ms, 469 KiB).

**Packaging, documentation, and maintenance**

* The built viewer bundle ships in source distributions and wheels, so a
  fresh installation has a viewer.
* New optional extra ``solid-node[web-snapshot]``.
* The development loop's per-node HTTP API under ``/node`` and the browser
  modules and dependencies that consumed it are removed. No published
  document, URL or CLI surface changes.
* Scaffolded projects ignore ``__pycache__/`` and ``_build*``; existing
  projects get ``_build*`` in ``.git/info/exclude`` on their next build.
* ``README.rst`` documents OpenSCAD as conditional and covers working on
  solid-node itself; the hosted documentation builds its embedded exports
  from source in CI.

v0.4.0
------

Released on 20/Jul/2026

**Breaking changes**

* The CLI is now command-first: ``solid <command> <node>``.
* ``solid new`` replaces the former solid-seed cloning workflow.

**New features**

* ``solid export`` generates a static viewer manifest and STL exports for a node tree.
* Exported models can be embedded with the standalone viewer widget and the
  ``.. solid-node::`` Sphinx directive.
* Added symbolic degree-aware math functions in ``solid_node.math``.
* Added ``assertBlockedBeyond`` and ``assertFreeWithin`` for kinematic-fit
  tests, plus ``along=`` support for translational perturbations.
* Added the ``NODE`` marker for choosing a node class from modules that define
  more than one.
* Node names now default from their parent attribute name.

**Correctness and reliability**

* Animation rendering is now idempotent across nested assemblies and multiple
  drivers.
* Node identity and artifact keys no longer collide across node classes,
  names, or positional/keyword parameter forms.
* Fixed animated rotation, translation reversal, operation deserialization,
  snapshots, testing-step offsets, and ``--failfast`` behavior.
* ``solid test`` now exits non-zero on failures and reports invalid test paths
  clearly.
* ``solid develop`` remains running after a broken reload and can launch the
  OpenSCAD viewer reliably.
* Improved mesh-intersection checks with configurable volume tolerance.

**Performance**

* Cached base meshes, loaded meshes, and Manifold objects.
* Composed transforms into one world matrix and added AABB broad-phase culling
  before exact intersection tests.

**Packaging, documentation, and maintenance**

* Migrated packaging to ``pyproject.toml`` and ensured compiled frontend assets
  ship in wheels.
* Relicensed the project from AGPL-3.0 to Apache-2.0, with updated attribution
  and NOTICE.
* Added comprehensive API, CLI, tutorial, testing, embedding, and architecture
  documentation.
* Removed obsolete CI configuration and refreshed contributor guidance.

v0.3.0
------

Released on 14/Jan/2026

**New Features**

* Snapshot CLI command for headless PNG rendering (ADR-019)
* Full CREDITS.md with license attribution for all dependencies

**Architecture Improvements (ADR-018)**

* Removed over-engineered WebSocket IPC (broker.py)
* Moved Git integration to solid-studio (git.py)
* Moved IDE refactoring features to solid-studio (refactor/)
* Removed dead code (exceptions.py, spatial.py)
* Framework is now lean and focused on core CAD functionality

**Maintenance**

* Added license headers to all source files
* Synchronized requirements.txt with setup.py
* Removed unused "unicorn" dependency

v0.2
----

Released on 25/Feb/2025

* JScadNode adapter for JSCAD backend support, plus further work on OpenScadNode
* API reference documentation building on Read the Docs

v0.1
----

After some evolution and several pre-releases (v0.0.1 through v0.0.8),
the project was documented and released as v0.1 with:

* Multi-backend support (SolidPython2, CadQuery, OpenSCAD)
* Web-based 3D viewer with React/Three.js
* Development server with hot-reload
* Test runner for CAD projects
* STL generation and optimization
