
.. _cli:

======================
Command line reference
======================

The ``solid`` command follows the grammar::

    solid <command> [reference] [options]

where ``reference`` is a model name the project declares, a qualifier
(``package.module:Class``), a Python file path, or a file path plus
class. When omitted, the project's default model is used: the ``model``
key of ``[tool.solid-node]`` in the nearest ancestor ``pyproject.toml``.
See :ref:`several-models` for a project that declares more than one.

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
                         [--no-web] [--debug-builder]
                         [--callback URL]

Runs everything needed to develop a project: monitors the filesystem,
rebuilds the parts that changed, and opens a viewer that reloads
automatically. The viewer comes from the separate `solid-node-viewer
<https://github.com/LibreSolid/solid-node-viewer>`_ package
(``pip install "solid-node[viewer]"``; see :doc:`the viewer <viewer>`),
and the command fails before starting development processes when it is absent.

``--web``
    Explicitly view the project in the browser at http://localhost:8000,
    the same behavior as the default. Without ``solid-node-viewer``, the
    command fails naming the extra to install.

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
    ``--web-dev``.

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
    solid build --all

Builds the node once using the same ordinary pipeline as ``solid develop``,
publishes the complete current model in its build directory, and exits.
``--all`` builds every model the project declares (see
:ref:`several-models`), in declaration order, each into its own build
directory; a model that fails does not stop the walk, each outcome is
reported, and the exit status is nonzero when any model failed.
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
              [--placement-quantum MM]
    solid test --all [--failfast]

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

``--placement-quantum MM``
    Merge two relative placements into one verdict-memo question when
    they differ by less than this, absorbing the float noise of composing
    one rigid motion by two different routes. Default
    ``SOLID_TEST_PLACEMENT_QUANTUM``, else ``1e-9``. Accepted by both
    kernels; ``0`` restores the exact-bytes key. A non-default quantum
    names itself on the summary line. See :ref:`The placement quantum
    <placement-quantum>`.

``--all``
    Run the tests of every model the project declares as one run, each
    model built in its own build directory. A model that fails to load
    or build counts as one failure and the run goes on.

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

solid models
============

::

    solid models [--json]

Lists the project's models: name, state, reference, and which is the
default. The state is read from each model's build directory and nothing
else — ``unbuilt``, ``published`` when it holds ``viewer.json``, ``failed``
when it holds ``errors.json`` — so the command never imports project
code and costs nothing to call. ``--json`` prints one object with the
project root, the build root, the default's name and the models, each
with its ``build_dir``; a project that declares a single ``model`` lists
one entry whose name is null.

.. _import-step:

solid import-step
==================

::

    solid import-step FILE [--into PACKAGE_DIR] [--model NAME]

Reads a STEP document's assembly structure and writes two files of
project-owned, declarative source the pilot then edits: ``parts.py``,
one :ref:`StepNode <step-import>` subclass per product that is a part,
and ``assembly.py``, one ``AssemblyNode`` subclass per assembly product,
declaring one child per occurrence and a ``render()`` that places each
one by ``rotate`` then ``translate`` at the document's own placement,
under a comment naming the occurrence and the file it came from. The
generated model is a **machine at rest**: it declares no driver and
defines no ``simulate()`` — which joints move is a design decision the
pilot makes in the source this command hands over, not a guess the
document's placements could support.

``--into`` names the package directory the two files are written into,
created if it does not exist, and given an ``__init__.py`` when it holds
none; it defaults to the current directory. ``--model`` names the
generated model, defaulting to a name derived from the document's root
product, or from the file's stem when that product is unnamed.

The command **never overwrites**: when either file already exists it
writes neither, names the one that stopped it, and exits 1 — the same
rule ``solid new`` applies to its target directory, for the same reason.
It writes nothing, either, when the document holds a placement that is
not a proper rigid transform (a mirror or a scale): the framework's
``rotate``/``translate`` pair cannot state one, and the message names the
occurrence with its determinant and scale factor.

It takes no node reference and loads no node — like ``solid models``, it
never imports project code — but it does need the exact-geometry kernel
to read the document, exactly as ``StepNode`` does; an installation
without it is told so by name, with the remedy, rather than failing with
an import traceback.

The command never touches ``pyproject.toml``: it prints the
``[tool.solid-node.models]`` line to add, along with the ``solid build``
and ``solid develop`` invocations to try next — following ``solid
models``, which reads the manifest and never writes it.

.. _several-models:

Several models in one project
=============================

A project that holds a family of machines — one repository, one shared
library, one model per machine — declares them by name::

    [tool.solid-node]
    model = "wall_clock_01"

    [tool.solid-node.models]
    wall_clock_01 = "design.wall_clock_01.clock:WallClock01"
    wall_clock_02 = "design.wall_clock_02.clock:WallClock02"

Beside the table, ``model`` names the default by its key; leave it out and
a command given no reference lists the names instead of guessing. A name
is one word of letters, digits, underscores and hyphens, and may not be
the name of a directory at the project root. Each declared model is a
reference — ``solid build wall_clock_02``, ``solid develop wall_clock_01``
— and owns its own build directory, ``_build/<name>/``, with its own
``viewer.json``, ``errors.json`` and build lock, so building one never
touches another. A reference that is not a declared name — a sub-assembly
by qualifier or path — builds in ``_build/`` itself, as it always did.

Environment variables
=====================

``SOLID_BUILD_DIR``
    The build root, relative to the project root. Default: ``_build``. A
    declared model builds in ``<build root>/<name>``.

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

``SOLID_TEST_PLACEMENT_QUANTUM``
    The placement quantum (mm) of the verdict memo when no
    ``--placement-quantum`` is given. Default: ``1e-9``. Read by both
    kernels.

The ``solid`` command loads a ``.env`` file from the working directory
at startup, so a project can pin its ports there — and a developer can
select the faceted test kernel for one checkout without the choice
reaching CI, which has no such file. ``solid new`` ignores ``.env``.
