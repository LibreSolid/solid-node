.. _embedding:

===================================
Embedding models in pages and docs
===================================

``solid export`` (see the :ref:`command line reference <cli>`) turns a
node into a static directory that renders the model in any browser —
animations and driver controls included, since operations are exported
as raw symbolic expressions over ``$t`` and qualified driver ids and
evaluated client-side. No server-side code is needed: any static file
host works.

What an export contains
=======================

::

    export/
    ├── manifest.json     # the document (see below)
    ├── models/           # one STL per distinct rigid part
    │   └── ...
    ├── index.html        # standalone viewer page
    └── solid-widget.js   # the viewer bundle (three.js based)

``manifest.json`` and ``models/`` are the data; ``index.html`` plus
``solid-widget.js`` are the viewer (omitted with ``--no-widget``). The
viewer files are copied from the installed `solid-node-viewer
<https://github.com/LibreSolid/solid-node-viewer>`_ package — install it
with ``pip install "solid-node[viewer]"`` — and an export that wants them
in an installation without it fails saying so. The bundle is AGPL-3.0-only
and says so in its first lines, together with the address of its source;
publishing an export publishes that notice with it.
Opening ``index.html`` over HTTP shows the model with orbit controls,
play/pause and a timeline for animated nodes, and the
:doc:`driver controls <driving>` for a machine that declares them.

The manifest is a ``solid-node-export`` document carrying ``format``
and ``version``, the ``animation`` parameters, a ``drivers`` table
(qualified id → default, range, unit, dtype, scale), an
``instructions`` table, an ordered ``bindings`` table when the model
has one, the ``root`` node tree with its symbolic operations, and the
printed-``pieces`` inventory. The declared ``version`` is a property of
the *content*: a document with no drivers is version 1, drivers make it
version 2, a flexible part makes it version 3, and a model whose
operations repeat a subexpression makes it version 4, so documents
published by earlier releases keep rendering.

``bindings`` is how a repeated subexpression reaches the wire once
instead of once per use: each entry is ``{name, expression}``, named
``_b0``, ``_b1``, … in the order a consumer must evaluate them (an
entry names only ``$t``, a declared driver id, or an *earlier* entry),
and an operation or a flexible leaf's ``params`` may hold one of those
names in place of the expression it stands for. A model whose
expressions repeat nothing publishes no ``bindings`` key at all, so an
ordinary export is unaffected.

.. warning::

   The viewer gained a version gate in 0.6, and older viewers have
   none: a 0.5.x bundle pointed at a version 2 or 3 document will
   **silently render only the part of the machine it can evaluate**
   rather than refusing. If your host pins its own copy of
   ``solid-widget.js``, upgrade it together with the framework. This
   release's viewer refuses a document schema it cannot read, naming
   the version.

Embedding in any web page
=========================

Host the export directory and point an ``<iframe>`` at its
``index.html``:

.. code-block:: html

    <iframe src="export/index.html" style="width: 100%; height: 480px; border: 0;">
    </iframe>

Two URL query parameters control playback:

``t`` (0.0 to 1.0)
    The initial animation time.

``autoplay=0``
    Start paused. Combined with ``t`` this shows a static pose:
    ``index.html?t=0.25&autoplay=0``.

These two are the whole URL surface: a driver cannot yet be preset or
the control chrome suppressed from a query string. A host that needs
either drives the widget programmatically, below.

The JavaScript API
==================

Hosts that load ``solid-widget.js`` directly may call
``SolidNodeWidget.mount(target, manifestUrl, options)``. The package's
``solidNodeViewerApi`` declaration, browser global, and each mount
handle all report API version 5, and the viewer accepts document
schema versions 1, 2 and 3 — 4 once a released viewer version adds
``bindings`` evaluation; until then a version-4 document (any model
whose operations repeat a subexpression) is refused, loudly, naming the
version, in the same phase that already refuses an unknown one.

Camera options: ``view`` (camera and target), ``up`` and ``fov``; each
vector may be a three-number tuple, and ``fov`` is in degrees. When
omitted they preserve the established Z-up direction and 50° field of
view. ``driverControls: 'none'`` suppresses the built-in sliders,
buttons and breadcrumb, for a host that builds its own control UI:

.. code-block:: javascript

    const viewer = await SolidNodeWidget.mount('#model', 'manifest.json', {
      view: { camera: [80, -60, 40], target: [0, 0, 0] },
      up: [0, 0, 1],
      fov: 22.5,
      driverControls: 'none',
    });

Driving from the host
---------------------

The mount handle exposes the machine:

``drivers()``
    The document's driver table: qualified ids with default, range,
    unit, dtype and scale.

``driver(id)`` / ``setDriver(id, value)``
    Read and write one driver's current value. Values are in the
    driver's **native** units (the units its default and state are
    kept in), and ids are verbatim from the document. A declared
    ``range`` is presentation metadata and never clamps.

``onDriverChange(fn)``
    Subscribe to value changes, whatever their source — a slider, a
    running ramp, or another ``setDriver`` call.

``instructions()`` / ``trigger(name)``
    List the declared instructions, and run one. ``trigger`` returns
    ``{done, cancel()}``: the ramp runs client-side over the
    instruction's declared duration and lands exactly on target, and
    a later ``trigger`` replaces an active ramp.

Moving one driver does not recompute the tree: which operations
re-evaluate is decided by the free variables read off each parsed
expression, so a host can wire a gauge to ``onDriverChange`` and
drag values at frame rate. The handle also keeps the earlier
navigation surface — assembly metadata, subtree focus and visibility,
``setTime`` — unchanged.

Embedding in Sphinx documentation
=================================

The ``solid_node.sphinx`` extension provides a directive that embeds an
export in the built HTML. In ``conf.py``:

.. code-block:: python

    extensions = [
        # ...
        'solid_node.sphinx',
    ]

Then, in any document:

.. code-block:: rst

    .. solid-node:: exports/my_model
       :height: 300px
       :t: 0.25
       :autoplay: no

The argument is the path to an export directory, relative to the
current document (or to the documentation source directory, with a
leading ``/``). The directory is copied into the HTML output and
embedded as an ``<iframe>``.

Options:

``:height:``
    Height of the embedded viewer. Default: ``480px``. The width
    always follows the page.

``:t:``
    Initial animation time, 0.0 to 1.0.

``:autoplay:``
    ``yes`` (default) or ``no``. With ``no``, the animation starts
    paused — combine with ``:t:`` for a static pose.

The exports are generated ahead of the documentation build and
committed (or produced by a CI step) — the Sphinx build itself never
runs the CAD stack. A missing or invalid export directory fails the
build with a message saying which ``solid export`` invocation would
create it.

The directive's options are ``:height:``, ``:t:`` and ``:autoplay:``
only — like the URL surface, it cannot yet preset a driver or
suppress the control chrome, so a driven model embeds with its
controls showing at their defaults.

Exports referenced by the directive may be made with ``--no-widget``:
the extension completes them with the viewer files from the installed
``solid-node-viewer`` package at build time, so the repository only needs
to carry each model's ``manifest.json`` and STLs, and every embedded
model shares one copy of the viewer source. A documentation build
therefore needs the ``viewer`` extra installed; without it the build
warns — and fails under ``-W`` — naming the extra.
