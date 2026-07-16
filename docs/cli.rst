
.. _cli:

======================
Command line reference
======================

The ``solid`` command follows the grammar::

    solid <command> <path> [options]

where ``<path>`` is the python source file of the node to work on. A
directory can be given instead, in which case its ``__init__.py`` is
used — so ``solid develop root`` and ``solid develop root/__init__.py``
are equivalent. Commands must be run from the project root directory.

Run ``solid <command> -h`` to see the options of each command.

solid new
=========

::

    solid new <name>

Creates a new project directory ``<name>`` with a starting structure:
a ``root`` node implementing a ``Solid2Node`` demo model, and a
``.gitignore`` for the build artifacts. Fails if ``<name>`` already
exists. See the :doc:`Quickstart <quickstart>`.

solid develop
=============

::

    solid develop <path> [--web] [--web-dev] [--openscad]
                         [--debug-builder] [--debug-web]

Runs everything needed to develop a project: monitors the filesystem,
rebuilds the parts that changed, and serves a viewer that reloads
automatically.

``--web``
    Start a webserver at http://localhost:8000 to view the project in
    the browser. This is the default when no viewer option is given.

``--openscad``
    Open the project in the OpenSCAD GUI instead. OpenSCAD reloads the
    generated code when it changes, except while animating.

``--web-dev``
    For working on the web viewer itself: additionally start the
    frontend development server (a proxy to ``npm start`` in the
    viewer's React app), so viewer code changes hot-reload too.

``--debug-builder``
    Run the builder in the foreground so breakpoints work. Automatic
    reload is disabled in this mode.

``--debug-web``
    Run the webserver in the foreground to support breakpoints in it.

solid test
==========

::

    solid test <path> [--failfast]

Builds the node at ``<path>`` and runs its tests — the ``test_*``
methods of the node itself (via ``TestCaseMixin``) and of its companion
test file, if one exists. See :ref:`Testing <using-solid-node>` in the
user guide for how to write tests.

``--failfast``
    Stop the test run on the first failure.

solid snapshot
==============

::

    solid snapshot <path> [options]

Renders the node to a PNG image using the OpenSCAD CLI, without opening
any viewer. This gives a headless way to inspect a model — in CI, or
for AI agents to visually check their work.

.. code-block:: bash

    $ solid snapshot root -o front.png --viewall --autocenter
    $ solid snapshot root --time 0.25 --imgsize 800x600 --projection ortho

``-o``, ``--output``
    Output file path. Default: ``snapshot.png``.

``--time``
    Animation time to render, between 0.0 and 1.0. Default: 0.0.

``--camera``
    Camera specification in OpenSCAD format. Either gimbal
    (``translate_x,y,z,rot_x,y,z,dist``) or vector
    (``eye_x,y,z,center_x,y,z``).

``--autocenter``
    Adjust the camera to look at the object's center.

``--viewall``
    Adjust the camera so the whole object fits in view.

``--imgsize``
    Image dimensions as WxH. Default: ``1920x1080``.

``--projection``
    ``perspective`` (default) or ``ortho``.

``--colorscheme``
    One of OpenSCAD's color schemes (``Cornfield``, ``Metallic``,
    ``Sunset``, ``Starnight``, ``BeforeDawn``, ``Nature``,
    ``DeepOcean``, ``Solarized``, ``Tomorrow``, ``Tomorrow Night``,
    ``Monotone``). Default: ``Cornfield``.

``--render`` / ``--preview``
    Mutually exclusive. ``--render`` does a full render (OpenSCAD's
    default: slower, accurate); ``--preview`` uses the ThrownTogether
    preview mode (faster, may show artifacts).

``--view``
    Comma-separated view helpers: ``axes``, ``crosshairs``, ``edges``,
    ``scales``, ``wireframe``.

Environment variables
=====================

``SOLID_BUILD_DIR``
    Directory where generated ``.scad`` and ``.stl`` files are placed,
    relative to the project root. Default: ``_build``.
