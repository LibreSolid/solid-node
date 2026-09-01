
.. _status-and-roadmap:

==========================
Project status and roadmap
==========================

This project has been developed and maintained by a single person so far, and as it is, it's pretty usable. It can already solve real bottlenecks in mechanical project development. It's still a bit far from 1.0 version, and until there a release may still change how a project is declared, how an assertion answers, or what a published document contains — 0.5 and 0.6 both did — so read the release notes before upgrading. The geometry you write inside a node is the stable part, and you're invited to use it in your next Open Source machine.

Version 0.6 makes a model a *machine*. An assembly declares named
inputs — drivers — read back as ordinary attributes, addressed by
instance-qualified ids, turned into sliders and instruction buttons by
the viewer, and stepped deterministically by a new simulation layer
(``Sim``, ``Instruction``, ``ScenarioTest``). Ports carry values
between parts with declared units. Three part kinds joined the tree:
laser-cut sheets that derive their DXF from the same profile as their
solid, imported STL meshes a new part can be designed to fit, and
**flexible** parts — a spring, a belt, a cable — whose shape follows
the machine's state, re-evaluated in the browser as you drive it. That
closes the FlexibleNode this page had long carried on its roadmap,
though not in the shape it was written down: a flexible part reads no
time of its own, it takes its values through connected ports, so
keyframes never entered it. ``assertAssemblySupported`` proves an
assembly rests on the ground and balances under gravity. build123d
became a fifth modelling backend. See :doc:`Driving a machine
<driving>`, :doc:`Simulating and testing scenarios <scenarios>` and
:doc:`Modeling parts <leaf-nodes>`.

**Upgrading to 0.6 requires reinstalling the environment** (the shared
OCCT binding moves and its versions cannot coexist), and a host that
pins its own copy of the viewer bundle must upgrade it with the
framework: a 0.5.x viewer has no version gate, so pointed at a 0.6
document it silently renders only the part of the machine it can
evaluate. See :doc:`changelog` for the full list, including the
breaking changes.

Version 0.5 answers geometric questions exactly wherever the CAD kernel can,
so assertions stop being mediated by tessellation; makes a project declare
itself in ``pyproject.toml`` and lets any command address any node; proves a
part is one connected solid and an assembly does not interfere with itself;
and replaces the three copies of the web viewer with a single package that
static exports, the Sphinx directive and ``solid develop`` all share.

Version 0.4 added ``solid export`` and the embedding pipeline — models
render in any static web page or Sphinx documentation, animations
included (see :doc:`embedding`) — along with a more robust builder
that recovers from broken edits.

Roadmap
=======

  * A new declarative API for describing a model
  * Semantics for production, so a model carries how a part is to be made
    and not only what shape it is
  * Friction, adhesion and dynamics in the assembly-support assertion,
    which today proves reachability and static equilibrium only
  * Improve the web viewer with workplanes, rulers, camera angles, a test runner
