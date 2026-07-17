
.. _testing:

===============
Test-driven CAD
===============

Solid Node has a test runner and `solid_node.test.TestCase` extension to
run tests with meshes. As an example, you could use
`assertNotIntersecting` to verify that two gears do not overlap during
movement, or `assertIntersecting` to verify that a handle is not
detached during movement.

Tests can be written in two styles, both run by the same
``solid test root`` command:

* mixing `solid_node.test.TestCaseMixin` into the node class, so tests
  live next to the rendering logic — used through most of this page;
* in a separate companion file, extending `solid_node.test.TestCase` —
  shown at the end, and the style the larger
  :doc:`gearbox example <examples>` uses.

A pin for the clock
===================

To demonstrate testing, let's make a pin holding the pointer and base
of the :doc:`simple clock <assemblies>` together.
First, to create a 6mm hole at the base, edit `root/clock_base.py`

.. code-block:: python

    class ClockBase(CadQueryNode):

        def render(self):
            wp = cq.Workplane("XY")
            return wp.circle(100).extrude(2) \
                .faces(">Z").workplane().hole(6)

Rendered — the base with its 6 mm hole:

.. solid-node:: _exports/clock_base_hole
   :height: 360px

And a hole in the pointer, at `root/pointer.py`

.. code-block:: python

    class Pointer(Solid2Node):

        def render(self):
            pointer = translate(-5, -5, 3)(
                cube(10, 90, 10)
            )
            hole = cylinder(r=3, h=15)
            return pointer - hole

Rendered — the pointer with its hole:

.. solid-node:: _exports/pointer_hole
   :height: 360px

Now, you should see a hole through both pointer and
base, while the pointer is rotating.

Let's make a pin through them. Create the file `root/pin.py`:

.. code-block:: python

    from solid_node.node import Solid2Node
    from solid2 import cube, cylinder, translate

    class Pin(Solid2Node):

        def render(self):
            return cylinder(r=3, h=20)

Rendered — the pin:

.. solid-node:: _exports/pin
   :height: 360px

And at `root/__init__.py`, assemble the pin together:

.. code-block:: python

    from solid_node.node import AssemblyNode
    from .clock_base import ClockBase
    from .pointer import Pointer
    from .pin import Pin

    class SimpleClock(AssemblyNode):

        def __init__(self):
            self.base = ClockBase()
            self.pointer = Pointer()
            self.pin = Pin()
            super().__init__()

        def render(self):
            angle = -360 * self.time
            self.pointer.rotate(angle, [0, 0, 1])
            return [self.base, self.pointer, self.pin]

Rendered — the full clock with the pin fitted (press play):

.. solid-node:: _exports/simple_clock_pin
   :height: 360px

You should see the pin rendered in viewer, with a tight fit.
We want to test if this is functional: if in reality, this
arrangement will work. So, let's write a test.

TestCaseMixin
=============

For that, we'll use `solid_node.test.TestCaseMixin`. Our SimpleClock
class will extend it, and we'll add two tests to `root/__init__.py`:

.. code-block:: python

    from solid_node.node import AssemblyNode
    from solid_node.test import TestCaseMixin
    from .clock_base import ClockBase
    from .pointer import Pointer
    from .pin import Pin

    class SimpleClock(AssemblyNode, TestCaseMixin):

        def __init__(self):
            self.base = ClockBase()
            self.pointer = Pointer()
            self.pin = Pin()
            super().__init__()

        def render(self):
            angle = -360 * self.time
            self.pointer.rotate(angle, [0, 0, 1])
            return [self.base, self.pointer, self.pin]

        def test_pin_runs_free_in_base(self):
            self.assertNotIntersecting(self.base, self.pin)

        def test_pin_runs_free_in_pointer(self):
            self.assertNotIntersecting(self.pointer, self.pin)

On the command line, stop the `solid develop root` command, and
run `solid test root`.

You should see two tests failing, as in practice there is a very
small intersection between rendered meshes even though mathematically
they should not. Let's reduce the radius of our pin to 2.99, at
`root/pin.py`:

.. code-block:: python

    class Pin(Solid2Node):

        def render(self):
            return cylinder(r=2.99, h=20)

Rendered — the slimmer pin:

.. solid-node:: _exports/pin_thin
   :height: 360px

Run the tests again. This time, the two tests will pass.

.. _testing-steps:

@testing_steps
==============

Even though the test has passed, if you look closely, the hole in pointer
and the pin are not really round, they are approximated by hexagons —
the :ref:`resolution problem <fn-property>` from Modeling parts. We
have tested that in the initial setup the pieces do not overlap, but
our test can't tell yet if the parts can freely move.

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

