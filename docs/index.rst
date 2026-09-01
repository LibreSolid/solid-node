Solid Node documentation
========================

Solid Node is an Open Source Python framework for designing and
simulating machines. You describe a machine as a tree of nodes in
Python — leaf parts modelled with the CAD backend that suits them
(OpenSCAD, SolidPython, CadQuery, build123d or JSCAD), plus laser-cut
sheets, imported STL meshes, and flexible parts whose shape follows
the machine's state. The machine declares its inputs as named
**drivers**: the browser viewer turns them into sliders and buttons
you drive by hand, a deterministic simulation steps them in Python,
and scenario tests assert what happens along the way — clearance held
through a move, an assembly that stands up under gravity — before
anything is committed to a printer or a laser cutter. The framework
builds only the pieces that changed, so a project keeps moving as it
grows, and a live viewer reflects each edit as you save it. It is
released under the Apache License 2.0: build what you like with it,
and license your own designs however you choose.

.. toctree::
   :maxdepth: 2
   :caption: Getting started

   why-solid-node
   quickstart

.. toctree::
   :maxdepth: 2
   :caption: Tutorial

   leaf-nodes
   assemblies
   declaring
   animation
   driving
   fusion
   testing
   scenarios

.. toctree::
   :maxdepth: 2
   :caption: Guides

   node-tree
   viewer
   embedding

.. toctree::
   :maxdepth: 2
   :caption: Reference

   examples
   cli
   api-reference
   status-and-roadmap
   contributing
   changelog

Indices and tables
==================
* :ref:`genindex`
* :ref:`search`
