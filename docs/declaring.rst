
.. _declaring:

===================
Declaring a machine
===================

Everything in :doc:`Modeling parts <leaf-nodes>` and :doc:`Combining
parts <assemblies>` builds a node the constructor way: an ``__init__``
that takes the part's parameters, stores them on ``self`` and forwards
them to ``super().__init__()``. That works, and every project written
that way keeps working. This page is the other way: the class body
*declares* the part, and the framework derives the rest.

.. code-block:: python

    from solid_node.node import CadQueryNode
    from solid_node.parameters import Length

    class Piston(CadQueryNode):

        diameter     = Length(29.4, min=0)
        crown_height = Length(18.0, min=0)
        skirt_depth  = Length(12.0, min=0)

        total_height = crown_height + skirt_depth

        def render(self):
            return (cq.Workplane("XY")
                    .circle(self.diameter / 2)
                    .extrude(self.total_height))

Compared with the constructor form, three things are gone: the
``__init__`` signature, the ``self.x = x`` lines, and the
``super().__init__(x=x, ...)`` call. The last one mattered most. The
build identity of a node is hashed over what reaches
``super().__init__()``, so forgetting one keyword there silently gave two
different parts one cached artifact. Here the framework owns the
identity: it is the class plus the resolved values of every declared
parameter, complete by construction.

Inside ``render()`` nothing changed. ``self.diameter`` is a plain float,
``self.total_height`` too. Declarations exist only in the class body;
by the time any ``render()`` runs, every parameter is a number.

The three layers of a value
===========================

Every value a node uses is one of three things:

.. list-table::
   :header-rows: 1

   * - layer
     - says
     - lives
     - example
   * - parameter
     - what is built
     - the declaration; propagates to children
     - ``bore = Length(30.0)``
   * - constant
     - where it sits
     - bare Python, read in ``render()``
     - ``BANK_HALF = 45.0``
   * - port
     - how it runs
     - the declaration; driven at runtime
     - ``crank = RotationalPort()``

The rule that separates the first two is the wrapper: **wrapped is a
parameter, bare is a constant**. A ``Length(...)`` propagates, enters the
build identity and can be set by a parent or from the command line. A
bare number in a module or class body is invisible to the framework,
because Python already provides constants. Placement arithmetic, lookup
tables and naming logic are constants and ordinary code in ``render()``,
never declarations.

Ports are the third layer and are unchanged from :doc:`Driving a machine
<driving>`, with one addition: a port can be fed by assignment.
``unit.crank = angle + phase`` binds exactly as ``self.connect(angle +
phase, unit.crank)`` does, scale applied.

One more declaration belongs to the root alone: its time base,
``time = Time(loop=<seconds>)``, which says what one turn of the animation
timeline is and makes ``self.time`` read seconds everywhere below it. See
:ref:`Declaring the time base <time-base>`.

Kinds
=====

A parameter is declared with a typed kind:

``Length``
    A linear dimension in the project's unit (millimetres). Signed by
    default, since a station can sit at ``-5.2``; ``min=0`` opts into
    non-negativity.

``Angle``
    In degrees. Its own quasi-dimension: this is what refuses
    ``phase + rotor_fraction`` and lets trigonometry demand an angle.

``Count``
    A whole number of things: teeth, cylinders, sides. Resolves to an
    ``int``, and refuses ``2.5``.

``Ratio``
    A dimensionless fraction, and what a length over a length is.

``Flag``
    A boolean selector. Outside the algebra; it gates structure through
    ``omit()`` (below).

``Scalar``
    The escape hatch: a number the algebra does not check.

Every kind, the ``Quantity`` base below and the errors a bad declaration
raises come from ``solid_node.parameters``, and nothing else does. Node
classes come from ``solid_node.node``, ports and the declared time base
from ``solid_node.motion.ports``, drivers from
``solid_node.simulation``, so a module's import block says which of its
names build the machine, which move it, and which drive it:

.. code-block:: python

    from solid_node.node import AssemblyNode, CadQueryNode
    from solid_node.parameters import Count, Flag, Length
    from solid_node.simulation import Driver

Every kind takes an optional default and, for the numeric ones, ``min=``
and ``max=``. Constraints are checked when the node is constructed, and a
violation raises naming the class, the parameter and the rule. A value
is coerced to its kind, so ``Piston(diameter=30)`` and
``Piston(diameter=30.0)`` are one part.

