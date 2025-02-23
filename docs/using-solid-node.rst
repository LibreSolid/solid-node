
.. _using-solid-node:

================
Using Solid Node
================

Make sure you have completed the ::doc:`Quickstart <quickstart>`.
At this point, you should be able to view your project at the viewer
- either Openscad or the web viewer - and have a source code to edit.

In Solid Node, project is organized in a tree structure, with leaf nodes
and internal nodes. **Leaf nodes** use uderlying modelling libraries, like
**SolidPython** and **CadQuery**, to generate solid models. **Internal Nodes**
combine children nodes in some way, like an **Assembly** or **Fusion**

Each node implements the `render()` method. Leaf nodes return an object of the
underlying library. Internal nodes `render()` should return a list of child
instances.

Leaf Nodes
==========

Solid2Node
----------

The initial example in *solid-seed* implements a **Solid2Node** node,
which uses **solidpython2** to create models. Open `root/__init__.py`:

.. code-block:: python

    from solid_node.node import Solid2Node
    from solid2 import cube, cylinder, translate

    class DemoProject(Solid2Node):

        def render(self):
            return translate(-25, -25, 0)(
                cube(50, 50, 50)
            ) - cylinder(r=10, h=100)


CadQueryNode
------------

The same model can be obtained using **CadQuery**:

.. code-block:: python

    import cadquery as cq
    from solid_node.node import CadQueryNode

    class DemoProject(CadQueryNode):

        def render(self):
            wp = cq.Workplane("XY")
            cube = wp.box(50, 50, 50)
            hole = wp.workplane(offset=-50).circle(10).extrude(100)
            return cube.cut(hole)

Internal Nodes
==============

There are two types of internal nodes: **AssemblyNode** and **FusionNode**.
An AssemblyNode is an assemble of its children nodes, while in FusionNode
the children nodes are fused in one mesh.


Simple Clock Example
====================

Let's make a very simple clock, as a proof of concept, mixing together
CadQuery and SolidPython, so we can demonstrate use of time and testing.

Create a new file `root/clock_base.py` and create a `CadQueryNode`:

.. code-block:: python

    import cadquery as cq
    from solid_node.node import CadQueryNode

    class ClockBase(CadQueryNode):

        def render(self):
            wp = cq.Workplane("XY")
            return wp.circle(100).extrude(2)

Now, a file `root/pointer.py` with a `Solid2Node`:

.. code-block:: python

    from solid_node.node import Solid2Node
    from solid2 import cube, cylinder, translate

    class Pointer(Solid2Node):

        def render(self):
            return translate(-5, -5, 3)(
                cube(10, 90, 10)
            )

And at `root/__init__.py`, an `AssemblyNode`

.. code-block:: python

    from solid_node.node import AssemblyNode
    from .clock_base import ClockBase
    from .pointer import Pointer

    class SimpleClock(AssemblyNode):

        base = ClockBase()
        pointer = Pointer()

        def render(self):
            return [self.base, self.pointer]

Now in the viewer you should see a round clock base with a pointer.

Using time
==========

The `AssemblyNode` can use the property `self.time` to position elements.
The time is a number between 0 and 1 that will be resolved in the viewer,
and you can use it to position elements relative to time.

Edit `root/__init__.py` to rotate the pointer:

.. code-block:: python

    class SimpleClock(AssemblyNode):

        base = ClockBase()
        pointer = Pointer()

        def render(self):
	    angle = 360 * self.time
	    self.pointer.rotate(angle, [0, 0, 1])
            return [self.base, self.pointer]

At this point you should see a rotating pointer in the viewer.
If you are using the Openscad viewer, you need to enable animation
(View -> Animate) and set fps and number of frames.
Reload is not automatic in Openscad while animating.

Testing
=======

Solid Node has a test runner and `solid_node.test.TestCase` extension to run tests
with meshes. As an example, you could use, for example. `AssertNotIntersecting`
to verify that two gears do not overlap during movement, or
`AssertIntersecting` to verify that a handle is not detached during movement.

