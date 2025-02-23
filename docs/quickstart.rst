
.. _quickstart:

==========
Quickstart
==========

Start by cloning solid-seed, which has a starting code for any project.

.. code-block:: bash

    $ git clone https://github.com/LibreSolid/solid-seed.git myproject


Then create a virtual environment for your project

.. code-block:: bash

    $ cd myproject
    $ virtualenv --python=python3 myproject-env
    $ source myproject-env/bin/activate

And install solid-node in your environment

.. code-block:: bash

    $ pip install solid-node

Make sure you have openscad installed

.. code-block:: bash

    $ sudo apt-get install openscad

Start the solid process. By default, the web viewer is used.

.. code-block:: bash

    $ solid root develop

Open the link http://localhost:8000 in your browser. If you prefer
using Openscad as a viewer, use the --openscad parameter

.. code-block:: bash

    $ solid root develop --openscad

Open `root/__init__.py` file in your prefered code editor and
see your model update in the viewer as you modify the code.

Check the _build directory for the STLs of your project.