A declaration may omit its default:

.. code-block:: python

    class Tower(Solid2Node):
        height = Length(min=0)

A value that depends on the parent has no sensible default, and
inventing one would be a quiet mistake. The parent supplies it; if
nothing does, constructing the node raises naming the class and the
parameter. That is also what happens when ``solid develop tower.py``
loads such a node directly — state the value with ``--set height=300``
(see :ref:`root-overrides`).

Formulas and the algebra
========================

A declared parameter is a symbolic token, and a formula over tokens is a
**derived parameter**, written as a bare class-body expression:

.. code-block:: python

    class CylinderUnit(AssemblyNode):

        bore           = Length(30.0, min=0)
        wall_clearance = Length(0.3,  min=0)

        piston_diameter = bore - 2 * wall_clearance

        piston = Piston(diameter=piston_diameter)

Read on the instance, ``self.piston_diameter`` is the evaluated float. It
cannot be supplied by a parent or by assignment: it follows its inputs.

Every quantity carries a vector of dimension exponents, and arithmetic is
arithmetic on exponents. Products add them, quotients subtract them, and
addition, subtraction and negation need them equal:

* ``teeth * module`` is a length (a ``Count`` is dimensionless);
* ``bore / stroke`` is dimensionless;
* ``bore * bore`` is a length squared, a valid quantity whether or not
  a kind is named for it;
* ``bore + pressure_angle`` raises a ``DimensionError`` in the class
  body, on ``import``, before any geometry exists.

The functions of ``solid_node.math`` take part: ``sqrt`` needs even
exponents and halves them, ``sin``/``cos``/``tan`` need an ``Angle`` and
return a dimensionless quantity, and ``asin``/``acos``/``atan``/``atan2``
take dimensionless arguments and return an ``Angle``. A bevel gear layer
reads exactly as it did in a hand-written parameter file:

.. code-block:: python

    from solid_node.math import atan, cos, sqrt

    class BevelDrive(AssemblyNode):

        module = Length(2.0, min=0)
        z1 = Count(16, min=1)
        z2 = Count(32, min=1)

        pitch_angle   = atan(z1 / z2)
        cone_distance = module / 2 * sqrt(z1 * z1 + z2 * z2)
        axis_y        = cone_distance * cos(pitch_angle)

The rest of ``solid_node.math`` takes part too, and its rules follow
from the same idea. ``abs`` keeps its argument's kind; ``min`` and
``max`` need their two arguments to agree and keep that kind; ``sign``
takes anything and gives a dimensionless -1, 0 or 1, because it compares
against zero and zero belongs to every kind.

``floor`` and ``ceil`` want a **dimensionless** argument, which is worth
a sentence because it surprises people. They compare a quantity against
the whole numbers, and a whole number has no dimension — so ``floor(bore)``
would only mean something if millimetres were assumed, and assuming a
unit is exactly what this algebra will not do. Say what you are counting
in and it reads better anyway::

    steps = floor(travel / pitch)      # a dimensionless count
    landed = steps * pitch             # back to a length

The functions built out of those — ``clamp``, ``clamp01``, ``ramp``,
``lerp``, ``wrap``, ``piecewise`` and ``bump`` — carry no rule of their
own; what they do to dimensions falls out of the primitives they
compose. ``clamp(reach, low, high)`` needs its three arguments to agree
and gives back that kind; ``ramp`` gives a dimensionless fraction. One
consequence catches people once: a bound stated as a bare number against
a dimensioned quantity is refused::

    clamp01(bore)             # DimensionError: bore is L, 0.0 is not
    max(bore, 0.0)            # the same
    max(bore, Length(0.0))    # what you meant

which is the same refusal ``bore + 1`` already gives, arriving from
``min`` and ``max`` rather than from a rule written for the clamp.

``wrap`` has the same catch in its second argument: its default period is
the plain number ``360.0``, so in a declaration state the period as a
quantity too::

    wrap(bearing)                 # DimensionError: bearing is A, 360.0 is not
    wrap(bearing, Angle(360.0))   # a derived Angle

A turn about the origin needs nothing of the sort — ``turn(point, angle)``
builds no centring terms at all, so it never meets a bare zero — but an
explicit centre must be stated in the point's own kind.