There is also `solid_node.test.TestCaseMixin`, which allows you to write tests
in your node class instead of using a separate file.

To demonstrate testing, let's make a pin holding the pointer and base together.
First, to create a hole at the base, edit `root/clock_base.py`

.. code-block:: python

    class ClockBase(CadQueryNode):

        def render(self):
            wp = cq.Workplane("XY")
            return wp.circle(100).extrude(2)

And a hole in the pointer, at `root/pointer.py`

.. code-block:: python

    class Pointer(Solid2Node):

        def render(self):
            pointer = translate(-5, -5, 3)(
                cube(10, 90, 10)
            )
            hole = cylinder(r=3, h=15)
            return pointer - hole

Now, you should see a hole through both pointer and
pin, while the pointer is rotating.

Let's make a pin through them. Create the file `root/pin.py`:

.. code-block:: python

    from solid_node.node import Solid2Node
    from solid2 import cube, cylinder, translate

    class Pin(Solid2Node):

        def render(self):
            return cylinder(r=3, h=20)

And at `root/__init__.py`, assemble the pin together:

.. code-block:: python

    from solid_node.node import AssemblyNode
    from .clock_base import ClockBase
    from .pointer import Pointer
    from .pin import Pin

    class SimpleClock(AssemblyNode):

        base = ClockBase()
        pointer = Pointer()
        pin = Pin()

        def render(self):
            angle = 360 * self.time
            self.pointer.rotate(angle, [0, 0, 1])
            return [self.base, self.pointer, self.pin]

You should see the pin rendered in viewer, with a tight fit.
We want to test if this is functional: if in reality, this
arrangement will work. So, let's write a test.

For that, we'll use `solid_node.test.TestCaseMixin`. Add
it to the base classes of the root node at `root/__init__.py`:

.. code-block:: python

    ...
    from solid_node.test import TestCaseMixin

    class SimpleClock(AssemblyNode, TestCaseMixin)

TestCaseMixin
.............

Now we'll add tests to our root node. Our SimpleClock
class will extend `solid_node.test.TestCaseMixin` and
we'll add two tests to `root/__init__.py`:

.. code-block:: python

    from solid_node.node import AssemblyNode
    from solid_node.test import TestCaseMixin
    from .clock_base import ClockBase
    from .pointer import Pointer
    from .pin import Pin

    class SimpleClock(AssemblyNode, TestCaseMixin):

        base = ClockBase()
        pointer = Pointer()
        pin = Pin()

        def render(self):
            ...

        def test_pin_runs_free_in_base(self):
            self.assertNotIntersecting(self.base, self.pin)

        def test_pin_runs_free_in_pointer(self):
            self.assertNotIntersecting(self.pointer, self.pin)

On the command line, stop the `solid root develop` command, and
run `solid root test`.

You should see two tests failing, as in practice there is a very
small intersection between rendered meshes even though matematically
they should not. Let's reduce the radius of our pin to 2.9, at
`root/pin.py`:

.. code-block:: python

    class Pin(Solid2Node):

        def render(self):
            return cylinder(r=2.9, h=20)

Run the tests again. This time, the two tests will pass.
If you look closely, the cylinder of the pins are not really round.
They are an approximation. This is because internally STLs are generated
for the models.

@testing_steps
..............
The tests are passing, the pieces are not intersecting. But would they still
not intersect during the rotation of the pointer? The test we made just
tested the situation for the initial setup. We can improve the test
by using the decorator `solid_node.test.testing_steps`:

.. code-block:: python

    ...
    from solid_node.test import TestCaseMixin, testing_steps

    class SimpleClock(AssemblyNode, TestCaseMixin):
        ...

        @testing_steps(3, end=0.1)
        def test_pin_runs_free_in_base(self):
            self.assertNotIntersecting(self.base, self.pin)

        @testing_steps(3, end=0.1)
        def test_pin_runs_free_in_pointer(self):
            self.assertNotIntersecting(self.pointer, self.pin)

 The tests above will run three times, at three different instants,
 from time 0 to 0.1.
