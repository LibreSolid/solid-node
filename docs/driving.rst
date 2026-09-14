
.. _driving:

=================
Driving a machine
=================

:doc:`Animation <animation>` moves a model with one looping clock. A
machine has more inputs than that: a carriage position, a crank angle,
a valve lift. In Solid Node those are **drivers** — named inputs an
assembly declares, with a default and the range a maker thinks in —
and `self.time` is one driver among several rather than the only one.

This page builds a small XY plotter you can drive by hand in the
embedded viewer at the end.

Declaring a driver
==================

A driver is a class attribute on an assembly, and it is read back as an
ordinary attribute:

.. code-block:: python

    from solid_node.node import AssemblyNode
    from solid_node.simulation import Driver

    TRAVEL = 160.0

    class Axis(AssemblyNode):
        """One linear axis: a rail and the carriage that rides it."""

        position = Driver(default=20.0, range=(0.0, TRAVEL), unit='mm')

        def __init__(self, *args, **kwargs):
            self.rail = Rail()
            self.carriage = Carriage()
            super().__init__(*args, **kwargs)

        def render(self):
            return [self.rail, self.carriage]

        def simulate(self):
            self.carriage.translate([self.position - TRAVEL / 2, 0, 11])

`self.position` is read in `simulate()`, the method the framework runs
on every instant after `render()` has built the axis at rest, and it is
used in expressions exactly as `self.time` is: the
expression is carried into the published document unevaluated and
resolved in the viewer, so dragging the driver moves the carriage
without re-running any Python.

Three rules keep driver state honest, and each fails loudly rather
than guessing:

* A driver's value belongs to a bound snapshot. **Assigning** to one
  (``self.position = 12``) raises and names `set_state`, the one way a
  value is bound from Python.
* **Reading** a driver that no snapshot has bound raises and names the
  driver. In the viewer and in `solid export` the declared defaults
  are bound for you.
* A declaration whose name would **shadow** a node member — `render`,
  `color`, `time` — fails at class-definition time, before any
  instance exists.

`range` is presentation metadata: it is what a slider travels over and
what a reader of your model sees. It never clamps — an instruction or
a simulation may drive past it, and the readout stays truthful.

Native and design units
-----------------------

A real axis often counts in units the electronics use, not the units
the design is drawn in. `dtype` and `scale` keep the two straight:

.. code-block:: python

    # GT2 belt on a 20-tooth pulley: 40mm/rev over 200 steps x 16 microsteps.
    MM_PER_USTEP = 40.0 / (200 * 16)

    class SteppedAxis(AssemblyNode):
        motor = Driver(default=800, range=(0, 100), unit='ustep', dtype=int,
                       scale=MM_PER_USTEP)

The driver's *value* is native (800 microsteps); its `range` and every
instruction target are *design* units (millimetres of travel), scaled
once by `scale`. An integer-typed driver ramps integer-exactly and
lands exactly on its target — no accumulated floating-point drift.

Two instances of one class
==========================

The plotter holds two instances of `Axis`, and the machine declares
its instructions at the top:

.. code-block:: python

    from solid_node.simulation import Driver, Instruction

    class Plotter(AssemblyNode):
        """The machine: two instances of one Axis, and its instructions."""

        instructions = {
            'Home': Instruction({'x_axis.position': 0.0,
                                 'y_axis.position': 0.0}, duration=2.0),
            'Center': Instruction({'x_axis.position': TRAVEL / 2,
                                   'y_axis.position': TRAVEL / 2}, duration=1.5),
        }

        def __init__(self, *args, **kwargs):
            self.bed = Bed()
            self.x_axis = Axis()
            self.y_axis = Axis()
            super().__init__(*args, **kwargs)

        def render(self):
            self.bed.translate([0, 0, -3])
            self.x_axis.translate([0, -110, 8])
            self.y_axis.rotate(90, [0, 0, 1])
            self.y_axis.translate([110, 0, 8])
            return [self.bed, self.x_axis, self.y_axis]

`position` is a class-local name, so the two instances would collide in
any flat namespace that has to address a driver. They never do: a
driver's public identity is its **instance-qualified id**, the dotted
path of the attribute names its parents gave it — ``x_axis.position``,
``y_axis.position``. That id is one string by construction, and the
same string everywhere it appears: in the published document's driver
table, in an instruction's targets above, in a simulation's state, and
in `set_state`. A tree that cannot be qualified — say, axes held in a
list, whose derived names like ``axes-0`` are not legal identifiers —
fails loudly instead of silently sharing one value between siblings.

Setting state from Python
=========================

`set_state` binds named driver values for one instant, propagating
them down the tree:

.. code-block:: python

    plotter.set_state(**{'x_axis.position': 40.0, 'y_axis.position': 120.0})

A dotted id is passed as a mapping because it is not a Python
identifier, and it reaches only that instance's subtree. A bare name
(``set_state(position=40.0)``) propagates flat and is exactly right
while only one driver in the tree bears the name; the moment two do,
binding fails naming both qualified ids. Entries **merge** into the
current snapshot rather than replacing it — `set_keyframe(t)` is
`set_state` with the single global entry ``time``, and
`clear_keyframe()` releases the tree back to symbolic expressions (see
:doc:`Animating with time <animation>`). A name that no declaration
backs is rejected on the spot, listing what is declared.