The algebra is honest about its reach. It catches *dimensional*
mistakes — a wrong formula shape, a forgotten factor, mixed kinds — not
geometric ones. ``Count`` and ``Ratio`` are both dimensionless, so
``teeth + fraction`` passes. Comparisons are refused in a declaration;
they belong in ``render()``, on the resolved values. A project that
needs a kind the framework does not name subclasses ``Quantity`` with
its own exponents (``class Torque(Quantity): dimension = {'M': 1,
'L': 2, 'T': -2}``), and ``.value`` on any token or formula yields the
unchecked form when the algebra gets in the way.

Declaring children
==================

A node constructed in a class body is a **declaration**, never an
instance. A class attribute would be one object shared by every parent
instance — eight cylinder units driving one piston — so the framework
records the class and its arguments, and each parent instance realizes
its own child when it is constructed:

.. code-block:: python

    class Engine(AssemblyNode):

        count = Count(8, min=2)
        bore  = Length(30.0, min=0)

        cylinders = Cylinders(count=count, bore=bore)
        block     = BlockAssembly(count=count, bore=bore)

Tokens passed to a child are passed by reference and resolved top-down
from the root: ``Engine()`` realizes with defaults, ``Engine(bore=32.0)``
rebinds the root and every derived value and child follows. One number
moves the whole machine. Set ``count`` to 6 and the cylinders and the
block agree by construction — which is the point of declaring a shared
parameter on the common ancestor and passing it down. A ``Flag`` passes
down the same way: ``supply = PowerSupply(fitted=power_supply_fitted)``
hands the child this class's boolean, so a structural choice can be
declared on the root and reached with ``--set``. Siblings do not reach
into each other: ``ConRod(pin_bore=piston.pin_bore)`` in a class
body raises, with the advice to declare ``pin_bore`` on the parent.

A child's class need not itself be declarative. A legacy class with an
ordinary ``__init__`` is realized by calling that constructor with the
resolved arguments, so the two styles mix freely in one tree.

Children are named after the attribute holding them, exactly as in
:doc:`Names, the node tree and caching <node-tree>`; ``name=`` passes
through and always wins.

Lists and repetition
--------------------

Enumerated, different children are a plain literal list, named
``<attr>-0``, ``<attr>-1``, ...:

.. code-block:: python

    plates = [PanelLeft(width=frame_width), PanelRight(width=frame_width)]

Identical units use ``repeat(count)``:

.. code-block:: python

    STATION_PITCH = 44.0
    BANK_HALF     = 45.0
    ROD_OFFSET    = 5.2

    class Cylinders(AssemblyNode):

        count = Count(8, min=2)
        bore  = Length(30.0, min=0)

        units = CylinderUnit(bore=bore).repeat(count)

        def render(self):
            for index, unit in enumerate(self.units):
                pin = index // 2
                side = 1 if index % 2 == 0 else -1
                unit.rotate(side * BANK_HALF, [1, 0, 0])
                unit.translate([STATION_PITCH * pin - side * ROD_OFFSET, 0, 0])

``repeat`` means *identical parts*: one geometry, one build identity,
one cached artifact, ``count`` placements — a quantity line on a bill of
materials. Per-unit variation never lives in the declaration. Placement
variation is ``enumerate`` plus constants in ``render()``; drive
variation is port feeding (``unit.crank = angle + THROW_PHASES[pin]``).
Children that differ geometrically are different parts: declare them
individually or in a literal list.

Two things to know about lists:

* Indices are declared identity and never renumber. An omitted
  ``units-3`` leaves ``units-4`` as ``units-4``; renumbering would
  silently re-identify every later unit.
* A **list comprehension in a class body cannot see class-level
  names**. ``[Unit(bore=bore) for _ in range(8)]`` raises ``NameError``
  for ``bore`` — that is Python's class scoping, and the framework never
  gets a chance to say so. Identical units are ``repeat``. A
  comprehension over what it *can* see does declare: ``[Clip(kind=k)
  for k in KINDS]`` over a module-level table is an enumerated list
  like a literal one, named ``clips-0``, ``clips-1``, ...
* A driver declared on a repeated or list-held child cannot be
  qualified, because ``units-3`` is not a legal expression identifier
  (see :doc:`Names, the node tree and caching <node-tree>`). Identical
  units are driven through ports, fed from the parent's ``simulate()``.

render() that returns nothing
=============================

On a declarative internal node, ``render()`` places the parts at rest,
selects, and returns nothing. The children are then the declared
children, in declaration order, minus any it omitted:

