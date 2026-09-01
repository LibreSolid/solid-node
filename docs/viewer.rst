
.. _viewer:

======================
The development viewer
======================

``solid develop [reference]`` is where you spend your time: it builds
the node, serves a viewer, watches the source files, and rebuilds
whenever you save — the CAD equivalent of a web framework's
development server.

The web viewer
==============

By default, ``solid develop`` serves the web viewer at
http://localhost:8000. It shows the assembled model with orbit
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
pin its ports there — and several projects can run side by side.

The Openscad viewer
===================

If you prefer OpenScad as a viewer, use:

.. code-block:: bash

    $ solid develop --openscad

Solid Node keeps a `.scad` file of the tree up to date and OpenScad
picks up the changes. To see animations, enable View → Animate and set
fps and number of frames; note that reload is not automatic in
Openscad while animating.

OpenScad has no notion of drivers: a driven machine appears at its
currently bound state, and a flexible part as a still snapshot of that
state. To drive a machine by hand, use the web viewer.

Hacking on the viewer itself
============================

The web viewer is a React app served pre-built. To work on the viewer
frontend with hot reloading, run ``solid develop --web-dev``,
which proxies to an npm dev server (port 3000, or
``SOLID_NODE_FRONTEND_PORT``). ``--debug-builder`` and ``--debug-web``
add verbose logging — see the :doc:`command line reference <cli>`.
