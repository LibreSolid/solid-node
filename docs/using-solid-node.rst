
.. _using-solid-node:

================
Using Solid Node
================

Make sure you have completed the ::doc:`Quickstart <quickstart>`.
At this point, you should be able to view your project at the viewer
- either Openscad or the web viewer - and have a source code to edit.

In Solid Node, project is organized in a tree structure, with leaf nodes
and internal nodes. **Leaf nodes** use uderlying modelling libraries, namely
**SolidPython**, **CadQuery**, **OpenScad** and **JScad", to generate solid
models. **Internal Nodes** combine children nodes in some way, like an
**Assembly** or **Fusion**

Each node implements the `render()` method. Leaf nodes return an object of the
underlying library. Internal nodes `render()` should return a list of child
instances.

Leaf Nodes
==========

There are four types of LeafNodes, each supporting one underlying technology
to create solids:

* **Solid2Node** Uses Solid Python 2, which is a python wrapper around OpenScad
* **CadQueryNode** Uses CadQuery, a pure python modeler based on OCCT
* **OpenScadNode** A wrapper around one OpenScad module
* **JScadNode** A wrapper around one JScad module

The ::doc:`Quickstart <quickstart>` starts with a Solid2Node example showing
a box with a hole. Below are the codes for the same model in each modelling
technology.

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

**TIP**: if you want to use CQ-editor, you can add `show_object` without
conflicting with Solid Node:

.. code-block:: python

    if __name__ == '__cq_main__':
        show_object(DemoProject().render())

OpenScadNode
------------

The same model can also be obtained using an **OpenScadNode**, which is a small
python wrapper around an OpenScad module.

.. code-block:: python

    from solid_node.node import OpenScadNode

    class DemoProject(OpenScadNode):

        scad_source = 'demo.scad'

Create a file `root/demo.scad` with a module to create the model:

.. code-block:: openscad

    module demo() {
      difference() {
        translate([-25, -25, 0]) {
          cube([50, 50, 50]);
        }
        cylinder(r=10, h=100);
      }
    }


JScadNode
---------

Finally, the model can also be obtained using an **JScadNode**, which similarly
to OpenScadNode, it's a python wrapper around an JScad function.

.. code-block:: python

    from solid_node.node import OpenScadNode

    class DemoProject(OpenScadNode):

        jscad_source = 'demo.js'

Create a file `root/demo.js` with a module to create the model:

.. code-block:: javascript

    const { square, circle } = require('@jscad/modeling').primitives
    const { subtract } = require('@jscad/modeling').booleans
    const { extrudeLinear  } = require('@jscad/modeling').extrusions

    function main() {
      let outerSquare = square({size: 50 });
      let innerCircle = circle({radius: 10 });

      let shape = subtract(outerSquare, innerCircle);
      return extrudeLinear({ height: 50 }, shape);
    }

    module.exports = { main }

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

    if __name__ == '__cq_main__':
        show_object(ClockBase().render())

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
First, to create a 6mm hole at the base, edit `root/clock_base.py`

.. code-block:: python

    class ClockBase(CadQueryNode):

        def render(self):
            wp = cq.Workplane("XY")
            return wp.circle(100).extrude(2) \
                .faces(">Z").workplane().hole(6)

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

    class SimpleClock(AssemblyNode, TestCaseMixin):

TestCaseMixin
-------------

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
they should not. Let's reduce the radius of our pin to 2.99, at
`root/pin.py`:

.. code-block:: python

    class Pin(Solid2Node):

        def render(self):
            return cylinder(r=2.99, h=20)

Run the tests again. This time, the two tests will pass.

@testing_steps
--------------

Even though the test has passed, if you look closely, the hole in pointer
and the pin are not really round, they are approximated by hexagons.
This is because internally STLs are generated for the models, and STLs
work with triangles. We have tested that in the initial setup the pieces
do not overlap, but our test can't tell yet if the parts can freely move.

By using the decorator `@testing_steps`, we can test the intersection of
pieces in several moments of the animation:

.. code-block:: python

    ...
    from solid_node.test import TestCaseMixin, testing_steps

    class SimpleClock(AssemblyNode, TestCaseMixin):
        ...

        @testing_steps(16)
        def test_pin_runs_free_in_base(self):
            self.assertNotIntersecting(self.base, self.pin)

        @testing_steps(16)
        def test_pin_runs_free_in_pointer(self):
            self.assertNotIntersecting(self.pointer, self.pin)

The tests above will each test run 32 times, at 32 different instants.
Run the tests again, and you'll see that the tests will pass and fail
in a pattern.

Running tests on the full animation cycle can be very time consuming.
We can keep test performance by applying the test to a slice of time

.. code-block:: python

        @testing_steps(4, end=0.125)
        def test_pin_runs_free_in_base(self):
            self.assertNotIntersecting(self.base, self.pin)

fn property
===========

You see that our tests are passing on the base, but not in the pointer,
as base is very roundly rendered. That's because CadQuery exports STL
files with more precision.

We can achieve that in `Soli2Node` nodes by setting the property `fn`
in the nodes `pin.py` and `pointer.py`, as the example below:

.. code-block:: python

    class Pointer(Solid2Node):

        fn = 256

Now you see the pin and hole seem more round, and the 0.01 margin
we put is enough to make the tests pass.

You should take in consideration the approximation error on holes
when using Openscad derived nodes, like `Solid2Node` and `OpenScadNode`