Under a root declaring `Time.running()`, and only there, a bound name
may instead be the qualified id of a JOINT COORDINATE the tree
publishes — ``set_state(**{'first.turn': 12.0})``,
``set_state(**{'chassis.pose.roll': 3.0})``. The entry is delivered to
the node that owns the coordinate, a leaf included, and bound through the
same path an assignment takes, so the joint's declared range and its
placement apply exactly as they always do. That is how a running
simulation binds its bank; a hand binding is not a run, so a coordinate a
relation drives is still re-solved by that relation on the render that
follows.

Ports: how parts talk
=====================

A driver is an *input to the machine*. A **port** is a connection
point *between parts*: a unit-tagged value slot a node declares, that
its parent binds on every `simulate()` with `connect()`. Ports come
from ``solid_node.motion.ports``, the module that answers what moves and
what drives what:

.. code-block:: python

    from solid_node.motion.ports import TranslationalPort

    class SteppedAxis(AssemblyNode):
        motor = Driver(default=800, range=(0, 100), unit='ustep', dtype=int,
                       scale=MM_PER_USTEP)
        position = TranslationalPort(unit='mm', scale=MM_PER_USTEP)

        def simulate(self):
            self.connect(self.motor, self.position)
            self.carriage.translate([self.position.value, 0, 0])
            ...

Ports are domain-typed — `RotationalPort`, `TranslationalPort`,
`SignalPort` — and carry a unit and an optional scale, so the
conversion from a source's units to the sink's is declared once
instead of sprinkled through expressions. `connect(source, sink)` is
causal: the source expression flows into the sink, immediately, every
`simulate()`. Ports are also how a :ref:`flexible part <flexible-parts>`
gets its shape — the chain is *driver → port → geometry* — and a
port-bound value is deliberately **not** part of a part's build
identity, so driving a machine never mints new cached artifacts.

Joints: where a part may move
=============================

A port carries a value; a **joint** says *where a body may move*, next
to the body, once. The three one-coordinate declarations come from
``solid_node.motion.joints``:

.. code-block:: python

    from solid_node.motion.joints import Prismatic, Revolute

    class Forearm(AssemblyNode):
        elbow = Revolute(axis=(0, 1, 0), at=(0, 0, 81.5),
                         range=(-135, 135), unit='deg')

    class Carriage(Solid2Node):
        travel = Prismatic(axis=(1, 0, 0), range=(0, 200), unit='mm')

**A joint is stated in the frame of whoever declares it, and there are
two declarers.** Written in a class body, as above, it is the body's own
statement about itself, so `axis` and `at` are read in that body's
**own** frame — the frame its own `render()` states its geometry in, one
rest placement away from wherever its parent puts it. This is MuJoCo's
rule, where a `<joint pos>` is a point of the body frame. `at` defaults
to the body's own origin, which is the case of a wheel turning on its
own bearing; `range` is a `(lo, hi)` pair in `unit`. The other half —
a joint passed as a keyword where a parent DECLARES a child, read in the
PARENT's frame instead — is its own section below, "A joint stated where
the child is placed". Each component may be a number, a declared
parameter, or a formula over them, and the whole argument may instead
be a callable of the realized node — for a position that comes out of a
library object your node builds rather than out of a formula. They are
resolved once, when the node is realized, and a joint argument never
enters a part's build identity.

A joint owns exactly **one coordinate, and that coordinate is a port**.
Reading the joint on an instance gives that port slot; assigning to it
binds through the same path `connect()` uses, and `declared_ports`
reports it under the joint's name, so anything that enumerates a node's
connection points sees a joint without knowing what a joint is.

**Binding the joint moves the body.** The parent binds it in
`simulate()`, and the framework composes the motion onto the node's rest
placement:

.. code-block:: python

    class Arm(AssemblyNode):
        angle = Driver(default=0.0, unit='deg')

        forearm = Forearm()

        def render(self):
            self.forearm.rotate(90, [1, 0, 0])
            self.forearm.translate([0, 241.5, 68])

        def simulate(self):
            self.forearm.elbow = self.angle

This is the case worth reading twice: the elbow does **not** run through
the forearm's own origin — it is 81.5 mm up the arm, along the axis the
forearm's own frame calls `[0, 1, 0]` — so turning the part about its
own z would be wrong, and nothing here needs to know that the parent
also turns the forearm 90° and moves it out along its own arm to place
it. The declaration already says exactly what the framework applies:
`translate([0, 0, -81.5])`, `rotate(angle, [0, 1, 0])`,
`translate([0, 0, 81.5])`, composed innermost, before the rest placement
`render()` applied. That is the arithmetic every robot arm in the wild
writes by hand to carry a parent-frame pivot into a part's own
coordinates — a project that states the joint in the body's own frame
in the first place has nothing left to carry. When the line does run
through the node's own origin the two centring translations disappear
and one rotation is left.