.. code-block:: python

    class Windmill(AssemblyNode):

        overall_height  = Length(400.0, min=0)
        rotor_fraction  = Ratio(0.36, min=0, max=1)
        guard_installed = Flag(True)

        rotor_radius = overall_height * rotor_fraction

        tower = TowerBody(height=overall_height)
        rotor = Rotor(radius=rotor_radius)
        guard = Guard()

        def render(self):
            if not self.guard_installed:
                self.guard.omit()

A pure grouping node — nothing to position, nothing to omit — needs no
``render()`` at all: ``Engine`` above is complete as declared. A
``render()`` that returns a list keeps the contract described in
:doc:`Combining parts <assemblies>` to the letter, and the framework
builds exactly that list. Both forms work on assemblies and on fusions.

``omit()`` is structural absence. An omitted part is not in the machine:
different mass, different bill of materials, absent from exports, absent
from a fused solid, never built. It is not the same as hiding a part in
the viewer. Every child is always declared — the tree's vocabulary is
complete at import time — and ``render()`` selects presence.

**Structure varies with parameters, never with time.** A machine does
not gain and lose parts per frame, and the children a fusion holds are
its build identity. Decide ``omit()`` from declared parameters only, in
``render()``: calling it from ``simulate()`` raises, and a ``render()``
that reads time to decide it is the deprecated form described next.

.. _root-overrides:

Varying a design from the command line
======================================

Because the root's parameters are declared, every command that loads a
node can set them:

.. code-block:: shell

    solid build engine.py --set bore=32.0 --set count=6
    solid develop windmill.py --set guard_installed=false
    solid develop tower.py --set height=300

A value is parsed by the parameter's kind — a float for ``Length``,
``Angle``, ``Ratio`` and ``Scalar``, an integer for ``Count``, ``true``
or ``false`` for ``Flag`` — and checked by its constraints, so the shell
has exactly the door Python has. An unknown name fails listing the
root's settable parameters, a derived parameter cannot be set, and a
root that declares nothing refuses the flag. A develop session applies
the same overrides to every rebuild of its watch loop.

Artifacts for different parameter sets coexist in the build directory,
keyed by their values, so switching back is a cache hit; a child whose
parameters do not depend on the changed value keeps its key and is not
rebuilt.

Checking parameters together
============================

``min=`` and ``max=`` bound one value. A rule between two — the valve
stop must clear the stem, the cap must be tall enough for the frame
clearance plus the head — is ``check()``:

.. code-block:: python

    class Valve(CadQueryNode):

        stem_diameter = Length(4.0, min=0)
        stop_diameter = Length(6.0, min=0)

        def check(self):
            if self.stop_diameter <= self.stem_diameter:
                raise ValueError(
                    f'{self.name}: stop {self.stop_diameter} must exceed '
                    f'stem {self.stem_diameter}')

The framework calls ``check()`` on a declarative node as soon as its
parameters are resolved — each reads as a plain value — and before any
child is realized, so a refused root builds nothing. Whatever it raises
propagates unchanged; ``ValueError`` is the convention. The base
``check()`` does nothing, so a subclass chains ``super().check()``. A
class that declares nothing is not called: its attributes do not exist
yet when the base constructor runs, and it keeps its guards where it
has them.

.. _rest-and-motion:

Rest and motion: render() and simulate()
========================================

An assembly has two lifecycle methods, and the split between them is
what the framework knows about your machine.

``render()`` builds the machine **at rest**. It declares presence with
``omit()`` and places every part that does not move — a bearing cap on
its saddle, a clamp on its rail, a motor bolted to a frame. It reads no
driver, no ``self.time`` and no port, and the framework runs it **once
per instance**: the children it returns and the operations it applies
are the instance's, kept for good.

``simulate()`` **moves** it. The framework runs it after ``render()`` on
every instant — under symbolic ``$t`` in the build and the viewer, under
plain numbers in tests, snapshots and a stepped simulation — and it is
the one place drivers, time and ports are read and bound. Every
operation it applies is motion: stated absolutely for its instant,
dropped before the next run, and composed **inside** the part's rest
placement, so a part rotated in ``simulate()`` and translated in
``render()`` spins about its own axis and is then carried to its seat.

