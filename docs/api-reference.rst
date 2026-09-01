
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
      (a list of three numbers, e.g. ``[0, 0, 1]``). Operations chain
      within one render — each ``render()`` states absolute placement
      for its instant, and an assembly drops the operations it applied
      in previous renders before re-rendering — and apply both in the
      viewer and to the mesh used by tests. Returns the node itself, so
      calls can be chained. ``angle`` may be an expression involving
      :attr:`AssemblyNode.time` or any declared driver.

   .. method:: translate(translation)

      Translate this node by the vector ``translation``, a list of three
      numbers, e.g. ``.translate([100, 0, 0])``. Chains like
      :meth:`rotate`, and the node itself is returned.

   .. attribute:: fn

      Number of facets used to approximate curved surfaces, applied as
      OpenSCAD's ``$fn`` to the generated code. Only meaningful for
      OpenSCAD-based nodes (``Solid2Node``, ``OpenScadNode``); the
      OCCT-backed leaves (``CadQueryNode``, ``Build123dNode``, the
      sheet leaves, ``MolejoNode``) export high-resolution STLs on
      their own. Default is ``None``, which keeps OpenSCAD's coarse
      default.

   .. attribute:: name

      The node's name, used in viewer and test failure messages. Defaults
      to the class name; can be overridden with the ``name`` keyword
      argument of the constructor.

   .. automethod:: set_keyframe

   .. automethod:: clear_keyframe

   .. automethod:: assemble

   .. autoproperty:: mtime

Leaf nodes
----------

.. autoclass:: solid_node.node.leaf.LeafNode
   :members: time

.. autoclass:: solid_node.node.exact_leaf.ExactLeafNode
   :members: exact, shape

.. autoclass:: solid_node.node.Solid2Node
   :members: as_number

.. autoclass:: solid_node.node.CadQueryNode

.. autoclass:: solid_node.node.Build123dNode

.. autoclass:: solid_node.node.SheetLeafNode
   :members: profile, render, validated_profile

   .. attribute:: thickness

      Thickness of the stock the part is cut from. Required and positive,
      declared as a class attribute or passed as a ``thickness=``
      constructor argument.

   .. attribute:: dxf_file

      Path of the node's nominal cut file, written beside its ``.stl``
      and ``.brep``.

.. autoclass:: solid_node.node.Build123dSheetNode
   :members: profile

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

.. autoclass:: solid_node.node.StlNode

   .. method:: adjust(mesh)

      Optional hook correcting the selected body in code: receives a
      `trimesh <https://trimesh.org/>`_ mesh, returns the corrected
      one. Whatever it returns is what the artifact holds — and what
      the watertight gate judges.

   .. attribute:: stl_source

      Path of the committed ``.stl``, relative to the directory of the
      python file declaring the node.

   .. attribute:: require_watertight

      ``True`` by default: a mesh that does not enclose a solid fails
      at build, naming the defect. Set to ``False`` to admit an open
      mesh knowingly; the flag never changes geometry.

   .. attribute:: body

      0-based index selecting one connected component of a multi-body
      file. A multi-body file with no ``body`` fails with a per-body
      inventory of centroid, bounds and volume.

.. autoclass:: solid_node.node.FlexibleNode

.. autoclass:: solid_node.node.MolejoNode
   :members: shape_tolerance

Internal nodes
--------------

.. autoclass:: solid_node.node.internal.InternalNode
   :members: connect

.. autoclass:: solid_node.node.AssemblyNode
   :members: set_state, set_keyframe, clear_keyframe, time

.. autoclass:: solid_node.node.FusionNode
   :members: time

Ports
=====

Domain-typed connection points between nodes, importable from
``solid_node.node``. A port is declared as a class attribute; the
parent assembly binds it every render with
:meth:`~solid_node.node.internal.InternalNode.connect`. See
:doc:`Driving a machine <driving>`.

.. autoclass:: solid_node.node.Port

.. autoclass:: solid_node.node.RotationalPort

.. autoclass:: solid_node.node.TranslationalPort

.. autoclass:: solid_node.node.SignalPort

.. autofunction:: solid_node.node.declared_ports

Simulation
==========

The stepped simulation layer lives in ``solid_node.simulation``. See
:doc:`Driving a machine <driving>` for drivers and instructions, and
:doc:`Simulating and testing scenarios <scenarios>` for the loop and
scenario tests.

.. autoclass:: solid_node.simulation.Driver

.. autoclass:: solid_node.simulation.Instruction

.. autoclass:: solid_node.simulation.RampProgram

.. autoclass:: solid_node.simulation.Sim
   :members: at, every, trigger, run, state, time,
             cadence_costs, assertion_stats

   .. attribute:: trajectory

      The recorded ``(tick, states)`` history of the run, one entry
      per stepped tick.

.. autoclass:: solid_node.simulation.ScenarioTest
   :members: simulation, scenario_node

.. autofunction:: solid_node.simulation.qualified_drivers

.. autofunction:: solid_node.simulation.qualified_instructions

Testing
=======

The testing API lives in ``solid_node.test``. See
:doc:`Test-driven CAD <testing>` for a walkthrough of both ways of
writing tests: mixing ``TestCaseMixin`` into a node class, or writing a
``TestCase`` in a separate file.

.. autoclass:: solid_node.test.TestCase
   :members:

   ``assertNoDisconnectedSolids(node)`` checks that every topmost rigid solid
   in a subtree is one connected body. ``assertNoSolidInterference(node)``
   checks that those same printed solids have no positive-volume world-space
   overlap at the runner's current keyframe; exact boundary contact passes and
   there is no public overlap epsilon.
   ``assertAssemblySupported(node, gravity=(0, 0, -1), max_drop=1.0,
   ground=None, supports=None, stability_margin=0.0)`` checks the physical
   inverse over the same selection: that every printed solid is transitively
   held against gravity, proved by dropping it ``max_drop`` into whatever
   holds it, and that the assembly can then stand — that push-only normal
   forces over the contacts detected by that drop and by a symmetric lift
   balance every solid's weight and torque. ``stability_margin`` (mm) shrinks
   each contact patch toward its centroid first, so a balance that lives on a
   patch boundary can be rejected. The older
   ``assertNoPairwiseIntersections`` leaf sweep is deprecated and retained
   only for compatibility.

.. autoclass:: solid_node.test.TestCaseMixin

.. autofunction:: solid_node.test.testing_steps

.. autofunction:: solid_node.test.testing_instant

Decorators
==========

.. autofunction:: solid_node.node.decorators.property_as_number