**A joint's coordinate is cleared with the motion it caused.** The value
and the operations are two halves of one binding, and the framework
drops them together: at the start of an assembly's phase, before its
own `simulate()` runs, every coordinate that assembly bound during its
PREVIOUS phase is cleared — the author's own binding included, not only
a relation's. A rest-default guard, written as ``if joint.value is
None: joint.value = default``, therefore finds the coordinate unbound on
every run and rebinds and re-places the body every time, rather than
standing correctly on the first enumeration and then at rest, from the
second one on, while the coordinate still reports the first run's
number. A binding made outside any phase — in ``__init__``, in a test,
through a bare ``render()`` no walker drove — is never recorded and
never cleared, exactly as an operation applied outside a phase is never
swept.

The operations are ordinary rotations and translations, so a symbolic
binding publishes a symbolic angle and the viewer evaluates it exactly
as it evaluates any other expression. A binding outside a declared
`range` is refused by name, with the node, the joint, the value and the
range; a symbolic binding is not checked, because its value is not known
at bind time. Nothing here is deprecated: a project that turns its parts
by hand in `simulate()` keeps working, and both forms may sit on one
node.

**Either bound may be open, or an expression over the coordinate
itself.** `None` as a bound means unbounded on that side, so
`range=(0, None)` states a coordinate that may not go below zero and may
go as far above it as the mechanism takes it. A bound given as a
**callable of one argument** states itself as an expression over the
joint's own coordinate, written in ``solid_node.math``:

.. code-block:: python

    class InputArbor(AssemblyNode):
        turn = Revolute(axis=(1, 0, 0),
                        range=(lambda turn: 36 * floor(turn / 36), None))

That is a ten-tooth ratchet: the lower bound is the last seated tooth
and there is no upper one, because forward rotation is free. The bound
is applied where it is USED — at the value being bound, so the same
declaration poses at any angle, and once per tick from the committed
bank under a running root, where it becomes a physical stop
(:ref:`scenarios <scenarios>`). A bound that is not satisfied at its own
argument — `lambda turn: turn + 1` — forbids every value, and the first
binding says so by name. A callable given as the WHOLE `range`, called
with the realized declarer and returning two numbers, keeps its own
meaning: the two forms are told apart by position, not by arity.

**A body may have more than one freedom, and the class says how they
stack.** The joints declared on one class compose in **declaration
order**, innermost first: the first declared is applied closest to the
body, the last declared is outermost, whatever order their coordinates
happen to be bound in — by hand, by a wiring, or by relations solved in
an order the class body does not show. So a class read from top to
bottom reads the machine from the body outward::

    class Chassis(AssemblyNode):
        roll  = Revolute(axis=(1, 0, 0), unit='deg')   # innermost
        pitch = Revolute(axis=(0, 1, 0), unit='deg')
        yaw   = Revolute(axis=(0, 0, 1), unit='deg')
        lift  = Prismatic(axis=(0, 0, 1), unit='mm')   # outermost

Base-class joints come before a subclass's, and a subclass redeclaring
an inherited joint keeps the position the base gave it. If a body's
freedoms stack the wrong way round, reorder the declarations — there is
no ordering keyword, because the declarations already are the order.
A joint's axis and anchor are never carried through anything — not the
node's rest placement, and not a sibling joint's motion — so every
joint's line is the line its OWN declaration stated whatever the body's
rest placement or its other freedoms are doing.

Hand-written motion on the same node composes **outside the whole joint
block**, keeping its call order among itself: the joints first,
innermost, then every `rotate()`/`translate()` the `simulate()` applied,
then the node's rest placement.

**A body its parent rotates carries its joint line with it.** Because
the axis is the body's own rather than the parent's, a shared or
catalogue class can be placed at several sites, or at several
attitudes, and state one declaration that is right everywhere:

.. code-block:: python

    class Pinion(Solid2Node):
        turn = Revolute(axis=(0, 0, 1), unit='deg')   # its own bearing

    class Gearbox(AssemblyNode):
        pinions = Pinion().repeat(4)

        def render(self):
            for pinion, placement in zip(self.pinions, MOUNTING_POINTS):
                pinion.rotate(placement.tilt, placement.axis)
                pinion.translate(placement.point)

Each of the four copies spins about the line through its own placed
origin, whatever attitude its own `render()` gave it, and none of them
needed an anchor its class could not know. This is the trade a
parent-frame reading cannot offer: a body placed at one site states an
anchor that is right there and wrong everywhere else, which is why the
catalogue's shared parts — pinions, pulleys, screws, gears — so often
turned by hand instead of by a declared joint.

A body that is carried without turning
--------------------------------------

A cycloidal disk rides an eccentric: its centre travels a small circle
about the drive axis while the disk itself turns slowly on that moving
centre. The travelling part is not a rotation of the body — the disk's
attitude is set by its own spin alone — and ``Orbit`` is the joint for
it:

.. code-block:: python

    from solid_node.motion.joints import Orbit, Revolute

    class CycloidalDisk(Solid2Node):
        spin  = Revolute(axis=(0, 0, 1), unit='deg')   # innermost: its own centre
        orbit = Orbit(axis=(0, 0, 1), unit='deg')      # outermost: the drive axis

    class Drive(AssemblyNode):
        shaft = EccentricShaft()
        disk = CycloidalDisk()

        shaft.turn.drives(disk.orbit)
        shaft.turn.drives(disk.spin, ratio=-1.0 / REDUCTION)

