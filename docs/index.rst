Solid Node documentation
========================

Solid Node is an Open Source Python framework for parametric, 3D-printable
mechanical projects. You describe a machine as a tree of nodes in Python —
leaf parts modelled with the CAD backend that suits them, whether OpenSCAD,
SolidPython or CadQuery, assembled and animated through rotations and
translations — and the framework builds only the pieces that changed, so a
project keeps moving as it grows past the point where a monolithic render
becomes too slow. A live viewer in the browser reflects each edit as you
save it, and mechanical assertions let you test how components fit and move
before committing anything to the printer. It is released under the Apache
License 2.0: build what you like with it, and license your own designs
however you choose.

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
   animation
   fusion
   testing

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
