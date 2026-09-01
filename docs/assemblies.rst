
.. _assemblies:

===============
Combining parts
===============

Parts become a project when they are combined by **internal nodes**.
An internal node's `render()` does not return a solid — it returns a
list of child node instances, after saying where each one sits and,
in a driven machine, wiring values between them.

There are two types of internal nodes:

* **AssemblyNode** — the children are separate parts that can move
  relative to each other. This is the node you'll use the most, and
  the subject of this page.
* **FusionNode** — the children are fused into one rigid, inseparable
  piece. Covered in :doc:`Fusing parts <fusion>`.

Both take part in the node tree the same way: an assembly can contain
leaf nodes, fusions and other assemblies.

The simple clock
================

Let's make a very simple clock, as a proof of concept, mixing together
CadQuery and SolidPython. This example continues through
:doc:`Animating with time <animation>` and :doc:`Test-driven CAD
<testing>`.

Create a new file `myproject/clock_base.py` and create a `CadQueryNode`:

.. code-block:: python

    import cadquery as cq
    from solid_node.node import CadQueryNode

    class ClockBase(CadQueryNode):

        def render(self):
            wp = cq.Workplane("XY")
            return wp.circle(100).extrude(2)

    if __name__ == '__cq_main__':
        show_object(ClockBase().render())

Rendered — the clock base:

.. solid-node:: _exports/clock_base
   :height: 360px

Now, a file `myproject/pointer.py` with a `Solid2Node`:

.. code-block:: python

    from solid_node.node import Solid2Node
    from solid2 import cube, cylinder, translate

    class Pointer(Solid2Node):

        def render(self):
            return translate(-5, -5, 3)(
                cube(10, 90, 10)
            )

Rendered — the pointer:

.. solid-node:: _exports/pointer_plain
   :height: 360px

And at `myproject/myproject.py`, an `AssemblyNode`:

.. code-block:: python

    from solid_node.node import AssemblyNode
    from .clock_base import ClockBase
    from .pointer import Pointer

    class SimpleClock(AssemblyNode):

        def __init__(self):
            self.base = ClockBase()
            self.pointer = Pointer()
            super().__init__()

        def render(self):
            return [self.base, self.pointer]

Rendered — base and pointer assembled (still, for now):

.. solid-node:: _exports/simple_clock_static
   :height: 360px

Now in the viewer you should see a round clock base with a pointer.

Children are instance attributes
================================

Children are created in ``__init__``, as instance attributes — this is
the rule to follow in every assembly, for two reasons:

* Children must keep their identity across renders, and each instance
  of the assembly must own its own children. Class attributes would be
  shared by every instance of the assembly, so two instances placed in
  different positions would be applying placement operations to the
  same objects.
* A child is named after the instance attribute that holds it: in the
  clock above, `self.base` and `self.pointer` show up in the viewer
  tree as ``base`` and ``pointer``. This is what keeps two children of
  the same class apart — two `Pointer()` instances held as
  `self.hours` and `self.minutes` are two distinct nodes, named
  ``hours`` and ``minutes``.

You can always override the derived name by passing ``name=`` to the
constructor, and children held in a list get indexed names
(``planets-0``, ``planets-1``, ...). The full naming rules — and how
node identity relates to build caching — are in
:doc:`Names, the node tree and caching <node-tree>`.

Assemblies declare the machine's inputs
=======================================

The assembly is also where a machine's named inputs live. A **driver**
is a class attribute, read back as an ordinary attribute in
``render()``:

.. code-block:: python

    from solid_node.simulation import Driver

    class Axis(AssemblyNode):

        position = Driver(default=20.0, range=(0.0, 160.0), unit='mm')

        def render(self):
            self.carriage.translate([self.position, 0, 0])
            return [self.rail, self.carriage]

The viewer turns drivers into sliders and declared instructions into
buttons, scoped to the assembly layer that declares them: an
assembly's controls appear when *it* is focused, so declare each input
on the assembly the input belongs to — an axis's travel on the axis,
the whole machine's ``Home`` on the machine. An assembly also wires
values between its children with ``connect()``, binding an expression
over its drivers to a child's port. Drivers, qualified ids, ports and
instructions are the subject of :doc:`Driving a machine <driving>`.

Assemblies are testable
=======================

Because an assembly knows its parts and their placements, the
:doc:`test framework <testing>` can interrogate it as a whole: that
parts do not interfere, that they form the connections the design
intends — and, with ``assertAssemblySupported``, that the assembly
actually rests on the ground and balances under gravity instead of
floating where the code put it.
