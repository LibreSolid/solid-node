
.. _scenarios:

================================
Simulating and testing scenarios
================================

:doc:`Driving a machine <driving>` by hand answers "what does this
pose look like". A **scenario** answers the questions after that: does
the carriage clear the stop on the way home, when does it arrive, what
did the whole run look like. For those, the machine is stepped
deterministically in Python by `solid_node.simulation`.

The stepped loop
================

A `Sim` steps one assembly with a fixed time step:

.. code-block:: python

    from solid_node.simulation import Sim

    sim = Sim(machine, dt=0.02)

Its instants are **integer tick counts**: the clock advances tick by
tick, ``sim.time`` is ``tick * dt`` in seconds, and an instant that is
not a whole number of ticks is rejected rather than rounded. That is
what makes a scenario deterministic — the same program over the same
machine takes the same ticks and lands on the same values, every run,
on every platform.

Inside a simulation, ``self.time`` in your ``simulate()`` reads this
stepped clock, in seconds. The normalized 0..1 ``$t`` of the
:doc:`animation timeline <animation>` is untouched outside
simulations; the two are different clocks for different jobs.

A scenario is scheduled, then run:

.. code-block:: python

    sim.at(0.0).trigger('Home')                # due at t=0, fires first
    sim.every(0.1, check_clearance, machine)   # a cadence, every 5 ticks
    sim.at(2.5).run(lambda s: log(s.state))    # any callable, given the sim
    sim.run(3.0)                               # step 150 ticks

* ``at(t)`` schedules an action for one instant — triggering an
  instruction or running a callable. Actions due at the current tick
  fire **before** the first step, so ``at(0.0).trigger(...)`` is not
  one tick late.
* ``every(period, fn, *args)`` calls ``fn`` on a cadence. This is how
  a scenario keeps an invariant under watch — an interference check
  every tenth of a second — and ``sim.cadence_costs`` reports what
  each cadence cost, so an expensive geometric check is a visible,
  chosen expense.