`axis` and `at` mean exactly what they mean on a ``Revolute`` — a
direction and a point on the line, in the disk's own frame. What
travels round that line is `carries`, a point of the body in the same
frame, which defaults to `(0, 0, 0)` — the disk's own origin, wherever
its parent places it — so the declaration above needs no further
argument. Name `carries` when the point that travels is not the body's
origin — the connecting rod's big-end bore, the knee pivot of a
parallelogram leg.

`spin` is declared first, so it composes innermost: the disk turns on
its own centre and the orbit then carries that turning disk round the
drive axis. The eccentric radius and the starting phase of the circle
are **never typed**. They are consequences of the carried point and the
line, and the framework derives them, which matters more than it sounds:
a project whose bore centres are measured off an imported document can
state the joint without ever writing one of those numbers as a literal,
and a number nobody types is a number nobody can get wrong. A carried
point that lies ON the line derives a radius of zero — the body would
not move — and is refused by name at the first binding.

A body that floats
------------------

A walking robot's chassis has no parent to be jointed to. It stands
where its legs put it: six freedoms against the ground, of which a
hexapod uses four. ``Free`` is one declaration for all six:

.. code-block:: python

    from solid_node.motion.joints import Free

    class Chassis(AssemblyNode):
        pose = Free(angle_unit='deg', length_unit='mm')

        body = Body()
        legs = Leg().repeat(6)

    class Spiderbot(AssemblyNode):
        chassis = Chassis()

        def simulate(self):
            self.chassis.pose.roll = self.roll
            self.chassis.pose.pitch = self.pitch
            self.chassis.pose.yaw = self.yaw
            self.chassis.pose.z = self.height

The joint owns **six coordinates** — `roll`, `pitch` and `yaw` in
`angle_unit`, and `x`, `y` and `z` in `length_unit` — and each of them is
an ordinary coordinate: bind it by assignment, name it at either end of
`drives`, read it from a driver or an expression. Where it differs is the
NAME. A joint owning one coordinate names it after the joint, so a
``Revolute`` called `turn` has a coordinate called `turn`; a joint owning
several names each one `<joint>.<coordinate>`, so the six above are
`pose.roll`, `pose.pitch`, `pose.yaw`, `pose.x`, `pose.y` and `pose.z`.
That is the name the port enumerator reports, the name a relation path
ends with — `tilt.drives(chassis.pose.pitch)` — and the only spelling
there is. It is not a Python identifier, so it is not a wiring keyword:
a coordinate of such a joint is bound by assignment or by a relation, and
both wiring forms are refused where they are written.

**The composition is fixed by the joint**, innermost first::

    R(roll, x̂) · R(pitch, ŷ) · R(yaw, ẑ) · T(x, y, z)

— the roll closest to the body and the translation outermost, about the
point `at` names in the body's own frame. The three directions are that
frame's own — literally `(1, 0, 0)`, `(0, 1, 0)`, `(0, 0, 1)` — so the
angles are read the way an aircraft's are; and because the translation
is the OUTERMOST operation, it displaces along those same fixed
directions rather than along whatever the roll, pitch and yaw have just
turned the body to. There is no ordering argument: unlike three separate ``Revolute``\ s,
whose order you choose by declaring them, a free joint is one thing and
its internal order is part of what it means.

The hexapod above binds four of the six and leaves `pose.x` and `pose.y`
alone. **An unbound coordinate places nothing** — no rotation, a plain
zero offset — while still reading as unbound, so
`chassis.pose.x.value` is `None` and the enumerator still reports the
port. Binding any one of the six re-places the whole joint from whatever
the six then hold, so the order you bind them in never shows.

A ``Free`` takes no `axis` — a free body turns about three directions,
and they are the frame's own — and no `range`, because a floating body
has no travel to bound. Three angles gimbal-lock at `pitch = ±90°`; that
is inherited from stating an attitude as three angles at all, and it is
what the hexapod's own hand-written composition does today.

A joint stated where the child is placed
-----------------------------------------

A body is not always entitled to state its own joint: a bought bearing
or a fastener knows nothing about the assembly it ends up in, and a
class built only to hold one declaration is a class that should not
exist. A joint passed as a **keyword** where a parent DECLARES a child
is the other half of the frame rule — the parent's own statement about a
child it is placing, read in the parent's frame, URDF's rule:

.. code-block:: python

    from solid_node.motion.joints import Revolute

    class Rack(AssemblyNode):
        screw = ZScrew(turn=Revolute(axis=(0, 0, 1), unit='deg'))

`axis` and `at` are read in the DECLARING PARENT's own frame this time —
`Rack`'s, not `ZScrew`'s — and `at` defaults to `(0, 0, 0)`, the
**parent's** own origin. That is the sentence a reader gets wrong:
**a child the parent TRANSLATES swings about the parent's origin, not
its own**, unless `at` names the child's own placement. That is not a
hazard, it is the whole point — it is what lets a joint be written with
no anchor at all where the parent's own origin already is the line a
shared catalogue part turns on, exactly the case a class-body joint
cannot state because the class does not know where it will be placed:

