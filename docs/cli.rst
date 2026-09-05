
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

    solid develop [reference] [--set NAME=VALUE ...] [--web] [--web-dev]
                         [--no-web] [--openscad] [--debug-builder]
                         [--callback URL]

Runs everything needed to develop a project: monitors the filesystem,
rebuilds the parts that changed, and opens a viewer that reloads
automatically. Which viewer depends on what is installed: the browser
viewer when the separate `solid-node-viewer
<https://github.com/LibreSolid/solid-node-viewer>`_ package is present
(``pip install "solid-node[viewer]"``; see :doc:`the viewer <viewer>`),
the OpenSCAD GUI otherwise. An explicit flag is honoured or refused, never
swapped for the other viewer.

``--web``
    View the project in the browser at http://localhost:8000. The default
    when ``solid-node-viewer`` is installed; without it, the command fails
    naming the extra to install.

``--openscad``
    Open the project in the OpenSCAD GUI. The default when
    ``solid-node-viewer`` is not installed. OpenSCAD reloads the generated
    code when it changes, except while animating.

``--web-dev``
    For working on the browser viewer itself, from a source checkout of
    ``solid-node-viewer``: the viewer additionally starts its own npm dev
    server and proxies the page to it, so viewer code changes hot-reload too.

``--no-web``
    Run the watch-and-rebuild loop with no viewer at all, leaving
    ``SOLID_NODE_PORT`` free. Use this when another program renders the
    published build directory itself and only needs the rebuilds; pair it
    with ``--callback URL`` to be told when a new build is ready. It cannot
    be combined with ``--web`` or ``--web-dev``.

``--debug-builder``
    Run the builder in the foreground so breakpoints work. Automatic
    reload is disabled in this mode. To step into the browser viewer's
    server instead, run it yourself: ``solid-node-viewer serve --build-dir
    _build``.

``--callback URL``
    POST the exact URL (with no request body) after the initial complete
    build and every later complete rebuild. Available in normal web mode and
    with ``--no-web``. The callback is best effort: delivery failures are
    logged and never stop development. It cannot be combined with
    ``--openscad`` or ``--web-dev``.

``--set NAME=VALUE``
    Set a declared parameter of the root node (:doc:`Declaring a machine
    <declaring>`); repeat the flag for several. The value is parsed by the
    parameter's kind — a float for ``Length``, ``Angle``, ``Ratio`` and
    ``Scalar``, an integer for ``Count``, ``true`` or ``false`` for
    ``Flag``, the kinds declared from ``solid_node.parameters`` — and
    checked by its declared constraints. An unknown name
    fails listing the settable parameters; a derived parameter cannot be
    set; a root that declares nothing refuses the flag. A parameter
    declared without a default must be set this way when its node is
    loaded directly. Every rebuild of the watch loop applies the same
    overrides. The flag is shared by every command that loads a node:
    ``build``, ``test``, ``snapshot`` and ``export`` take it too.

solid build
===========

::

    solid build [reference] [--set NAME=VALUE ...]

Builds the node once using the same ordinary pipeline as ``solid develop``,
publishes the complete current model in the normal build directory, and exits.
It starts neither a viewer nor a filesystem watcher. A missing resolved model
prints a diagnostic and exits with status 66 (``MODEL_NOT_FOUND``); other
build errors use a generic non-zero status. Each artifact is published whole
or not at all, but a failed build can leave a partially updated model rather
than the last complete set; ``errors.json`` reports it. A reader may likewise
observe a mixed model while a build is running.

solid test
==========

::

    solid test [reference] [--set NAME=VALUE ...] [--failfast]
              [--exact | --faceted] [--volume-epsilon MM3]

Builds the node at ``<path>`` and runs its tests — the ``test_*``
methods of the node itself (via ``TestCaseMixin``) and of its companion
test file, if one exists. A companion ``ScenarioTest`` runs here like
any other test class, and the same class runs under plain ``pytest``
unmodified. See :doc:`Test-driven CAD <testing>` and
:doc:`Simulating and testing scenarios <scenarios>`.

``--failfast``
    Stop the test run on the first failure.

``--exact`` / ``--faceted``
    The kernel every geometric assertion decides on: exact parts on their
    boundary-representation solids (the default), or every pair on the
    parts' meshes at tessellation precision — the fast development loop.
    Without a flag ``SOLID_TEST_KERNEL`` decides, else the run is exact.
    A faceted run names itself before the first build and on its summary
    line. See :ref:`Choosing the comparison kernel <comparison-kernel>`.

``--volume-epsilon MM3``
    Under ``--faceted``, report an intersection of at most this volume as
    empty for the whole run. Default ``SOLID_TEST_VOLUME_EPSILON``, else 0.
    Refused with the exact kernel, which has nothing to absorb.

