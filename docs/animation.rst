
.. _animation:

===================
Animating with time
===================

An `AssemblyNode` moves its children in `simulate()`, reading the
property `self.time`. On this page — the animation timeline — it is a
number between 0 and 1 that loops and is resolved in the viewer, and
you can use it to position elements relative to time. (`time` is one
driver among several: under a :doc:`stepped simulation <scenarios>` the
same `self.time` reads the simulation clock in seconds instead.)

Edit `myproject/myproject.py` to rotate the pointer of the
:doc:`simple clock <assemblies>`:

.. code-block:: python

    class SimpleClock(AssemblyNode):

        def __init__(self):
            self.base = ClockBase()
            self.pointer = Pointer()
            super().__init__()

        def render(self):
            return [self.base, self.pointer]

        def simulate(self):
            angle = -360 * self.time
            self.pointer.rotate(angle, [0, 0, 1])

The angle is negative because a positive rotation around the Z axis is
counter-clockwise (the right-hand rule), and clocks run clockwise.

`render()` builds the clock at rest — which parts it has, and where a
part that never moves sits — and the framework runs it once. `simulate()`
moves it: the framework runs it after `render()` on every instant, and it
is the one place `self.time` and the :doc:`drivers <driving>` are read.
The split is described in full in :ref:`Rest and motion
<rest-and-motion>`.

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

Every `simulate()` expresses **absolute** motion for its instant.
Before an assembly simulates again, the operations it applied on its
children last time are dropped, so you always compute motion from the
current inputs alone — `self.time` and any :doc:`drivers <driving>` —
with no accumulated state to undo. A motion composes *inside* the
part's rest placement: a part rotated in `simulate()` and translated in
`render()` spins about its own axis and is then carried to its seat.
This also means two different assemblies can drive the same node (say,
a wheel spun by its axle and steered by the steering assembly) without
disturbing each other's operations.

.. _non-linear-kinematics:

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

        def simulate(self):
            angle = 15 * sin(360 * 8 * self.time)
            self.anchor.rotate(angle, [0, 0, 1])
            ...

These functions work in both worlds `self.time` lives in: in the
viewer, where time is symbolic and the expression is evaluated
client-side as you scrub the timeline, and in tests, where time is a
plain number (see :ref:`testing_steps <testing-steps>`). Python's
`math.sin` would crash on symbolic time — and it works in radians,
while all angles in Solid Node are degrees.

More than trigonometry
----------------------

Motion is rarely all curves. A mechanism holds at a stop, moves over
part of a stroke and not the rest, counts whole steps, or follows a
path you measured rather than derived — and none of that can branch on
``self.time``, because in the viewer there is no value to branch on.
``solid_node.math`` carries the arithmetic that expresses those without
a branch:

* ``abs``, ``floor``, ``ceil``, ``sign``, ``min`` and ``max`` — the
  OpenSCAD builtins, which the browser evaluates from JavaScript's
  ``Math`` and which need no stand-in built out of ``sqrt``;
* ``clamp(x, low, high)`` and ``clamp01(x)`` — a value held within
  bounds, which is how a part stops at a stop;
* ``ramp(x, start, end)`` — 0 before ``start``, 1 after ``end``,
  straight through between, so a stage of a timeline is one term;
* ``lerp(a, b, u)`` — ``a`` at 0 and ``b`` at 1, unclamped;
* ``wrap(angle)`` — an angle folded into (-180, 180], and
  ``wrap(value, period)`` for anything else that repeats;
* ``piecewise(x, points)`` — linear interpolation through measured
  ``(x, y)`` waypoints, held flat past each end;
* ``bump(u)`` — a smooth 0–1–0 pulse over ``u`` in [0, 1], for a stage
  that rises and falls inside its own slice of the timeline.

A cam that dwells and then lifts, over a measured profile, reads as
what it is:

.. code-block:: python

    from solid_node.math import clamp01, piecewise

    PROFILE = [(0.0, 0.0), (90.0, 0.0), (150.0, 12.0), (210.0, 0.0)]

    class Valve(AssemblyNode):

        def simulate(self):
            angle = 360 * self.time
            self.stem.translate([0, 0, piecewise(angle, PROFILE)])

There is deliberately no ``round`` and no ``mod``. OpenSCAD rounds a
half away from zero, JavaScript rounds it toward +infinity and Python
rounds it to even, so a ``round`` could not mean one thing everywhere;
write ``floor(x + 0.5)``, which all three agree on. OpenSCAD spells
modulo as the ``%`` operator rather than a function, and its sign rule
differs from Python's, so ``wrap`` is built on ``ceil`` instead.

Some things stay yours to write, and one is worth naming because it
looks like it should be here. "1 when these two integers are equal" is
one line::

    def selected(a, b):
        return 1 - clamp01(abs(a - b))

but it is only an indicator *for integers* — for anything else it is a
triangular hat, quietly. The framework cannot check that precondition,
so the line lives in your project, where the precondition is yours to
state.

Points, not just numbers
------------------------

The same three faces cover small vector arithmetic, so a point turned
by a driver-derived angle survives the viewer::

    from solid_node.math import polar, rotate_x

    class Finger(AssemblyNode):

        def simulate(self):
            tip = rotate_x((0, 0, PHALANX), -90 * self.closure)
            self.pad.translate(list(tip))

