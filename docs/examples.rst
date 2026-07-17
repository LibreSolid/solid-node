
.. _examples:

========
Examples
========

Gearbox
=======

The repository ships a complete worked example in
`examples/gearbox <https://github.com/LibreSolid/solid-node/tree/main/examples/gearbox>`_:
a 5-speed + reverse constant-mesh car gearbox with dog-clutch engagement,
built and tested component by component. It exercises most of the
framework in a real project:

* **CadQuery leaf nodes** for gears (via ``cq_gears``), shafts, bushings
  and housing walls, parametrized from a single table of design
  constants.
* **Animated assemblies** — an ``AssemblyNode`` subclass in
  ``kinematics.py`` derives every gear's angle from ``self.time``
  through one shared meshing-law function.
* **Test-driven CAD** — each part has a companion ``test_*.py`` file
  (the separate-file style described in
  :doc:`Test-driven CAD <testing>`), asserting fits and
  clearances with ``assertNotIntersecting``, ``assertClose`` and
  friends, over the animation via ``@testing_steps``.
* **A design document** (``docs/design.md``) as the single source of
  truth every dimension in code traces back to.

To run it from a checkout of the repository:

.. code-block:: bash

    $ cd examples/gearbox
    $ pip install -r requirements.txt
    $ solid develop root

and to run its test suite:

.. code-block:: bash

    $ solid test root
