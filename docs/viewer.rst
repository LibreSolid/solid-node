
.. _viewer:

======================
The development viewer
======================

``solid develop [reference]`` is where you spend your time: it builds
the node, opens a viewer, watches the source files, and rebuilds
whenever you save — the CAD equivalent of a web framework's
development server.

The **browser viewer** is a separate package,
`solid-node-viewer <https://github.com/LibreSolid/solid-node-viewer>`_,
installed with ``pip install "solid-node[viewer]"``. It is the sole
interactive viewer opened by ``solid develop``; without it the command fails
before starting the development processes and names the extra to install.
``--web`` remains an explicit spelling of the default, and ``--no-web`` runs
only the watch-and-build loop for an external host.

The two packages are licensed differently: solid-node under Apache-2.0
and the viewer under AGPL-3.0-only. The framework is complete without the
viewer — it builds, tests, exports (``--no-widget``), develops with
``--no-web``, and takes fixed-pose snapshots through OpenSCAD — and reaches
the browser viewer only as a separate process when it is installed.

The web viewer
==============

With the ``viewer`` extra installed, ``solid develop`` serves the browser
viewer at http://localhost:8000. It shows the assembled model with orbit
controls, a navigation tree of the nodes, and plays the animation of
nodes that use `self.time`.

Edit and save any source file, and the affected parts are rebuilt in
the background and reloaded in the browser — no manual refresh.

Driving the model
=================

A model that declares :doc:`drivers <driving>` grows controls in this
same viewer: one slider per driver and one button per instruction
declared at the focused assembly layer, with a breadcrumb to walk the
focus down into subassemblies and back up. Sliders show a numeric
readout in the driver's design units, and dragging one re-evaluates
only the expressions that read it. The full description of the control
surface — scoping rules included — is in :doc:`Driving a machine
<driving>`; it applies unchanged to static exports and embedded
widgets (:doc:`Embedding models <embedding>`).

When an edit doesn't compile or fails to render, the viewer shows the
build error and keeps running: fix the code, save, and the model comes
back. If the `solid develop` process itself is not running (or was
restarted), the viewer shows a persistent offline banner until it
reconnects.

Ports
=====

The backend port is 8000 by default, configurable with the
``SOLID_NODE_PORT`` environment variable. The `solid` command loads a
``.env`` file from the working directory at startup, so a project can
pin its ports there — and several projects can run side by side. The
viewer's server inherits that environment.

OpenSCAD snapshots are a separate capability
============================================

OpenSCAD remains a supported modelling and output technology. To photograph
one numerically bound pose through its renderer:

.. code-block:: bash

    $ solid snapshot --renderer openscad

That fixed-pose snapshot renderer remains the default for ``solid snapshot``.
It is not an interactive viewer: OpenSCAD has no notion of the independent
driver controls and instructions, and flexible geometry is evaluated only at
the selected state. Use the browser viewer to drive a machine by hand.

Hacking on the viewer itself
============================

The browser viewer's source — the three.js widget, its React
development shell and the server ``solid develop`` launches — lives in
the `solid-node-viewer repository
<https://github.com/LibreSolid/solid-node-viewer>`_, not in solid-node.
Clone it, install it editable in the same environment as solid-node, and
run ``solid develop --web-dev``, which asks the viewer to start its own
npm dev server (port 3000, or ``SOLID_NODE_FRONTEND_PORT``) and proxy the
page to it, so viewer code changes hot-reload too. To step into the
viewer's server under a debugger, run it directly:
``solid-node-viewer serve --build-dir _build``. ``--debug-builder`` does
the same for the builder — see the :doc:`command line reference <cli>`.
