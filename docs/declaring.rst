
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

    from solid_node.node import CadQueryNode, Length

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
  units are driven through ports, fed from the parent's ``render()``.

render() that returns nothing
=============================

On a declarative internal node, ``render()`` positions and selects, and
returns nothing. The children are then the declared children, in
declaration order, minus any it omitted:

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
its build identity. Decide ``omit()`` from declared parameters only. A
condition on a time-derived value already fails under symbolic time,
and under a bound keyframe the framework compares each render's omitted
set with the instance's first render and raises when they differ.

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

Where placement goes
====================

``render()`` runs every frame, and the animator sweeps and re-applies
the operations it adds. That is right for a part that moves. A part
that never moves — a bearing cap on its saddle, a clamp on its rail —
is placed once. A declarative class may still define ``__init__`` for
exactly that:

.. code-block:: python

    class Block(AssemblyNode):

        clearance = Length(0.3, min=0)

        frame = BlockFrame(clearance=clearance)
        caps  = MainBearingCap(clearance=clearance).repeat(5)

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            for cap, x in zip(self.caps, BEARING_CENTERS):
                cap.translate([x, 0, 0])

After ``super().__init__(**kwargs)`` the parameters read as values and
the children are realized, and an operation applied there survives
every render untouched. Moving parts stay in ``render()``. This is the
recommendation for now: the split between a once-only placement and a
per-frame one is on the pilot's list to revisit together with the
naming of ``render()`` itself.

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
* Guards over several parameters at once go in ``check()``; a
  once-only placement goes in ``__init__`` after
  ``super().__init__(**kwargs)``. Neither needs the constructor form
  back.
* If a node class carries its own metaclass, derive it from
  ``solid_node.node.declarative.NodeMeta``, the way ``CadQueryNode``'s
  does.