``polar(radius, angle)`` gives a point on a ray, ``turn(point, angle,
about=...)`` turns a 2D point about a centre, and ``rotate_x``,
``rotate_y`` and ``rotate_z`` turn a 3D point about an axis. All
degrees, all right-handed, all returning plain tuples.
Before writing a mechanism out longhand over those functions, look in
`solid_node.mechanisms`: it carries the laws projects kept rewriting —
the external spur-gear mesh, the lead screw, the slider-crank, linear
delta kinematics, and the circle geometry a linkage keeps asking for.
Each is a composition over `solid_node.math`, so it has that module's
numeric and symbolic faces — and only those two: a mechanism law carries
degree literals the dimension algebra cannot type, so unlike the
functions of `solid_node.math` it has no third, declared face, and
reaching one from a class body raises there. Each states its frame, its
zero and its sign in the family module it lives in. See :doc:`the API
reference <api-reference>`.

The delta is the worked reason the package exists. A rod leaning toward
a moving effector leans about a direction that the effector's position
decides — and a `Rotation`'s axis is a *constant*: it cannot carry a
driver symbol, so ``rotate(angle, computed_axis)`` works in a test and
fails in the viewer. `delta_rod` therefore returns two rotations about
constant axes, ``-tilt`` about Y then ``azimuth`` about Z, which is the
same pose and survives symbolically. That finding cost one project a
rendered mesh to discover; it is now a docstring.

.. _time-base:

Declaring the time base
=======================

The timeline is a loop from 0 to 1, and nothing above says how long a
turn of it *is*. A machine modelled in real time declares that on its
root:

.. code-block:: python

    from solid_node.node import AssemblyNode, Time

    class WallClock(AssemblyNode):

        time = Time(loop=12 * 3600)   # one turn of the slider is twelve hours

        def simulate(self):
            self.movement.seconds = self.time

`loop` is the span of machine time, in seconds, that one turn of the
timeline covers. From then on `self.time` reads **seconds** everywhere:
here in `simulate()`, in every assembly below the root, in tests, under a
:doc:`stepped simulation <scenarios>`, and in `solid snapshot`. On the
build and viewer path the value is the symbolic product ``$t * loop``, so
the slider is still ``$t`` from 0 to 1 and the multiplication travels
inside the published expressions; nothing about the viewer's evaluation
changes. `set_keyframe(2700)` and ``@testing_steps(48, end=1.5)`` state
seconds — the decorators' defaults do not follow the declaration, so a
sweep over a declared root says the span it covers.

The time base is the root's: every assembly below it reads the root's
declaration, whether or not it declares one itself, and a declaration on
a linked descendant is refused when read, naming both nodes. A
sub-assembly loaded on its own, or under test, uses its own. A root that
declares nothing keeps the 0..1 fraction it always had.

The documents `solid build`, `solid export` and the web snapshot publish
carry the loop as ``animation.loop`` beside ``fps`` and ``frames``. The
viewer plays such a loop at real time by default and offers a speed
control to watch it faster — a twelve-hour clock at ×720 turns its hour
hand once a minute; an older viewer that does not read the key keeps
playing ``frames / fps`` seconds a turn, at the right pose throughout.

Beyond the timeline: drivers
============================

The timeline is one looping clock, and a machine has more than one
input: a crank angle, a valve lift, a carriage position. Those are
**drivers** — named inputs an assembly declares and reads exactly as
it reads `self.time`, which the viewer turns into sliders and buttons.
Drivers, ports, and machine instructions have their own chapter:
:doc:`Driving a machine <driving>`. `$t` keeps working alongside them
— one expression may mix the two — and the timeline transport keeps
driving `self.time` as before. A part whose *shape* moves — a spring,
a belt, a cable — is a flexible leaf driven through a port; see
:doc:`Modeling parts <leaf-nodes>`.

Freezing and releasing time
===========================

`set_keyframe(t)` pins an assembly and everything below it to one
instant, so `self.time` becomes the plain number `t` and meshes resolve
numerically. That is what tests and single-instant renders do.

Freezing is reversible: `clear_keyframe()` releases the assembly back
to symbolic time and simulates again, so its operations hold `$t`
expressions again — including expressions built with `solid_node.math`.
Rest placement — what `render()` did — is left alone, and nothing
accumulates however often you freeze and release.

.. code-block:: python

    clock.set_keyframe(0.25)     # self.time == 0.25, meshes are numeric
    pose = clock.pointer.mesh    # inspect one instant

    clock.clear_keyframe()       # self.time is $t again

This matters when one program both inspects and publishes a model. An
operation records whatever value `simulate()` computed, so a frozen node
has no expression left to publish — exporting it would write the frozen
numbers and produce a document that is valid, silent, and completely
static. `solid export` never freezes, and `export_node` releases the
node for you before serializing, so an export always carries the
animation. It leaves the node released afterwards; call `set_keyframe`
again if you still want a pose. To *show* one instant of an exported
model, use the widget's ``?t=`` and ``?autoplay=0`` options rather than
publishing a frozen document.