.. code-block:: python

    class MotorDrive(AssemblyNode):
        shaft_pin = MotorShaft()
        gear = SmallGear()
        # GearLockScrew is a shared catalogue No2SelfTapScrew: it knows
        # nothing about the motor shaft it locks the gear to, and the
        # shaft axis IS this drive's own origin.
        gear_screws = GearLockScrew(
            orbit=Revolute(axis=(0, 0, 1), unit='deg')).repeat(2)

One declaration, two copies, no anchor, no sign, no index: a joint may
be passed to a `.repeat()` exactly as a plain keyword can, and it is
declared **once** — the arguments resolve once, against the SAME
declaring parent, so every copy gets the same numbers, and what differs
per copy is where each one's own rest placement carries that one line
to. A relation may still name the coordinate through the repeat, exactly
as it names a class-declared one:
`eccentric_shaft.spin.drives(eccentric_bearings.orbit)`.

An ``Orbit``'s `carries` keeps the exception it already has: WRITTEN at
a site it is a point of the declaring parent's frame, like `at`; left
DEFAULTED it is still the CHILD's own origin, never the parent's —
naming the point that travels round the line is a statement about the
body, not about where the site sees it:

.. code-block:: python

    class CycloidalDrive(AssemblyNode):
        # Both `at` and `carries` defaulted: the drive axis (the
        # PARENT's own origin) and the disk's own bore centre (the
        # CHILD's own origin) -- two different defaults, on purpose, so
        # the two points do not collapse onto the line and the derived
        # radius is never zero.
        disk = CycloidalDisk(orbit=Orbit(axis=(0, 0, 1), unit='deg'))

Defaulting `carries` to the parent's origin too — following `at` — would
name a point that is not of the body at all, and with `at` also
defaulted the two would always coincide, refusing every such joint at
the first binding for a radius of zero. When the point that travels IS
off the body's own centre in a way the site's own frame can name more
directly than the body's, write it there instead:
`carries=DISK_BORE_CENTRE`, the assembly's own already-derived point.

**The two forms are told apart by the VALUE at the keyword, never by
where the code sits.** A coordinate the DECLARING class already owns —
a port, or a joint that class declares — is a wiring, exactly as before;
a fresh `Revolute(...)`/`Orbit(...)`/`Free(...)`, built right there in
the argument list and belonging to no class yet, is a site declaration.
A site joint of a name the child's class already declares REPLACES that
declaration whole — its axis, its anchor, its unit, its range — and
keeps that name's slot in the composition order; a site joint of a NEW
name is appended after every class-declared joint, in the order the
keywords were written. Neither is a parameter: the keyword never reaches
the child's constructor, so it is invisible to the child's identity —
two children of one class differing only in the joints their sites
passed still key one printed artifact. Refused by name at class
definition: a keyword naming a port, a parameter, or any other attribute
the child already answers to; a joint declared on some third class,
neither the parent nor the child; two things landing on one coordinate.

The one thing a site joint costs that a class-declared one does not: its
operations are carried through the inverse of the child's own rest
placement before they are applied (the arithmetic that carries a
parent-frame pivot into a part's own coordinates, restored for this one
case), so a body whose rest placement carries a value the framework
cannot evaluate numerically refuses a SITE-declared joint — naming the
node, the joint and the operation — where a class-declared one on the
same body would not.

Passing a coordinate down
-------------------------

Several parts often turn as one body. Hand the child the parent's
coordinate in the class body, by naming a port or joint the child
declares:

.. code-block:: python

    class Arbor(AssemblyNode):
        index = Count(0, min=0)

        turn = Revolute(axis=(0, 0, 1), unit='deg')

        wheel = Wheel(turn=turn)
        pinion = Pinion(turn=turn)

That keyword is a **wiring**, not a parameter: it says which value
reaches the child at each instant, never what geometry is built, so it
is absent from the child's parameters and from its identity — two arbors
turning differently are still one printed wheel. The framework rebinds
it from the parent's end after every `simulate()` of the parent, applying
the child end's declared scale as any binding does. A wiring the child
cannot receive fails at class definition, naming both classes; an
unbound source fails when it is bound; and a wired coordinate has exactly
one binder, so binding the child's end by hand in the declaring parent is
refused rather than silently overwritten.

Relations: one coordinate drives another
========================================

A joint says where a body may move; a **relation** says that one
coordinate's motion *is* another's. It is written as a statement in a
class body, and it needs no import:

.. code-block:: python

    class Movement(AssemblyNode):
        power  = TrainArbor(index=0)
        centre = TrainArbor(index=1)
        escape = TrainArbor(index=2)

        power.drives(centre, law=going_train)
        centre.drives(escape, law=going_train)

        def simulate(self):
            self.escape.turn = escape_angle(self.time)

Either end may be a port, a joint, a **child declaration** — which
stands for its class's one joint, as ``power`` and ``centre`` do above —
a **path** through declared children, a **derived coordinate**, or, as
the source only, a ``Driver``:

