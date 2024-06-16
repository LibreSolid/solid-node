.. highlight:: shell

============
Installation
============


As Git versioning is implemented SolidNode core, any project will require a git repository. You should start by forking from solid-seed.

.. code-block:: console

    $ git clone https://github.com/LibreSolid/solid-seed.git myproject

Then create a virtual environment for your project

.. code-block:: console

    $ cd myproject
    $ virtualenv --python=python3 myproject-env
    $ source myproject-env/bin/activate

And install solid-node in your environment

.. code-block:: console

    $ pip install solid-node
