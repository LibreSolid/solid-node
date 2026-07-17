
.. _animation:

===================
Animating with time
===================

An `AssemblyNode` can use the property `self.time` to position its
children. The time is a number between 0 and 1 that will be resolved in
the viewer, and you can use it to position elements relative to time.

Edit `root/__init__.py` to rotate the pointer of the
:doc:`simple clock <assemblies>`:

.. code-block:: python

    class SimpleClock(AssemblyNode):

        def __init__(self):
            self.base = ClockBase()
            self.pointer = Pointer()
            super().__init__()

        def render(self):
            angle = -360 * self.time
            self.pointer.rotate(angle, [0, 0, 1])
            return [self.base, self.pointer]

The angle is negative because a positive rotation around the Z axis is
counter-clockwise (the right-hand rule), and clocks run clockwise.

Rendered with ``solid export`` — press play to see the pointer rotate:

.. solid-node:: _exports/simple_clock
   :height: 360px

At this point you should see a rotating pointer in the viewer.
If you are using the Openscad viewer, you need to enable animation
(View -> Animate) and set fps and number of frames.
Reload is not automatic in Openscad while animating.

Positioning operations
======================

Besides `rotate(angle, axis)`, nodes also have `translate([x, y, z])`.
Both apply in the viewer and in tests alike, and return the node
itself, so they can be chained:

.. code-block:: python

    self.pointer.rotate(angle, [0, 0, 1]).translate([0, 0, offset])

Don't confuse the node method `translate([x, y, z])` with solid2's
`translate(x, y, z)` primitive used inside a `Solid2Node.render()`: the
primitive shapes the part itself, the node method positions a part
within an assembly.

Every `render()` expresses **absolute** positions for its instant.
Before an assembly re-renders, the operations it applied on its
children in previous renders are dropped, so you always compute
placement from `self.time` alone — there is no accumulated state to
undo. This also means two different assemblies can drive the same node
(say, a wheel spun by its axle and steered by the steering assembly)
without disturbing each other's operations.

Non-linear kinematics
=====================

A linear expression of `self.time`, like ``-360 * self.time`` above,
works out of the box. For non-linear movement — anything that needs
trigonometry over time — use `solid_node.math`, which provides
degree-based `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2` and
`sqrt` matching OpenScad's semantics:

.. code-block:: python

    from solid_node.math import sin

    class Escapement(AssemblyNode):

        def render(self):
            angle = 15 * sin(360 * 8 * self.time)
            self.anchor.rotate(angle, [0, 0, 1])
            ...

These functions work in both worlds `self.time` lives in: in the
viewer, where time is symbolic and the expression is evaluated
client-side as you scrub the timeline, and in tests, where time is a
plain number (see :ref:`testing_steps <testing-steps>`). Python's
`math.sin` would crash on symbolic time — and it works in radians,
while all angles in Solid Node are degrees.