solid snapshot
==============

::

    solid snapshot [reference] [options]

Renders the node to a PNG image without opening a viewer. The default
OpenSCAD renderer is the fast inspection path; the optional web renderer
hands the model to the installed ``solid-node-viewer``, which photographs it
in headless Chromium and preserves a real alpha channel for compositing.

.. code-block:: bash

    $ solid snapshot -o front.png --viewall --autocenter
    $ solid snapshot windmill.windmill:Sail --time 0.25 --imgsize 800x600 --projection ortho
    $ solid snapshot --renderer web -o transparent.png

``--renderer``
    ``openscad`` (default) or ``web``. The default stays ``openscad``
    whether or not the browser viewer is installed. Install the web renderer
    with ``pip install "solid-node[web-snapshot]"`` (the viewer package with
    its browser driver) and download the browser separately with
    ``playwright install chromium``. Neither renderer ever falls back to the
    other when its dependency is unavailable.

``-o``, ``--output``
    Output file path. Default: derived from the resolved node.

``--time``
    Animation time to render, between 0.0 and 1.0. Default: 0.0. This
    poses the model through ``$t`` only; a driven machine renders at
    its declared driver defaults.

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
    ``perspective`` (default) or ``ortho``. OpenSCAD renderer only.

``--colorscheme``
    One of OpenSCAD's color schemes (``Cornfield``, ``Metallic``,
    ``Sunset``, ``Starnight``, ``BeforeDawn``, ``Nature``,
    ``DeepOcean``, ``Solarized``, ``Tomorrow``, ``Tomorrow Night``,
    ``Monotone``). Default: ``Cornfield``. OpenSCAD renderer only.

``--render`` / ``--preview``
    Mutually exclusive. ``--render`` does a full render (OpenSCAD's
    default: slower, accurate); ``--preview`` uses the ThrownTogether
    preview mode (faster, may show artifacts).
    OpenSCAD renderer only.

``--view``
    Comma-separated view helpers: ``axes``, ``crosshairs``, ``edges``,
    ``scales``, ``wireframe``.
    OpenSCAD renderer only.

With ``--renderer web``, explicitly supplying ``--projection``,
``--colorscheme``, ``--view``, ``--render``, or ``--preview`` is an error;
the command names every unsupported option rather than silently ignoring it.
``--camera`` accepts both OpenSCAD camera forms under either renderer.

solid export
============

::

    solid export [reference] [options]

Builds the node's STL meshes and writes a static, self-contained
directory that renders the model — animations and driver controls
included — in any browser, with no server-side code. The manifest
carries the document schema version and the machine's driver and
instruction tables. See :doc:`embedding` for what the output contains
and how to use it.

.. code-block:: bash

    $ solid export -o export
    $ python -m http.server -d export   # view at http://localhost:8000

``-o``, ``--output``
    Output directory. Default: ``export``.

``--fps``
    Animation frames per second in the manifest. Default: 30.

``--frames``
    Frames per animation cycle. Together with ``--fps`` this sets the
    cycle duration (default: 360 frames at 30 fps = 12 seconds). Both
    govern the ``$t`` timeline only — drivers have no frame grid, and
    a simulation's ``dt`` is unrelated.

``--no-widget``
    Export only ``manifest.json`` and ``models/``, without the viewer
    page and JS bundle. Useful when the viewer is supplied elsewhere —
    for example by the Sphinx extension at documentation build time — and
    the only way to export in an installation without ``solid-node-viewer``,
    since the widget files are copied from that package.

Environment variables
=====================

``SOLID_BUILD_DIR``
    Directory where generated build artifacts are placed, relative to
    the project root. Default: ``_build``.

``SOLID_NODE_PORT``
    Port of the ``solid develop`` browser viewer. Default: 8000. Read by
    the viewer's server, which inherits the environment ``solid`` loaded.

``SOLID_NODE_FRONTEND_PORT``
    Port of the viewer's npm dev server behind ``solid develop --web-dev``.
    Default: 3000.

``SOLID_TEST_KERNEL``
    The comparison kernel of ``solid test`` when no ``--exact`` /
    ``--faceted`` flag is given: ``exact`` (the default) or ``faceted``.
    Any other value is refused by name.

``SOLID_TEST_VOLUME_EPSILON``
    The volume epsilon (mm³) of a faceted ``solid test`` run when no
    ``--volume-epsilon`` is given. Default: 0. Not read by the exact
    kernel.

The ``solid`` command loads a ``.env`` file from the working directory
at startup, so a project can pin its ports there — and a developer can
select the faceted test kernel for one checkout without the choice
reaching CI, which has no such file. ``solid new`` ignores ``.env``.
