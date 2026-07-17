
.. _fusion:

============
Fusing parts
============

Sometimes several nodes describe one piece. A knob, for example, can be
modeled as a shaft plus a grip: two simple solids, easier to write and
read separately — but in reality it's a single rigid part, printed in
one go. That's what a **FusionNode** is for: its children are fused
into one mesh.

Let's build that knob. Create `root/knob_shaft.py`:

.. code-block:: python

    from solid_node.node import Solid2Node
    from solid2 import cylinder

    class KnobShaft(Solid2Node):

        fn = 64

        def render(self):
            return cylinder(r=4, h=30)

Rendered — the shaft:

.. solid-node:: _exports/knob_shaft
   :height: 360px

Then `root/knob_grip.py` — a tapered grip, with a small indicator mark
on top:

.. code-block:: python

    from solid_node.node import Solid2Node
    from solid2 import cube, cylinder, translate

    class KnobGrip(Solid2Node):

        fn = 64

        def render(self):
            grip = translate(0, 0, 28)(
                cylinder(r1=16, r2=12, h=14)
            )
            mark = translate(-1, -14, 41)(
                cube(2, 12, 2)
            )
            return grip + mark

Rendered — the grip:

.. solid-node:: _exports/knob_grip
   :height: 360px

And the fusion, at `root/knob.py`:

.. code-block:: python

    from solid_node.node import FusionNode
    from .knob_shaft import KnobShaft
    from .knob_grip import KnobGrip

    class Knob(FusionNode):

        def render(self):
            return [KnobShaft(), KnobGrip()]

The shaft and grip are fused into one rigid mesh:

.. solid-node:: _exports/knob
   :height: 360px

Unlike an assembly, a fusion consumes its children into a single mesh —
they don't need to keep their identity across renders, so creating them
directly in `render()` is fine.

Since the result of a fusion is rigid, a FusionNode cannot use
`self.time` (it raises an exception) — animate it from the AssemblyNode
that contains it instead.

Fusions in assemblies
=====================

A FusionNode takes part in the node tree like any other node, so it can
be a child of an AssemblyNode — and this is where fusing pays off: the
whole knob is placed, rotated and tested as one part.

Let's mount the knob on a panel and turn it. At `root/__init__.py`:

.. code-block:: python

    from solid_node.node import AssemblyNode, Solid2Node
    from solid2 import cube, translate
    from .knob import Knob

    class Panel(Solid2Node):

        def render(self):
            return translate(-40, -40, -3)(
                cube(80, 80, 3)
            )

    class VolumeControl(AssemblyNode):

        def __init__(self):
            self.panel = Panel()
            self.knob = Knob()
            super().__init__()

        def render(self):
            self.knob.rotate(-270 * self.time, [0, 0, 1])
            return [self.panel, self.knob]

    NODE = VolumeControl

Press play to turn the volume up:

.. solid-node:: _exports/knob_assembly
   :height: 360px

This file defines two node classes, so the module-level ``NODE``
marker tells Solid Node which one is *the* node of this file — without
it, loading the file fails with an `AmbiguousNodeError`. See
:doc:`Names, the node tree and caching <node-tree>`.
