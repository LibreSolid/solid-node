
.. _animation:

===================
Animating with time
===================

An `AssemblyNode` can use the property `self.time` to position its
children. The time is a number between 0 and 1 that will be resolved in
the viewer, and you can use it to position elements relative to time.

Edit `myproject/myproject.py` to rotate the pointer of the
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

Animating a shape, not just a placement
=======================================

Everything above moves a part *around*. A spring, a belt or a cable
moves differently: the part itself changes shape. That is what a flexible
leaf is for (see :doc:`Modeling parts <leaf-nodes>`), and it animates
through the same idea as everything else on this page — a value the
viewer resolves — with one extra hop.

The hop exists because `self.time` is one global clock, and a machine has
more than one input: a crank angle, a valve lift, a carriage position.
Those are **drivers**, declared on an assembly with a default and the
range a maker thinks in:

.. code-block:: python

    from solid_node.simulation import Driver

    class Valvetrain(AssemblyNode):

        lift = Driver(default=0.0, range=(0.0, 12.0), unit='mm')

A driver is read as an ordinary attribute — `self.lift` — and used in
expressions exactly as `self.time` is. The chain to a flexible part is
then **driver → port → shape**: the assembly writes an expression over
its drivers and connects it to the part's port, and the part's geometry
follows:

.. code-block:: python

    def render(self):
        self.connect(FREE_HEIGHT - self.lift, self.spring.height)
        self.gear.rotate(self.lift * 30, [1, 0, 0])
        return [self.gear, self.spring]

Both lines in that `render()` are the same kind of statement. One says
where a rigid gear sits; the other says how tall the spring is. Neither
computes a number: like a `self.time` expression, each is carried into
the viewer unevaluated and resolved there, so the spring's geometry is
recomputed in the browser on exactly the frames its own inputs moved.

The viewer builds a slider for each declared driver, so a reader of your
published model can push the valve down and watch the spring close. `$t`
still works alongside them — one expression may mix the two — and the
timeline transport keeps driving `self.time` as before.

Freezing and releasing time
===========================

`set_keyframe(t)` pins an assembly and everything below it to one
instant, so `self.time` becomes the plain number `t` and meshes resolve
numerically. That is what tests and single-instant renders do.

Freezing is reversible: `clear_keyframe()` releases the assembly back
to symbolic time and re-renders, so its operations hold `$t`
expressions again — including expressions built with `solid_node.math`.
Static placement you applied outside an assembly's `render()` is left
alone, and nothing accumulates however often you freeze and release.

.. code-block:: python

    clock.set_keyframe(0.25)     # self.time == 0.25, meshes are numeric
    pose = clock.pointer.mesh    # inspect one instant

    clock.clear_keyframe()       # self.time is $t again

This matters when one program both inspects and publishes a model. An
operation records whatever value `render()` computed, so a frozen node
has no expression left to publish — exporting it would write the frozen
numbers and produce a document that is valid, silent, and completely
static. `solid export` never freezes, and `export_node` releases the
node for you before serializing, so an export always carries the
animation. It leaves the node released afterwards; call `set_keyframe`
again if you still want a pose. To *show* one instant of an exported
model, use the widget's ``?t=`` and ``?autoplay=0`` options rather than
publishing a frozen document.
