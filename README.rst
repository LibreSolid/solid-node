==========
Solid Node
==========


.. image:: https://img.shields.io/pypi/v/solid_node.svg
        :target: https://pypi.python.org/pypi/solid_node

.. image:: https://readthedocs.org/projects/solid-framework/badge/?version=latest
        :target: https://solid-framework.readthedocs.io/en/latest/?version=latest
        :alt: Documentation Status


**The Open Source framework for parametric 3D printable mechanical projects**

* Open Source: Apache License 2.0
* Documentation: https://solid-node.readthedocs.io

Quickstart
==========

.. code-block:: bash

    $ pip install solid-node
    $ solid new myproject

Transparent browser-rendered snapshots are optional because they require a
separate Chromium download:

.. code-block:: bash

    $ pip install "solid-node[web-snapshot]"
    $ playwright install chromium
    $ solid snapshot --renderer web -o transparent.png

See `the docs <https://solid-node.readthedocs.io>`_.

Working on solid-node itself
============================

This section is for contributors — humans and coding agents — who modify the
framework in this repository. For *using* solid-node in your own mechanical
project, see the documentation above.

Development environment
-----------------------

Requirements: Python >= 3.11, and Node.js >= 20 only if you intend to rebuild
the web viewer or the embeddable widget. `OpenSCAD
<https://openscad.org/>`_ is conditional: put it on the PATH when working on
SolidPython2/Solid2 or raw OpenSCAD nodes, faceted fusions, symbolic Solid2
animation values, the ``solid develop --openscad`` viewer, or the default
OpenSCAD snapshot renderer. All-exact CadQuery projects build, test, and export
without it; use ``solid snapshot --renderer web`` for snapshots on a machine
without OpenSCAD.

Clone with submodules (the docs embed the example V8-engine project):

.. code-block:: bash

    $ git clone --recurse-submodules https://github.com/LibreSolid/solid-node.git
    $ cd solid-node

Create a virtualenv and install the package in editable mode with the dev
dependencies:

.. code-block:: bash

    $ python -m venv .venv
    $ source .venv/bin/activate
    $ pip install -e ".[dev]"

The ``solid`` CLI entrypoint (``solid_node/cli.py``) is now on the PATH of
the virtualenv.

Running tests
-------------

The test suite is pytest, run from the repository root:

.. code-block:: bash

    $ make test          # equivalent to: pytest
    $ pytest tests/test_builder_lifecycle.py   # a single file
    $ make lint          # flake8 + black --check
    $ make test-all      # tox across supported Python versions

Notes:

* Rendering tests invoke the real ``openscad`` binary. On a headless machine,
  snapshot-related tests may need ``xvfb-run -a pytest ...``.
* Browser-snapshot tests are mandatory for changes to that renderer. Install
  the ``web-snapshot`` extra and Chromium as shown above; a missing browser is
  reported as a setup failure rather than skipped.
* ``tests/meta_project/`` together with ``tests/test_meta.py`` is the
  end-to-end meta-project harness: it runs small real solid-node projects —
  both deliberately green and deliberately red fixtures — to prove the
  loading, rendering, and ``solid test`` subprocess paths. Use it when a
  change touches behavior that direct unit tests cannot establish; see
  `docs/contributor-briefing.md <docs/contributor-briefing.md>`_ for when and
  why.
* Browser tests for the web viewer live with the application under
  ``solid_node/viewers/web/``.

Where things live
-----------------

* ``solid_node/node/`` — the node tree (base, assembly, fusion, leaf, CAD
  backend adapters, operations)
* ``solid_node/manager/`` and ``solid_node/cli.py`` — the ``solid`` command:
  develop loop, test, snapshot, new, export
* ``solid_node/core/`` — build pipeline, loader, caching
* ``solid_node/test.py`` — mesh-oriented test cases and assertions
* ``solid_node/viewers/`` — OpenSCAD snapshotter, web viewer
  (FastAPI + React/three.js), embeddable widget
* ``tests/`` — Python test suite
* ``docs/`` — Sphinx documentation, architecture synthesis, ADRs
* ``openspec/`` — OpenSpec change proposals and baseline specs

Development discipline
======================

This repository is developed agentically and follows a strict
spec-first discipline. **Every behavioral change starts as an OpenSpec
change proposal and is ratified before implementation.** Drive-by edits,
unrecorded redesigns, and "fix it first, document it later" are not how
this project moves — this applies equally to human contributors and to
coding agents operating autonomously.

OpenSpec changes
----------------

Behavioral contracts live in ``openspec/specs/``. Changes are proposed,
reviewed, implemented, and archived through the OpenSpec workflow
(`OpenSpec <https://openspec.ai>`_, CLI v1.x; the repo's
``openspec/config.yaml`` carries project context and rules):

1. **Propose** — create a change under ``openspec/changes/<name>/`` with
   ``proposal.md`` (why, what changes, capabilities, impact), ``design.md``
   (how), and ``tasks.md`` (implementation steps). The change describes
   *deltas* against the current specs.
2. **Review** — the proposal is inspected and refined before any code is
   written. Specs describe observable behavior only; no aspirational
   requirements.
3. **Apply** — implement the ratified proposal, task by task, TDD-style:
   red evidence first (a failing test that pins the contract), then the
   smallest change that satisfies it.
4. **Archive** — when the change lands, its spec deltas are merged into
   ``openspec/specs/`` and the change moves to ``openspec/changes/archive/``.

The ``.claude/commands/opsx/`` and ``.claude/skills/openspec-*/`` directories
encode this workflow for agents (``propose``, ``apply``, ``archive``, etc.);
humans can drive the same lifecycle with the ``openspec`` CLI directly.

Architecture Decision Records
-----------------------------

*Why* the system is the way it is lives in ``docs/adrs/`` (see
`docs/adrs/README.md <docs/adrs/README.md>`_ for the index and the full
discipline):

* One decision per ADR, numbered sequentially, filed under the subsystem it
  affects (NODE, BUILD, IPC, MATH, TEST-FRAMEWORK, VIEWER-WEB, EXPORT).
* Statuses flow ``Proposed`` → ``Accepted``; later ADRs may mark earlier ones
  ``Superseded``. Superseded ADRs stay in the log — they are the history that
  makes current decisions legible.
* When an OpenSpec change carries an architectural shift, its ADR is written
  alongside the change and the architecture synthesis
  (`docs/architecture.md <docs/architecture.md>`_) is updated as part of
  landing it.

Read order for orientation: **architecture synthesis first**
(``docs/architecture.md``), **then the specs** for exact observable behavior
(``openspec/specs/``), **then an ADR** when you need to know why
(``docs/adrs/``). The contributor briefing
(`docs/contributor-briefing.md <docs/contributor-briefing.md>`_) adds
verification guidance: how to choose between direct pytest coverage and the
meta-project harness, and the red-first evidence principle.

Contributing
============

Bug reports and pull requests are welcome at
https://github.com/LibreSolid/solid-node — see
`CONTRIBUTING.rst <CONTRIBUTING.rst>`_ and the development discipline above.
