.. _examples:

========
Examples
========

Two example machines are maintained alongside the framework, embedded
here live. The smaller models used throughout the tutorial pages are
committed with the documentation itself and indexed at the bottom.

V8 engine
=========

The V8 engine was vibe-coded as a testing project to demonstrate
solid-node and strengthen the framework. It has enough nested
rotations and translations to test the parity between Python,
OpenSCAD, browser viewer and embedded widget for all rendering
operations — and since increment 9 its valve springs are flexible
parts: each spring's height follows the valve it seats through a
connected port, so the springs compress in the browser as the engine
turns.

.. solid-node:: examples/v8-engine/docs/_exports/v8-engine
   :height: 620px

You can check the project source code at its Github page: https://github.com/LibreSolid/example-v8-engine

Metamaquina 2
=============

The `Metamaquina 2 <https://github.com/LibreSolid/Metamaquina2>`_ is a
real product: a Brazilian open-hardware RepRap 3D printer, originally
authored in OpenSCAD. Its solid-node model is a machine in the full
0.6 sense — and a reuse story: the original ``.scad`` sources are not
replaced but read in place, each leaf reaching one OpenSCAD module of
the historical design through solid2.

The machine declares ``x``, ``y`` and ``z`` drivers and machine-level
instructions (``Rest``, ``CenterX``, ``PresentBed``, ``HomeZ``), so
the widget below shows buttons at the top layer and sliders down the
breadcrumb. Its filament path, GT2 belts, bed springs and extruder
idler spring are flexible parts whose shape follows the machine's
state.

.. solid-node:: examples/metamaquina2/docs/_exports/metamaquina2
   :height: 620px

Models used in this documentation
=================================

The tutorial pages embed small committed exports under
``docs/_exports/``: the simple clock and its parts
(:doc:`assemblies`, :doc:`testing`), the knob fusion (:doc:`fusion`),
the per-backend demo boxes and the sheet demo (:doc:`leaf-nodes`), and
the two-axis plotter (:doc:`driving`). Each is built from the code
shown on its page.
