
.. _quickstart:

==========
Quickstart
==========

Start by cloning solid-seed, which has a starting code for any project.

    ```bash
    $ git clone https://github.com/LibreSolid/solid-seed.git myproject
    ```
    
Then create a virtual environment for your project

    ```bash
    $ cd myproject
    $ virtualenv --python=python3 myproject-env
    $ source myproject-env/bin/activate
    ```

And install solid-node in your environment

    ```bash
    $ pip install solid-node
    ```

Make sure you have openscad installed

    ```bash
    $ sudo apt-get install openscad
    ```

Start the solid process. By default, the web viewer is used.

    ```bash
    $ solid root develop
    ```

Open the link http://localhost:8000 in your browser. If you prefer
using Openscad as a viewer, use the --openscad parameter

    ```bash
    $ solid root develop --openscad
    ```

Open `root/__init__.py` file in your prefered code editor and
see your model updated in the viewer.

Check the _build directory for the STLs of your project.