.. code-block:: python

    anchor.turn.drives(pendulum.swing)
    centre.turn.drives(motion_works.cannon.turn, offset=hand_setting)
    elbow_pulley.turn.drives(elbow_belt.travel, ratio=PITCH_ARC)
    art3.drives(shoulder.art2.art3.elbow)          # a root Driver

Reading a port, a joint or another child off a declaration is what makes
a path: ``shoulder.art2.art3.wrist`` names a place in the tree, checked
against the classes where you write it, so a misspelt segment is a
class-definition error rather than a mystery at runtime. Reading a
declared *parameter* off a declaration is still refused — a parameter is
a value, and a class body has none. A ``Driver`` may drive, but nothing
may drive a ``Driver``: its value belongs to the bound snapshot.

**Direction is mechanical; solving is not.** ``a.drives(b)`` says what
turns what. Which way the framework *solves* it is decided on every run,
from whichever end is bound at that instant: forward through the law
when the driver end is bound, backward through its inverse when the
driven one is. The train above is written power-first and solved
escape-first, because that is the end ``simulate()`` bound, and nothing
had to be reordered to make it so. Every relation of a class is
ATTEMPTED at the end of that instance's simulate phase, so a relation
stated on an ancestor and reaching a coordinate by path binds it before
the descendant's own relations run.

What one instance's own attempt cannot reach is not refused on the
spot: it is held until every assembly in the tree has had its own
phase, and only then resolved or refused. This is what lets the going
train above be split exactly where the machine is — the chain stated
inside ``Train``, the movement only binding the escapement two levels
away::

    class Train(AssemblyNode):
        centre = TrainArbor(index=1)
        third  = TrainArbor(index=2)
        escape = TrainArbor(index=3)

        centre.drives(third, law=going_train)
        third.drives(escape, law=going_train)

    class Movement(AssemblyNode):
        power = TrainArbor(index=0)
        train = Train()

        power.drives(train.centre, law=going_train)

        def simulate(self):
            self.train.escape.turn = escape_angle(self.time)

``Movement``'s own relation cannot resolve during ``Movement``'s own
phase — ``train.centre`` is not bound until ``Train``'s own relations
have solved, and those have not run yet. It is deferred, resolved once
``Train``'s phase completes, and never refused: reading a coordinate a
relation, a derived formula or a wiring is going to bind is refused, not
finding it unbound at the point something reaches it late. The same rule
also means a class no longer reads its own derived coordinate, or a
joint its own relation drives, as a silent empty slot inside its own
``simulate()``: that read is now refused by name, naming the coordinate,
the binder and the two-phase order — *unless* the same class's
``simulate()`` binds it there itself, which is the ordinary rest-default
guard (``if self.coordinate.value is None: self.coordinate = default``)
and stays exactly as unremarkable as it always was.

A ``DoublyBound`` coordinate is the one thing never deferred: it is a
contradiction, not a question of timing, and is refused in the instance
whose attempt found it, immediately.

A subclass may now REPLACE a base's named relation, keeping its
position in the solve::

    class Actuator(AssemblyNode):
        drive = input_angle.drives(rotor.spin, ratio=8.0)

    class Preview(Actuator):
        drive = free_run.drives(Actuator.rotor.spin, ratio=1.0)

``Preview`` enumerates one ``drive``, the replacing one, at the position
the base's held; ``Actuator`` is untouched, and an instance of it still
solves its own. A relation with no name, or a name no base used, stays
additive, as it always was.

Finally, a coordinate is cleared with the motion it caused: at the start
of an assembly's phase, the framework drops the value and binder of
every coordinate that assembly bound during its PREVIOUS phase — the
author's own ``simulate()`` included. A rest-default guard therefore
rebinds and re-places its body on every run rather than standing, from
the second run on, at a stale number with no operation left to show for
it.

The law
-------

``ratio=`` and ``offset=`` are the shorthand for ``Affine``, the one new
name to import when you want it explicitly::

    from solid_node.motion.couplings import Affine

    Affine(ratio, offset)   # driven = ratio * driver + offset

Both faces are ordinary arithmetic, so a symbolic driver read or ``$t``
produces an expression and a number produces a number, and it inverts
itself: you never write the reverse reading.

Anything else is a ``law=`` **callable of your own**, called once per
realized parent with the two realized nodes that own the coordinates,
driver first, and returning the law:

.. code-block:: python

    def going_train(driver, driven):
        return Affine(ratio=-driver.wheel_teeth / driven.pinion_teeth,
                      offset=registration(driver, driven))

Because it is handed the realized nodes, it reads whatever they have —
a built library object, an index, a resolved parameter. The framework
looks nothing up: there is no hook on your class, no registry of
mechanism shapes, and no vocabulary of gears. A returned object needs a
``forward(x)``, and an ``inverse(y)`` if the relation may ever be read
backwards; a plain function is taken as forward-only.

A relation over a repeated child
---------------------------------

A relation whose DRIVEN end reaches through a ``.repeat()``\ ed child is
a **broadcast**: one relation, written once, resolving to one relation
per realized copy. An abacus column used to bind its four beads by
hand::

    def simulate(self):
        for index, bead in enumerate(self.earth_beads):
            bead.travel = earth_lift(self.earth.value, index, self.stroke)

