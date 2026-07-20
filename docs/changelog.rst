
.. _changelog:

=========
Changelog
=========

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
