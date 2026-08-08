
.. _cli:

======================
Command line reference
======================

The ``solid`` command follows the grammar::

    solid <command> [reference] [options]

where ``reference`` is a qualifier (``package.module:Class``), a Python
file path, or a file path plus class. When omitted, the project model in
``[tool.solid-node]`` of the nearest ancestor ``pyproject.toml`` is used.

Run ``solid <command> -h`` to see the options of each command.

solid new
=========

::

    solid new <name>

Creates a new project directory ``<name>`` with a package, model module,
``pyproject.toml`` manifest, and ``.gitignore``. Fails if ``<name>`` exists.

solid develop
=============

::

    solid develop [reference] [--web] [--web-dev] [--no-web] [--openscad]
                         [--debug-builder] [--debug-web] [--callback URL]

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

``--no-web``
    Run the watch-and-rebuild loop with no viewer at all, leaving
    ``SOLID_NODE_PORT`` free. Use this when another program renders the
    published build directory itself and only needs the rebuilds; pair it
    with ``--callback URL`` to be told when a new build is ready. It cannot
    be combined with ``--web``, ``--web-dev`` or ``--debug-web``.

``--debug-builder``
    Run the builder in the foreground so breakpoints work. Automatic
    reload is disabled in this mode.

``--debug-web``
    Run the webserver in the foreground to support breakpoints in it.

``--callback URL``
    POST the exact URL (with no request body) after the initial complete
    build and every later complete rebuild. Available in normal web mode and
    with ``--no-web``. The callback is best effort: delivery failures are
    logged and never stop development. It cannot be combined with
    ``--openscad`` or ``--web-dev``.

solid build
===========

::

    solid build [reference]

Builds the node once using the same ordinary pipeline as ``solid develop``,
publishes the complete current model in the normal build directory, and exits.
It starts neither a viewer nor a filesystem watcher. A missing resolved model
prints a diagnostic and exits with status 66 (``MODEL_NOT_FOUND``); other
build errors use a generic non-zero status. A failed later build leaves the
last complete published artifacts in place.

solid test
==========

::

    solid test [reference] [--failfast]

Builds the node at ``<path>`` and runs its tests — the ``test_*``
methods of the node itself (via ``TestCaseMixin``) and of its companion
test file, if one exists. See :doc:`Test-driven CAD <testing>` for how
to write tests.

``--failfast``
    Stop the test run on the first failure.

solid snapshot
==============

::

    solid snapshot [reference] [options]

Renders the node to a PNG image using the OpenSCAD CLI, without opening
any viewer. This gives a headless way to inspect a model — in CI, or
for AI agents to visually check their work.

.. code-block:: bash

    $ solid snapshot -o front.png --viewall --autocenter
    $ solid snapshot windmill.windmill:Sail --time 0.25 --imgsize 800x600 --projection ortho

``-o``, ``--output``
    Output file path. Default: derived from the resolved node.

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

solid export
============

::

    solid export [reference] [options]

Builds the node's STL meshes and writes a static, self-contained
directory that renders the model — animations included — in any
browser, with no server-side code. See :doc:`embedding` for what the
output contains and how to use it.

.. code-block:: bash

    $ solid export -o export
    $ python -m http.server -d export   # view at http://localhost:8000

``-o``, ``--output``
    Output directory. Default: ``export``.

``--fps``
    Animation frames per second in the manifest. Default: 30.

``--frames``
    Frames per animation cycle. Together with ``--fps`` this sets the
    cycle duration (default: 360 frames at 30 fps = 12 seconds).

``--no-widget``
    Export only ``manifest.json`` and ``models/``, without the viewer
    page and JS bundle. Useful when the viewer is supplied elsewhere —
    for example by the Sphinx extension at documentation build time.

Environment variables
=====================

``SOLID_BUILD_DIR``
    Directory where generated ``.scad`` and ``.stl`` files are placed,
    relative to the project root. Default: ``_build``.
