
.. _quickstart:

==========
Quickstart
==========

Requirements
============

Always needed:

* **Linux** — other platforms are currently untested and unsupported.
* **Python 3.11 or newer**.

Needed for OpenSCAD-family parts:

* **OpenSCAD** — builds the STL files of OpenSCAD-based nodes
  (``Solid2Node``, ``OpenScadNode``) and renders OpenSCAD snapshots.
  The project template ``solid new`` scaffolds starts from a
  ``Solid2Node``, so the quickstart path below needs it. A project
  whose parts are all OCCT-backed (``CadQueryNode``, ``Build123dNode``
  and the sheet leaves) builds, tests and exports without it.

Optional:

* The **jscad** CLI (from npm), if you want to write nodes in
  JavaScript with ``JScadNode``.

Everything else — CadQuery, build123d, trimesh, `molejo
<https://molejo.readthedocs.io>`_ for flexible parts — comes with
``pip install solid-node``. The **browser viewer** is a separate package,
`solid-node-viewer <https://github.com/LibreSolid/solid-node-viewer>`_,
installed through the ``viewer`` extra; without it, ``solid develop`` opens
OpenSCAD instead. The two are licensed differently — the framework under
Apache-2.0, the viewer under AGPL-3.0-only — which is why they are separate
packages you install separately.

Installation
============

Start by creating a virtual environment for your project

.. code-block:: bash

    $ virtualenv --python=python3 myproject-env
    $ source myproject-env/bin/activate

And install solid-node in your environment, with the browser viewer

.. code-block:: bash

    $ pip install "solid-node[viewer]"

or without it, keeping OpenSCAD as your only viewer

.. code-block:: bash

    $ pip install solid-node

For the default project template, make sure you have openscad
installed. On Debian-based systems:

.. code-block:: bash

    $ sudo apt-get install openscad

Upgrading from 0.5.x
====================

0.6 moves ``cadquery`` to 2.7 and adds ``build123d``, which share one
large binary OCCT wheel whose versions cannot coexist. **Upgrade by
recreating the virtual environment and reinstalling**, not with an
in-place ``pip install -U``. No project source changes are needed; see
the :doc:`changelog <changelog>` for the details.

Create your project
===================

Create a new project with a starting structure

.. code-block:: bash

    $ solid new myproject
    $ cd myproject

Start the solid process. With the ``viewer`` extra installed, the browser
viewer opens by default; otherwise OpenSCAD does. With no argument,
`solid develop` operates on the project's model, declared as
`model = "myproject.myproject:Myproject"` in the `pyproject.toml`
manifest `solid new` just wrote for you.

.. code-block:: bash

    $ solid develop

Open the link http://localhost:8000 in your browser. If you prefer
using Openscad as a viewer, or did not install the extra, use the
--openscad parameter

.. code-block:: bash

    $ solid develop --openscad

Open `myproject/myproject.py` file in your preferred code editor and
see your model update in the viewer as you modify the code.

Drive it
========

A model becomes a machine the moment it declares an input. Replace the
scaffolded class with an assembly that lifts it:

.. code-block:: python

    from solid_node.node import AssemblyNode, Solid2Node
    from solid_node.simulation import Driver
    from solid2 import cube, cylinder, translate

    class Block(Solid2Node):

        def render(self):
            return translate(-25, -25, 0)(
                cube(50, 50, 50)
            ) - cylinder(r=10, h=100)

    class Myproject(AssemblyNode):

        lift = Driver(default=0.0, range=(0.0, 80.0), unit='mm')

        def __init__(self):
            self.block = Block()
            super().__init__()

        def render(self):
            self.block.translate([0, 0, self.lift])
            return [self.block]

Save, and the viewer grows a ``lift`` slider: drag it and the block
follows. That slider travels with the model into every export and
embed — see :doc:`Driving a machine <driving>`. (The module now holds
two node classes, so if you kept the scaffolded test, declare its node
with ``node = Myproject`` — see :doc:`Testing <testing>`.)

Build artifacts
===============

Check the `_build` directory for the artifacts of your project: an STL
per leaf part, plus a `.brep` beside it for OCCT-backed parts (the
exact geometry) and a `.dxf` beside sheet parts (the nominal cut
profile).

From here, continue with the tutorial: :doc:`Modeling parts
<leaf-nodes>`.
