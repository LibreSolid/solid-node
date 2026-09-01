.. _examples:

========
Examples
========

Two example machines are maintained alongside the framework, each on
its own page and embedded there live — one page, one running model.
The smaller models used throughout the tutorial pages are committed
with the documentation itself and indexed at the bottom.

.. toctree::
   :maxdepth: 1

   example-v8-engine
   example-metamaquina2

:doc:`example-v8-engine`
   A vibe-coded V8, built to demonstrate solid-node and strengthen the
   framework: nested rotations and translations enough to test
   rendering parity across every backend, with valve springs that
   compress as the engine turns.

:doc:`example-metamaquina2`
   A real product — a Brazilian open-hardware RepRap 3D printer,
   originally authored in OpenSCAD and read in place, leaf by leaf. It
   is a machine in the full 0.6 sense: declared drivers, machine-level
   instructions, and flexible belts, springs and filament.

Models used in this documentation
=================================

The tutorial pages embed small committed exports under
``docs/_exports/``: the simple clock and its parts
(:doc:`assemblies`, :doc:`testing`), the knob fusion (:doc:`fusion`),
the per-backend demo boxes and the sheet demo (:doc:`leaf-nodes`), and
the two-axis plotter (:doc:`driving`). Each is built from the code
shown on its page.
