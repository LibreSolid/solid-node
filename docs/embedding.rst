.. _embedding:

===================================
Embedding models in pages and docs
===================================

``solid export`` (see the :ref:`command line reference <cli>`) turns a
node into a static directory that renders the model in any browser —
animations included, since operations are exported as raw ``self.time``
expressions and evaluated client-side. No server-side code is needed:
any static file host works.

What an export contains
=======================

::

    export/
    ├── manifest.json     # the node tree: names, colors, operations
    ├── models/           # one STL per distinct rigid part
    │   └── ...
    ├── index.html        # standalone viewer page
    └── solid-widget.js   # the viewer bundle (three.js based)

``manifest.json`` and ``models/`` are the data; ``index.html`` plus
``solid-widget.js`` are the viewer (omitted with ``--no-widget``).
Opening ``index.html`` over HTTP shows the model with orbit controls
and, for animated nodes, play/pause and a timeline.

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
runs OpenSCAD. A missing or invalid export directory fails the build
with a message saying which ``solid export`` invocation would create
it.

Exports referenced by the directive may be made with ``--no-widget``:
the extension completes them with the viewer files from the installed
``solid_node`` package at build time, so the repository only needs to
carry each model's ``manifest.json`` and STLs, and every embedded
model shares one copy of the viewer source.
