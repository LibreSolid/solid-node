=======
History
=======

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
