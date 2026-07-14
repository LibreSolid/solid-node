
.. _changelog:

=========
Changelog
=========

v0.4.0
------

Unreleased

**License**

* Relicensed the project from AGPL-3.0 to Apache-2.0, with consent from all contributors

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