One relation, with a per-copy ``law=``, replaces the loop::

    earth.drives(earth_beads.travel, law=earth_lift)

    def earth_lift(column, bead):
        rank = bead.index          # the copy's own 0-based position
        return lambda level: clamp(level, rank) * column.stroke

``law=`` is called once per **copy**, at realization, with the copy as
its second argument, instead of once per instance — the copy's own
``index`` is what a per-copy sign, phase or rank reads, with no change
to the callable's two-argument signature and nothing new for the
framework to inspect. ``ratio=``/``offset=`` still work, resolved once
against the declaring instance and shared, as the same ``Affine``, by
every copy: a ratio names a value of the declaring class and has no way
to see a copy.

Every copy a repeat realizes carries its own ``index``, a plain 0-based
attribute — not a declared parameter, and no part of the part's
identity or its cached artifact.

A repeated end is a driven end only. Named as the SOURCE —
``beads.travel.drives(x)``, ``beads.drives(x)``, or reached through a
path one level down — it is refused at class definition, naming the
path as written, the repeated declaration and its class: a relation's
source is one value, and the copies hold one each. Bound already, a
broadcast is never read backwards, whatever its law offers: the n
copies would have to agree on one source value, and the framework does
not compare values to decide that.

Several coordinates at one end
-------------------------------

A mechanism often reads several coordinates and moves several. A delta
printer's rod has four freedoms from three drivers; a Pascaline's pawl
deflects from two drums at once::

    def simulate(self):
        count, next_count = self.count.value, self.next_count.value or 0
        theta = drum_angle(count)
        self.sautoir.pawl.swing = PAWL_DEFLECTION * (
            climbing(theta) + ratchet(next_count) * (1 - pushing(theta)))

One relation replaces the hand binding, with a group of sources joined
by ``&``::

    (count & next_count).drives(sautoir.pawl.swing, law=pawl_deflection)

    def pawl_deflection(sources, driven):
        position = sources[0]
        def law(count, next_count):
            theta = drum_angle(count)
            return PAWL_DEFLECTION * (climbing(theta)
                                      + ratchet(next_count) * (1 - pushing(theta)))
        return law

``&`` joins coordinates into a group, free on every declaration that
carries ``drives``, chaining flat — ``x & y & z`` is one group of three,
never a nested pair. It is the source-side spelling because the
ratified sentence for a source group, ``(count, next_count).drives(...)``,
is not Python: a tuple display has no ``drives`` and, being an immutable
built-in type, cannot be given one. The DRIVEN side accepts either
spelling — a tuple, exactly as written above for a single end, or
``&`` — because a tuple written as an argument reaches the framework
intact::

    (x & y & z).drives((rod.spin, rod.lean, rod.swing, rod.rise), law=delta_rod)
    (x & y & z).drives(towers.height, law=delta_carriage_law)   # several sources, one driven end

A group names at least two coordinates, none of them twice, none of
them a term of a derived coordinate, and none of them named on both
sides of one relation naming several ends. A driven group that fans out
over a ``.repeat()`` — every member a broadcast of the SAME repeated
segment — resolves to one record per copy holding that copy's several
driven ends, the law called once per copy exactly as a single-coordinate
broadcast is.

**The law's two arguments are shaped by the sentence, not spread by the
end.** A side naming one coordinate hands that coordinate's realized
OWNER, exactly as a one-to-one relation always has; a side naming
several hands the TUPLE of their owners, in the order written — so a
six-source law still takes two arguments, never eight. ``forward`` is
called with one positional argument per SOURCE, in written order — the
mechanism's own function of its own inputs — and returns the driven
value itself for one driven end, or a SEQUENCE of exactly as many
values, in written order, for several. A return with no length, that is
text, or of the wrong length is refused by name at the moment it is
applied, naming the relation, the law, the driven ends as written and
what came back — because a value slot takes whatever is put into it,
and a wrong-shaped return would be a pose nobody stated.

**A relation naming several coordinates at either end is read FORWARD
ONLY**, whatever its law offers, for the reason a broadcast is: n
sources cannot be recovered from m driven values without comparing or
solving values, which the framework does not do. ``ratio=``/``offset=``
and the bare default law are refused with a group on either side: an
affine law relates one value to one value, so a relation naming several
ends always carries a ``law=``.

**Guidance:** if the combination is LINEAR, write a derived coordinate
and keep both directions; if it is not, write a ``law=`` over several
sources and lose the reverse. A square root, a trigonometric function, or
any other non-linear combination of several coordinates is the second
kind — a delta printer's carriage height and a flexure stage's leg lean
both are. Two symbolic rules already true of a one-source law stay true
here: ``forward`` may not BRANCH on its arguments' values (a symbolic
value is not comparable), and a non-linear function of a symbolic value
must come from ``solid_node.math`` so it emits an OpenSCAD call.

Derived coordinates
-------------------

A linear formula over coordinates is itself a coordinate of the class:

