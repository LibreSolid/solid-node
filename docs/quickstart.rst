
.. _quickstart:

==========
Quickstart
==========

Requirements
============

* **Linux** — other platforms are currently untested and unsupported.
* **Python 3.10 or newer**.
* **OpenSCAD** — solid-node uses it to build the STL files of
  OpenSCAD-based nodes and to render snapshots, so it is required even
  if you only use the web viewer.
* Optionally, the **jscad** CLI (from npm) if you want to write nodes
  in JavaScript with ``JScadNode``.

Installation
============

Start by creating a virtual environment for your project

.. code-block:: bash

    $ virtualenv --python=python3 myproject-env
    $ source myproject-env/bin/activate

And install solid-node in your environment

.. code-block:: bash

    $ pip install solid-node

Make sure you have openscad installed. On Debian-based systems:

.. code-block:: bash

    $ sudo apt-get install openscad

Create your project
===================

Create a new project with a starting structure

.. code-block:: bash

    $ solid new myproject
    $ cd myproject

Start the solid process. By default, the web viewer is used.

.. code-block:: bash

    $ solid develop root

Open the link http://localhost:8000 in your browser. If you prefer
using Openscad as a viewer, use the --openscad parameter

.. code-block:: bash

    $ solid develop root --openscad

Open `root/__init__.py` file in your preferred code editor and
see your model update in the viewer as you modify the code.

Check the _build directory for the STLs of your project.
