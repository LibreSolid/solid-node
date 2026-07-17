
.. _api-reference:

=============
API Reference
=============

Nodes
=====

All node classes are importable from ``solid_node.node``. A project is a
tree of nodes: leaf nodes generate solids with an underlying modelling
library, internal nodes combine their children.

Common node API
---------------

.. autoclass:: solid_node.node.base.AbstractBaseNode

   .. method:: render()

      Every node must implement ``render()``. Leaf nodes return an object
      of the underlying modelling library; internal nodes return a list of
      child node instances.

   .. method:: rotate(angle, axis)

      Rotate this node by ``angle`` degrees around the vector ``axis``
      (a list of three numbers, e.g. ``[0, 0, 1]``). Operations accumulate
      and are applied both in the viewer and to the mesh used by tests.
      Returns the node itself, so calls can be chained. ``angle`` may be an
      expression involving :attr:`AssemblyNode.time`.

   .. method:: translate(translation)

      Translate this node by the vector ``translation``, a list of three
      numbers, e.g. ``.translate([100, 0, 0])``. Like :meth:`rotate`,
      the operation accumulates and the node itself is returned.

   .. attribute:: fn

      Number of facets used to approximate curved surfaces, applied as
      OpenSCAD's ``$fn`` to the generated code. Only meaningful for
      OpenSCAD-based nodes (``Solid2Node``, ``OpenScadNode``); CadQuery
      exports its own high-resolution STL. Default is ``None``, which
      keeps OpenSCAD's coarse default.

   .. attribute:: name

      The node's name, used in viewer and test failure messages. Defaults
      to the class name; can be overridden with the ``name`` keyword
      argument of the constructor.

   .. automethod:: set_keyframe

   .. automethod:: assemble

   .. autoproperty:: mtime

Leaf nodes
----------

.. autoclass:: solid_node.node.leaf.LeafNode
   :members: time

.. autoclass:: solid_node.node.Solid2Node
   :members: as_number

.. autoclass:: solid_node.node.CadQueryNode

.. autoclass:: solid_node.node.OpenScadNode
   :members: __init__

   .. attribute:: scad_source

      Path of the OpenScad source file, relative to the directory of the
      python file declaring the node.

   .. attribute:: module_name

      Name of the module to call inside :attr:`scad_source`. Defaults to
      the file name without the ``.scad`` extension.

.. autoclass:: solid_node.node.JScadNode

   .. attribute:: jscad_source

      Path of the JScad source file, relative to the directory of the
      python file declaring the node. The file must export a ``main``
      function.

Internal nodes
--------------

.. autoclass:: solid_node.node.internal.InternalNode

.. autoclass:: solid_node.node.AssemblyNode
   :members: set_keyframe, time

.. autoclass:: solid_node.node.FusionNode
   :members: time

Testing
=======

The testing API lives in ``solid_node.test``. See
:doc:`Test-driven CAD <testing>` for a walkthrough of both ways of
writing tests: mixing ``TestCaseMixin`` into a node class, or writing a
``TestCase`` in a separate file.

.. autoclass:: solid_node.test.TestCase
   :members:

.. autoclass:: solid_node.test.TestCaseMixin

.. autofunction:: solid_node.test.testing_steps

.. autofunction:: solid_node.test.testing_instant

Decorators
==========

.. autofunction:: solid_node.node.decorators.property_as_number
