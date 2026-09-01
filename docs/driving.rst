
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
            self.carriage.translate([self.position - TRAVEL / 2, 0, 11])
            return [self.rail, self.carriage]

`self.position` is used in expressions exactly as `self.time` is: the
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

Ports: how parts talk
=====================

A driver is an *input to the machine*. A **port** is a connection
point *between parts*: a unit-tagged value slot a node declares, that
its parent binds on every render with `connect()`:

.. code-block:: python

    from solid_node.node import TranslationalPort

    class SteppedAxis(AssemblyNode):
        motor = Driver(default=800, range=(0, 100), unit='ustep', dtype=int,
                       scale=MM_PER_USTEP)
        position = TranslationalPort(unit='mm', scale=MM_PER_USTEP)

        def render(self):
            self.connect(self.motor, self.position)
            self.carriage.translate([self.position.value, 0, 0])
            ...

Ports are domain-typed — `RotationalPort`, `TranslationalPort`,
`SignalPort` — and carry a unit and an optional scale, so the
conversion from a source's units to the sink's is declared once
instead of sprinkled through expressions. `connect(source, sink)` is
causal: the source expression flows into the sink, immediately, every
render. Ports are also how a :ref:`flexible part <flexible-parts>`
gets its shape — the chain is *driver → port → geometry* — and a
port-bound value is deliberately **not** part of a part's build
identity, so driving a machine never mints new cached artifacts.

Instructions
============

An `Instruction` names driver targets in design units plus a duration:
``Instruction({'x_axis.position': 0.0}, duration=2.0)``. Declared in an
``instructions`` dict on an assembly class, it becomes a button in the
viewer and a `trigger()` in simulations and in the embedding API.
Triggering one ramps every target from its current value to the named
value over the duration, landing exactly on target; triggering another
while one runs replaces the active ramp.

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
layer: see :doc:`Simulating and testing scenarios <scenarios>`.
