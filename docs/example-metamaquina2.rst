.. _example-metamaquina2:

=============
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