* ``trigger(name)`` starts a declared `Instruction`: a `RampProgram`
  advances each target from its current value as a pure function of
  the tick, and **lands exactly on target**. An integer-typed driver
  ramps integer-exactly (``start + delta*k//n``) — every intermediate
  value is a whole native unit, with no accumulated float error.
* ``run(duration)`` steps the loop. Each tick binds a full snapshot of
  qualified driver values plus the global ``time``, so nested
  assemblies render numerically, and appends to ``sim.trajectory`` —
  the recorded ``(tick, states)`` history of the whole run.

``sim.state`` is the live bank of driver values by qualified id, the
same ids `set_state` and the document's driver table use.

Scenario tests
==============

`ScenarioTest` packages the loop for a test suite. Declare the node,
the step, and whether the scenario needs geometry:

.. code-block:: python

    from solid_node.simulation import ScenarioTest

    from .axis import Axis

    class AxisScenarioTest(ScenarioTest):
        node = Axis
        dt = 0.02
        meshes = True    # this scenario asserts on geometry

        def test_homing_stays_clear_of_the_stop(self):
            sim = self.simulation()
            arrived = []

            sim.at(0.0).trigger('Home')
            sim.every(0.1, self.assertNoSolidInterference, self.node)
            sim.at(2.5).run(lambda s: arrived.append(s.state['x']))
            sim.run(3.0)

            self.assertEqual(arrived, [0])
            self.assertEqual(sim.assertion_stats[0], 30)

Every scenario gets a **fresh** simulation from ``self.simulation()``
— the state bank is the whole of what a run mutates, so two scenarios
of one class share nothing but the geometry they were built from, and
each starts from the declared driver defaults.

``meshes = True`` is what makes the run build STLs; a scenario about
state alone should not pay for them. With meshes on, the geometric
assertions of the :doc:`test framework <testing>` work inside a
cadence: the homing test above proves clearance thirty times along the
move, and its counterpart proves the *teeth* — an instruction that
deliberately drives into the stop must be caught at the exact tick the
overlap appears:

.. code-block:: python

        def test_a_crash_is_caught_at_the_tick_it_appears(self):
            sim = self.simulation()

            sim.at(0.0).trigger('Crash')
            sim.every(0.1, self.assertNoSolidInterference, self.node)

            with self.assertRaises(AssertionError):
                sim.run(3.0)

            self.assertEqual(sim.tick, 75)

A scenario that only ever passes is not evidence; write the run that
must fail, and assert where it fails.

One class, both runners
=======================

A `ScenarioTest` is a `TestCase`. As a companion test of a node file
it runs under ``solid test`` like any other; imported into a pytest
module it runs under plain ``pytest``. Neither runner is modified for
it, and nothing in a scenario is written for one runner or the other —
under the CLI, ``node`` is the built instance the runner hands over;
under pytest it is the declared class and the scenario builds it.

Choosing dt
===========

``dt`` is part of the scenario's meaning, not a tuning knob: the crash
test above asserts tick 75 *because* ``dt = 0.02`` makes the carriage
travel 0.15mm per tick. Pick a step that resolves the finest motion
the scenario judges, declare it on the class, and let the tick
arithmetic be exact from there.


Running a machine that keeps its history
========================================

Everything above poses the machine from the current driver values. Under
a root declaring :ref:`Time.running() <animation>` — ``time =
Time.running()``, the second time base — a simulation instead OWNS the
machine's coordinates and moves them by increments, so a crank turned ten
degrees twice leaves its arbor at forty rather than back at twenty.

``sim.state`` is then the whole BANK: every driver **and** every joint
coordinate of the linked tree, by the same qualified ids the document
publishes. Plain ports and derived coordinates are not in it — they are
calculations over the state, recomputed by the ordinary render on every
tick. The initial bank is the untimed rest pose at the requested driver
values, so ``Sim(machine, dt, state={'crank': 30.0})`` starts where the
relations put the machine at a crank of thirty. A joint coordinate the
rest render leaves unbound is refused at construction, naming it: the run
needs a rest value for every coordinate it keeps the history of.

Commands, not bindings
----------------------

A running simulation takes requests rather than snapshots:

.. code-block:: python

        sim = Sim(machine, 0.1)

        turn = sim.move('crank', by=10.0, duration=1.0)   # travel
        sim.move('carriage', to=40.0, duration=0.5)       # land
        spin = sim.rate('spindle', 90.0)                  # until released
        sim.trigger('Advance')                            # an instruction

        sim.run(1.0)
        sim.rate('spindle', 0)          # completes the rate

        turn.status                     # 'completed'
        turn.admitted                   # 10.0, in design units

Only a declared driver can be moved, and each has ONE OWNER at a time: a
second move or rate on an input another command holds is refused naming
both. Every request returns a handle reporting ``active``, ``completed``,
``blocked``, ``refused`` or ``cancelled`` and the travel actually
admitted; a completed command leaves ``sim.commands`` the tick it
finishes, so a long run accumulates none. ``duration`` is a whole number
of ticks, zero included — a zero-duration move settles at the current
tick without advancing the clock.

An instruction works the same way, and now states either where its
drivers land or how far they travel:

.. code-block:: python

    instructions = {
        'Park':    Instruction({'crank': 40.0}, duration=0.5),
        'Advance': Instruction(by={'crank': 10.0}, duration=0.5),
    }

``by=`` is a relative ramp under every time base: untimed and looping it
ramps each driver from where it stands, and under a running root it
becomes ``move(by=)``. A relative instruction is not published in the
document's instructions table yet — the shipped viewer reads ``targets``
off every entry — so declare one for a scenario before you declare one
for a button.

A law that jumps
----------------

A law may contain a **jump** — ``floor``, ``ceil``, ``sign``, ``%`` or a
comparison — and a periodic mechanism usually does. The Curta's tooth
window is the illustration: a pinion that turns 72 degrees while one
tooth is engaged, once per crank revolution.

.. code-block:: python

    def periodic_window(source, target):
        return lambda angle: 4 + 72 * clamp01(
            (angle - 360 * floor(angle / 360) - 113.5) / 11.25)

    crank.drives(pinion.turn, law=periodic_window)

Absolutely, that law can only say where the pinion IS for a crank angle:
after a whole revolution it reads exactly what it read before. Running,
it is INTEGRATED, and the jump is subtracted. Over one tick the run cuts
the path the sources take at every crossing of every jump surface it
meets; on each piece every jump node holds one branch, read at the
piece's midpoint; and the increment is the sum of the branch-substituted
law's change over the pieces. So the pinion stands at ``4`` at rest, at
``76`` after one crank turn and at ``148`` after two, and the tick in
which the crank passes 360 degrees contributes exactly zero.

Every crossing inside the tick is found, not only the difference of its
ends: a crank turned far enough to pass three tooth windows in one tick
adds three throws. The five primitives cross where their LEVEL QUANTITY
reaches a surface — ``floor(x)`` and ``ceil(x)`` over ``x`` at every
integer, ``sign(x)`` over ``x`` at zero, ``a % b`` over ``a / b`` at
every NONZERO integer (``%`` is ``fmod``, which takes the sign of the
dividend and is continuous where ``a / b`` crosses zero), and a
comparison over ``a - b`` at zero. :func:`~solid_node.math.wrap` is
built on ``ceil`` and integrates through the same door — a wrapped law
reads as the unwrapped travel — and :func:`~solid_node.math.piecewise`
needs nothing of its own, being a sum of ``clamp01`` terms with no jump
in it at all.

DISENGAGEMENT is a law's own business, and both its shapes are now
expressible: a gate factor in a multi-source law, or the zero-slope
region of a single-source one.

.. code-block:: python

    def clutch(sources, target):
        return lambda shaft, sleeve: -2 * shaft * (sleeve > 0.5)

    (shaft.turn & sleeve.travel).drives(wheel.turn, law=clutch)

The wheel holds while the sleeve is out, drives while it is in, and on
the tick in which the sleeve travels from ``0`` to ``1`` takes the travel
AFTER engagement only — never the value the gate factor would have jumped
to. A law naming several sources takes one straight path in their joint
space, which is what makes a clutch closing while a shaft turns one
question rather than two.

Two things are refused, and one more can refuse a tick:

* a law that can move its coordinate **only by jumping** — ``floor(turns)``
  alone — because every jump is subtracted, so such a law can never move
  anything. It states arithmetic, not a mechanism.
  ``9 * enabled + floor(turns)`` is not refused: ``enabled`` still
  carries slope, and the running reading simply gives the turns nothing;
* a jumping law whose driven ends are all **intermediates** — a plain
  port, a derived coordinate. A subtracted jump implies a history, and
  only a coordinate the run owns keeps one; an intermediate is
  recomputed from the bank on every tick, so it would snap while the
  joint behind it moved smoothly. State the relation into the joint
  coordinate and let the port follow it;
* a tick that would cross more than a thousand surfaces of one law is
  refused naming the relation, the coordinate, the primitive and the
  count, and commits nothing. A ``dt`` that coarse is not resolving the
  mechanism.

A level quantity that is AFFINE in the sources along the path — which is
every periodic law in practice — has its crossings solved exactly, all of
them. Anything else is sampled at 64 sub-intervals and each bracketed
crossing bisected; a level quantity that turns twice inside one
sub-interval is outside that guarantee, and the answer to it is a smaller
``dt``.

Snapshot, restore, reset, record
--------------------------------

``sim.snapshot()`` is a value: the bank, the tick, ``dt``, the active
commands and the program's identity. ``sim.restore(snapshot)`` puts the
run back, refusing a snapshot taken over a different machine or a
different ``dt`` before it touches anything, and ``sim.reset()`` restores
``sim.initial`` — the rest pose. Recording is explicit and bounded:
``record=None`` keeps nothing and ``sim.trajectory`` reads empty, while
``record=64`` keeps a ring of the most recent sixty-four ticks. A run
that never wraps cannot keep every tick, and ``every()`` sees each one as
it happens.

``record=N`` keeps a second ring of the same length, read through
``sim.crossings``: the most recent ``N`` crossings located inside a tick,
each naming the tick, the relation as written, the driven coordinate, the
primitive that jumped, the surface it reached and the fraction of the
tick at which it did. ``record=None`` keeps none and builds none, and
restore and reset clear both rings. A surface reached exactly at a tick's
own boundary is not inside any tick, so it is integrated — correctly, and
contributing nothing — without appearing in the record.

What this release refuses
-------------------------

Each of these is refused by name, and each is a later cycle's to lift:

* a law that cannot be applied to a symbol — one written over Python's
  own ``math`` rather than :doc:`solid_node.math <math>`;
* a relation into a coordinate the run owns whose SOURCE is a plain port
  an author's ``simulate()`` binds: state that value as a relation, or
  give the part a joint;
* an author's ``simulate()`` that binds a run-owned coordinate
  unconditionally — that is a law written imperatively, and it belongs in
  a relation. The rest-default idiom, binding under ``if ... is None``,
  keeps working: it binds once, at the rest render;
* a **reverse** move — a negative ``by``, a ``to`` below where the input
  stands, a negative rate — because reverse travel meets no stop until a
  joint range becomes a physical one;
* a joint coordinate leaving its declared **range**, which fails the tick
  rather than stopping the group it is connected to.

A tick that refuses commits nothing: the bank, the tick count and the
posed tree stand as they were, and the commands that moved an input in
it are retired reporting ``refused``.
