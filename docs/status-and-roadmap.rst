
.. _status-and-roadmap:

==========================
Project status and roadmap
==========================

This project has been developed and maintained by a single person so far, and as it is, it's pretty usable. It can already solve real bottlenecks in mechanical project development. It's still a bit far from 1.0 version, and until there a release may still change how a project is declared or how an assertion answers — 0.5 did both — so read the release notes before upgrading. The geometry you write inside a node is the stable part, and you're invited to use it in your next 3D printable Open Source project.

Since 0.5, and not yet released, a machine can declare named inputs —
drivers — that the viewer turns into sliders, and a part can be
**flexible**: a spring, a belt or a cable whose shape follows those
inputs rather than staying a fixed solid, re-evaluated in the browser as
you drive the machine. That closes the FlexibleNode this page had long
carried on its roadmap, though not in the shape it was written down: a
flexible part reads no time of its own, it takes its values through
connected ports, so keyframes never entered it. See
:doc:`Modeling parts <leaf-nodes>` and
:doc:`Animating with time <animation>`.

Version 0.5 answers geometric questions exactly wherever the CAD kernel can,
so assertions stop being mediated by tessellation; makes a project declare
itself in ``pyproject.toml`` and lets any command address any node; proves a
part is one connected solid and an assembly does not interfere with itself;
and replaces the three copies of the web viewer with a single package that
static exports, the Sphinx directive and ``solid develop`` all share. See
:doc:`changelog` for the full list, including its breaking changes.

Version 0.4 added ``solid export`` and the embedding pipeline — models
render in any static web page or Sphinx documentation, animations
included (see :doc:`embedding`) — along with a more robust builder
that recovers from broken edits.

Roadmap
=======

  * A command to pack the project into a distributable with source and builds
  * Improve the web viewer with workplanes, rulers, camera angles, a test runner
