=======
History
=======

Unreleased
----------

* A node now tracks the project modules its source imports, not just its own
  file, and a leaf whose artifacts are already current is no longer rendered
  (ADR-033). Editing a module that holds shared geometry but defines no node
  — the conventional ``kinematics.py`` — used to move no tracked mtime, so
  every artifact went on reporting up to date and ``solid develop`` never
  saw the edit; now it invalidates exactly the nodes that import it. Because
  the up-to-date check used to run *after* ``render()``, caching saved
  almost nothing: a no-op rebuild of a CadQuery-heavy project cost the same
  as building it from scratch (19.8 s either way), and now costs 3.2 s.
  ``CadQueryNode`` and ``JScadNode`` no longer rewrite an artifact that is
  already current. Two consequences worth knowing: ``assemble()`` may now
  call ``render()`` zero times rather than exactly once, so anything relying
  on a render side effect is affected; and a node whose geometry depends on
  something a static import walk cannot see — a data file read at runtime, a
  module reached through ``importlib``, an environment variable — can look
  current when it is not, where the old unconditional render hid it. An
  existing build directory rebuilds once as the corrected source set takes
  effect.
* New ``solid develop --no-web`` flag: run the watch-and-rebuild loop with no
  viewer, leaving ``SOLID_NODE_PORT`` free, for a host that renders the
  published build directory itself. Pairs with ``--callback URL``.
* Projects scaffolded by ``solid new`` ignore ``__pycache__/``.
* The build directory is now a symlink to a versioned sibling directory,
  rebound atomically on each publication (ADR-032). A reader following it
  always reaches one complete artifact set, and a verification build no
  longer fails when it publishes beside a running watch loop. Consumers that
  require the build path to be a real directory are affected; it still
  behaves as a directory for ordinary reads.
* Projects scaffolded by ``solid new`` ignore ``_build*``. An existing
  project gets that pattern recorded in ``.git/info/exclude`` on its next
  build, leaving its tracked ``.gitignore`` untouched. Because that exclude
  file is per-clone, a project created before this change may need
  ``_build*`` added to its ``.gitignore`` when cloned elsewhere.

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