.. code-block:: python

    class Art2(AssemblyNode):
        shoulder = Revolute(axis=(0, 0, 1), unit='deg')
        art3     = Art3()

        relative_elbow = art3.elbow - shoulder     # the belt is anchored
        relative_elbow.drives(elbow_pulley.turn)   # on the housing

    class Art56(AssemblyNode):
        wrist = Revolute(axis=(0, 0, 1), unit='deg')
        tool  = Revolute(axis=(0, 1, 0), unit='deg')

        left  = wrist + 2 * tool
        right = wrist - 2 * tool

``+``, ``-``, unary ``-`` and scaling by a number or a declared
parameter are all it does; a product of two coordinates, or any other
function of one, is refused where it is written and pointed at ``law=``.
The result reads on an instance as a bound port slot, is reported by
``declared_ports`` under its name, takes its domain and unit from its
terms, and solves in both directions: from its terms when they are all
bound, and for its one remaining term when it is bound itself.

When it refuses
---------------

Solving refuses by name rather than posing a machine it cannot justify.
Each of the four is its own error kind in
``solid_node.motion.couplings``, and each message names the node paths,
the relation as written and the ends:

``UnreachedCoordinate``
    nothing bound either end of a relation, and nothing reached it —
    or a derived coordinate is bound while two of its terms are not.

``DoublyBound``
    something else already bound the coordinate this relation would
    bind: your own ``simulate()``, a wiring, or another relation. Two
    relations that would give the *same* value are refused too — the
    framework cannot compare two symbolic expressions to decide whether
    they agree, and a silent first-writer-wins would hide a real
    modelling mistake.

``NotInvertible``
    the driven end is the bound one, so the law has to be read
    backwards, and it offers no inverse.

``PrematureRead``
    your own ``simulate()`` read a coordinate that a relation, a derived
    coordinate or a wiring of your own class bound only afterwards, so
    the value it read was not this run's; the message names the read's
    source location and the binder. A read whose value your own
    ``simulate()`` binds itself is the ordinary rest default and is not
    refused.

Wirings take part in the same solve, so passing a coordinate down from a
coordinate a relation solves works without ordering anything by hand;
and at the start of each run the framework clears what was bound during
the previous run — through a wiring, a relation, or your own
``simulate()`` alike — so every instant re-solves from fresh bindings and
a rest default written as ``if self.turn.value is None: self.turn = 0``
applies again on every run. A value bound outside any run, before the
first ``render()``, is not cleared.

Instructions
============

An `Instruction` names driver targets in design units plus a duration:
``Instruction({'x_axis.position': 0.0}, duration=2.0)``. Declared in an
``instructions`` dict on an assembly class, it becomes a button in the
viewer and a `trigger()` in simulations and in the embedding API.
Triggering one ramps every target from its current value to the named
value over the duration, landing exactly on target; triggering another
while one runs replaces the active ramp.

An instruction may state travel instead of a landing place:
``Instruction(by={'crank': 10.0}, duration=0.5)`` advances the crank ten
degrees from wherever it stands, which is what "advance one step" means
on a machine that is operated rather than positioned. Exactly one of
``targets`` and ``by`` is stated; both, or neither, is refused at
declaration. A relative instruction ramps relatively under every time
base, and under a root declaring `Time.running()` it becomes a relative
move on the run (see :doc:`Simulating and testing scenarios
<scenarios>`). It is not published in the document's instructions table
yet, so it drives a scenario rather than a viewer button.

Declare machine-level moves on the machine, not on its parts: `Home`
above belongs to the `Plotter`, because homing is something the whole
machine does.

Driving it in the viewer
========================

Here is the plotter. Press `Center` or `Home`, and use the breadcrumb
to step into an axis and drag its slider:

.. solid-node:: _exports/two_axis_plotter
   :height: 480px

The controls are scoped by assembly layer, strictly:

* One **button per instruction** and one **slider per driver**
  declared at the focused layer, labelled relative to that layer and
  shown in design units with a numeric readout.
* A **breadcrumb** walks focus down into subassemblies that declare
  controls, and back up. At the top you see the plotter's two buttons
  and no sliders — `position` belongs to the axes. Focus `x_axis` and
  you get its slider.
* A root that declares nothing shows no controls, even when its
  children declare plenty. That strictness is deliberate pressure: if
  a move belongs to the machine, declare it on the machine.

A document with no drivers looks exactly as it did before drivers
existed, and a host embedding the widget can suppress the chrome
entirely with ``driverControls: 'none'`` and build its own UI on the
:doc:`programmatic API <embedding>`.

Dragging one driver does not recompute the world: which operations
re-evaluate is decided by the free variables of each parsed
expression, so only geometry that actually reads ``x_axis.position``
moves when you drag it. `$t` still works alongside drivers — one
expression may mix the two — and the timeline transport keeps driving
`self.time` as before.

Stepping instead of dragging
============================

Sliders answer "what does this pose look like". The questions that
follow — does the carriage clear the stop on the way home, how long
does the move take, what does the trajectory look like — need the
machine *stepped* deterministically in Python. That is the simulation
layer: see :doc:`Simulating and testing scenarios <scenarios>`, whose
last section covers the machine that keeps its history — a root
declaring `Time.running()`, whose simulation owns every joint coordinate,
moves it by increments, and integrates a law that jumps by locating its
crossings inside the tick and subtracting them.