The tests above will each run 16 times, at 16 different instants.
Run the tests again, and you'll see that the tests will pass and fail
in a pattern: the base passes, because CadQuery renders it very
roundly, but the hexagonal hole in the pointer catches the pin at some
angles.

The fix is the `fn` property from
:ref:`Modeling parts <fn-property>` — set ``fn = 256`` on `Pointer`
and `Pin`, and the 0.01 margin we left is enough to make the tests
pass at every step. You should take in consideration the approximation
error on holes whenever OpenScad-derived nodes, like `Solid2Node` and
`OpenScadNode`, take part in a fit.

Running tests on the full animation cycle can be very time consuming.
We can keep test performance by applying the test to a slice of time

.. code-block:: python

        @testing_steps(4, end=0.125)
        def test_pin_runs_free_in_base(self):
            self.assertNotIntersecting(self.base, self.pin)

@testing_instant
================

While `@testing_steps` runs a test across a range of the animation,
`@testing_instant` runs it at one specific instant:

.. code-block:: python

    from solid_node.test import TestCaseMixin, testing_instant

    class SimpleClock(AssemblyNode, TestCaseMixin):
        ...

        @testing_instant(0.5)
        def test_pointer_at_half_turn(self):
            self.assertNotIntersecting(self.pointer, self.pin)

Tests in a separate file
========================

Instead of mixing `TestCaseMixin` into the node class, tests can live in
their own file, extending `solid_node.test.TestCase`. The test runner
looks for a companion file next to the node being tested:

* for a node in a package, like `root/__init__.py`, it loads
  `root/test.py`;
* for a node in a module, like `root/pointer.py`, it loads
  `root/test_pointer.py`.

The test class receives the built node as `self.node`, plus an alias
named after the test class (CamelCase converted to snake_case, with the
`Test` suffix dropped) — so a `SimpleClockTest` can also refer to the
node as `self.simple_clock`. The clock tests from above, in a separate
`root/test.py`:

.. code-block:: python

    from solid_node.test import TestCase, testing_steps

    class SimpleClockTest(TestCase):

        @testing_steps(4, end=0.125)
        def test_pin_runs_free_in_base(self):
            self.assertNotIntersecting(self.node.base, self.node.pin)

        @testing_steps(4, end=0.125)
        def test_pin_runs_free_in_pointer(self):
            self.assertNotIntersecting(self.node.pointer, self.node.pin)

Both styles are run by the same `solid test root` command, and can be
combined — this is how the gearbox in :doc:`Examples <examples>` keeps
one test file per part.

Available assertions
====================

Besides `assertNotIntersecting` and `assertIntersecting`, the test case
provides mesh assertions for fits and clearances:

* `assertNotIntersecting(node1, node2)` — the two meshes do not overlap
* `assertIntersecting(node1, node2)` — the two meshes have some overlap
* `assertInside(node1, node2)` — node2 is completely inside node1
* `assertClose(node1, node2, max_distance)` — every point of node2 is at
  most `max_distance` away from node1
* `assertFar(node1, node2, min_distance)` — every point of node2 is at
  least `min_distance` away from node1
* `assertIntersectVolumeAbove(node1, node2, min_volume)` — the overlap
  volume is above `min_volume`
* `assertIntersectVolumeBelow(node1, node2, max_volume)` — the overlap
  volume is below `max_volume`

Perturbation assertions
-----------------------

Two assertions verify a fit by perturbing a part around its own
position and checking the consequence, in both directions:

* `assertBlockedBeyond(node, angle, against, axis=(0, 0, 1))` — rotated
  by ``+angle`` and ``-angle`` degrees about `axis`, `node` must
  intersect `against`: the fit genuinely locks beyond its play. Use it
  to prove a key, a dog clutch or a hex socket actually engages.
* `assertFreeWithin(node, angle, against, axis=(0, 0, 1))` — the
  anti-gaming twin: rotated by ``±angle`` (or every angle in a list),
  `node` must **not** touch `against`. A blocking test alone could be
  satisfied by an undersized bore that always rubs; asserting free play
  within a smaller angle closes that loophole.

.. code-block:: python

    def test_dog_clutch_engages(self):
        self.assertFreeWithin(self.sleeve, 2, self.gear)
        self.assertBlockedBeyond(self.sleeve, 5, self.gear)

Adjacency sweep
---------------

* `assertNoPairwiseIntersections(node)` — walks the assembled tree
  rooted at `node` down to its leaves and asserts that every pair of
  leaves is non-intersecting. This is a safety net that holds
  regardless of which specific contracts exist: any two parts you
  forgot to test against each other directly are still covered.
  Combine it with `@testing_steps` to sweep the whole animation.

See the :doc:`API Reference <api-reference>` for details. All the
standard `unittest.TestCase` assertions are available as well.