.. code-block:: python

    class Block(AssemblyNode):

        clearance = Length(0.3, min=0)

        frame = BlockFrame(clearance=clearance)
        caps  = MainBearingCap(clearance=clearance).repeat(5)
        crank = Crankshaft()

        angle = Driver(default=0.0, range=(0.0, 720.0), unit='deg')

        def render(self):
            for cap, x in zip(self.caps, BEARING_CENTERS):
                cap.translate([x, 0, 0])
            self.crank.translate([0, 0, CRANK_HEIGHT])

        def simulate(self):
            self.crank.rotate(self.angle, [1, 0, 0])

The crank turns about its own axis at rest height: the rotation from
``simulate()`` is applied first, the translation from ``render()``
carries it. A part that does not move needs no ``simulate()``; a pure
grouping node needs neither method. ``super().simulate()`` chains as
``super().render()`` does.

Ports are bound in ``simulate()`` too — ``connect()`` and port
assignment alike — because a binding made in ``render()`` would be made
once and never follow the drivers. The framework runs a parent's
``simulate()`` before it descends into the children, so a child reads in
its own ``simulate()`` what its parent bound:

.. code-block:: python

    class Cylinders(AssemblyNode):

        crank = Driver(default=0.0, range=(0.0, 720.0), unit='deg')

        units = CylinderUnit().repeat(8)

        def render(self):
            for unit, x in zip(self.units, STATIONS):
                unit.translate([x, 0, 0])

        def simulate(self):
            for unit, phase in zip(self.units, PHASES):
                unit.angle = self.crank + phase      # binds the unit's port

    class CylinderUnit(AssemblyNode):

        angle = RotationalPort(unit='deg')

        def simulate(self):
            self.con_rod.rotate(rod_angle(self.angle.value), [1, 0, 0])

The rule is enforced by what a method reads, not by its name. A
``render()`` that reads a driver, ``self.time`` or a port keeps working
exactly as it did before this split — it re-runs on every instant and
its operations are swept — and the build prints once per class::

    FutureWarning: SimpleClock.render() read time 'time'. Reading
    drivers, time or ports in render(), or binding a port there, is
    deprecated: render() builds the machine at rest and the framework
    runs it once per instance. Move the read or binding and the
    operations it feeds into simulate(), which runs on every instant.
    Until then SimpleClock re-renders per binding as before.

The class it names is migrated by moving the read and the operations it
feeds:

.. code-block:: python

    class SimpleClock(AssemblyNode):      # before

        def render(self):
            self.pointer.rotate(-360 * self.time, [0, 0, 1])
            return [self.base, self.pointer]

    class SimpleClock(AssemblyNode):      # after

        def render(self):
            return [self.base, self.pointer]

        def simulate(self):
            self.pointer.rotate(-360 * self.time, [0, 0, 1])

The framework decides on the first run of an instance's ``render()``, so
a ``render()`` that reads a driver only under some condition is judged
by what that first run did; a read through solid2's
``get_animation_time()`` directly is not seen at all. Read ``self.time``.
Binding a port in ``render()`` is reported the same way. The warning is
printed once per class per process, so when auditing several roots,
render each in its own process.
Placement applied in ``__init__`` still works and still composes after
the motion; it is no longer needed, and ``render()`` is where a rest
placement reads best.

Migrating a class
=================

Nothing forces a migration. A class that declares nothing keeps the
constructor form exactly as it is, and the two forms mix in one tree.
When you do migrate a class, know that:

* A class that forwarded all of its keywords, with float defaults,
  keeps its build identity. A class that forgot one gets a new, correct
  key; a class that passed an integer where a float kind now resolves
  re-keys once. Either way the next build rebuilds those artifacts, once.
* A declarative class rejects positional arguments and unknown keywords
  with a ``TypeError`` listing the declared names. Declaration order is
  a reading order, not a call signature.
* A declared name cannot shadow an attribute a base class carries
  (``name``, ``time``, ``mesh``, ``children``, ``color``, a sheet part's
  ``thickness``, ...); class definition raises. Such attributes stay
  what they are: a per-class constant or a constructor argument.
* A parameter cannot be assigned on an instance; ``self.bore = 5``
  raises. Pass the value to the constructor.
* Guards over several parameters at once go in ``check()``; rest
  placement goes in ``render()`` and motion in ``simulate()``. Neither
  needs the constructor form back.
* If a node class carries its own metaclass, derive it from
  ``solid_node.node.declarative.NodeMeta``, the way ``CadQueryNode``'s
  does.
