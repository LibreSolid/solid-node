# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""render() builds the machine at rest; simulate() moves it.

An assembly's render() reads no driver, no time and no port: it declares
structure, omits, and places what does not move, and the framework runs
it once per instance. simulate() runs after it on every enumeration,
under the current binding -- symbolic $t when nothing is bound, plain
numbers under set_state and set_keyframe -- and every operation it
applies composes INNERMOST, before the rest placement, tagged and swept
so poses are absolute.

A render() that does read a driver keeps the previous behaviour for that
instance -- re-run per binding, tagged and swept -- and warns once per
class. Nothing that worked stops working.
"""

import warnings

import numpy as np
from solid2 import cube

from solid_node.node import AssemblyNode, Solid2Node
from solid_node.motion.ports import RotationalPort
from solid_node.node.base import _compose_world_matrix
from solid_node.node.declarative import StructureError
from solid_node.parameters import Flag, Length
from solid_node.simulation import Driver

from .base import BaseNodeTest


class Box(Solid2Node):

    size = Length(1.0, min=0)

    def render(self):
        return cube(self.size, center=True)


class Rotor(Box):

    angle = RotationalPort(unit='deg')


def serialized(node):
    return [op.serialized for op in node.operations]


def kinds(node):
    return [op.serialized[0] for op in node.operations]


def origin(node):
    point = _compose_world_matrix(node) @ np.array([0.0, 0.0, 0.0, 1.0])
    return tuple(round(float(v), 6) for v in point[:3])


class Arm(AssemblyNode):
    """Rest placement in render(), motion in simulate()."""

    angle = Driver(default=0.0, unit='deg')

    box = Box()

    renders = 0

    def render(self):
        type(self).renders += 1
        self.box.translate([10, 0, 0])

    def simulate(self):
        self.box.rotate(self.angle, [0, 0, 1])


class Spinner(AssemblyNode):
    """Motion over the timeline: symbolic until a keyframe binds it."""

    box = Box()

    def simulate(self):
        self.box.rotate(360 * self.time, [0, 0, 1])


class Seated(Arm):
    """Construction placement, then rest placement, then motion."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.box.translate([0, 0, 5])


class Doubled(Arm):

    def simulate(self):
        super().simulate()
        self.box.translate([0, 1, 0])


class Group(AssemblyNode):

    box = Box()


class Spin(AssemblyNode):

    def __init__(self, wheel):
        self.wheel = wheel
        super().__init__()

    def render(self):
        return [self.wheel]

    def simulate(self):
        self.wheel.rotate(360 * self.time, [0, 1, 0])


class Steer(AssemblyNode):

    def __init__(self, wheel):
        self.wheel = wheel
        super().__init__()

    def render(self):
        return [self.wheel]

    def simulate(self):
        self.wheel.rotate(30 * self.time, [0, 0, 1])


class Gated(AssemblyNode):

    guard = Flag(True)

    a = Box()
    b = Box()

    def render(self):
        if not self.guard:
            self.b.omit()

    def simulate(self):
        self.a.rotate(360 * self.time, [0, 0, 1])


class Omitter(AssemblyNode):

    a = Box()
    b = Box()

    def simulate(self):
        self.b.omit()


class LegacyTime(AssemblyNode):

    def __init__(self):
        self.box = Box()
        super().__init__()

    def render(self):
        self.box.translate([10 * self.time, 0, 0])
        return [self.box]


class LegacyDriver(AssemblyNode):

    motor = Driver(default=0, unit='ustep')

    def __init__(self):
        self.box = Box()
        super().__init__()

    def render(self):
        self.box.translate([self.motor * 0.001, 0, 0])
        return [self.box]


class LegacyPort(AssemblyNode):

    rotor = Rotor()

    def render(self):
        self.rotor.angle = 15.0
        self.rotor.rotate(self.rotor.angle.value, [0, 0, 1])

    def simulate(self):
        pass


class LegacyBinding(AssemblyNode):

    rotor = Rotor()

    def render(self):
        self.rotor.angle = 15.0


def caught(action):
    with warnings.catch_warnings(record=True) as seen:
        warnings.simplefilter('always')
        action()
    return [w for w in seen if issubclass(w.category, FutureWarning)]


class SimulateCompositionTest(BaseNodeTest):

    def test_simulate_runs_after_render_and_composes_innermost(self):
        arm = Arm()
        arm.set_state(angle=90.0)

        self.assertEqual(kinds(arm.box), ['r', 't'])
        self.assertEqual(origin(arm.box), (10.0, 0.0, 0.0))

    def test_a_render_that_read_nothing_runs_once(self):
        Arm.renders = 0
        arm = Arm()
        arm.set_state(angle=10.0)
        placement = arm.box.operations[-1]
        arm.set_state(angle=20.0)
        arm.set_state(angle=30.0)

        self.assertEqual(Arm.renders, 1)
        self.assertIs(arm.box.operations[-1], placement)
        self.assertEqual(kinds(arm.box), ['r', 't'])
        self.assertEqual(arm.box.operations[0].serialized[1], '30.0')

    def test_rest_placement_is_never_swept(self):
        arm = Arm()
        arm.set_state(angle=10.0)
        placement = arm.box.operations[-1]

        self.assertFalse(hasattr(placement, '_animator'))
        self.assertIs(arm.box.operations[0]._animator, arm)

    def test_simulate_is_symbolic_until_bound_and_reversible(self):
        spinner = Spinner()
        spinner.render()
        self.assertIn('$t', serialized(spinner.box)[0][1])

        spinner.set_keyframe(0.25)
        self.assertEqual(serialized(spinner.box)[0][1], '90.0')

        spinner.clear_keyframe()
        self.assertEqual(len(spinner.box.operations), 1)
        self.assertIn('$t', serialized(spinner.box)[0][1])

    def test_assemble_runs_simulate(self):
        spinner = Spinner()
        spinner.assemble()

        self.assertEqual(kinds(spinner.box), ['r'])
        self.assertIn('$t', serialized(spinner.box)[0][1])

    def test_two_simulators_of_one_node_keep_apart(self):
        wheel = Box()
        spin = Spin(wheel)
        steer = Steer(wheel)
        spin.render()
        steer.render()
        steering = wheel.operations[-1]
        spin.render()

        self.assertEqual(len(wheel.operations), 2)
        self.assertIn(steering, wheel.operations)
        self.assertEqual({op._animator for op in wheel.operations},
                         {spin, steer})

    def test_construction_placement_sits_between_motion_and_rest(self):
        seated = Seated()
        seated.set_state(angle=45.0)

        self.assertEqual(serialized(seated.box), [
            ['r', '45.0', [0, 0, 1]],
            ['t', ['0', '0', '5']],
            ['t', ['10', '0', '0']],
        ])

    def test_a_subclass_simulate_delegates(self):
        doubled = Doubled()
        doubled.set_state(angle=45.0)
        doubled.set_state(angle=60.0)

        self.assertEqual(kinds(doubled.box), ['r', 't', 't'])
        self.assertEqual(serialized(doubled.box)[0][1], '60.0')
        self.assertEqual(serialized(doubled.box)[1], ['t', ['0', '1', '0']])

    def test_a_methodless_assembly_needs_no_simulate(self):
        group = Group()

        self.assertEqual([c.name for c in group.render()], ['box'])
        self.assertEqual(group.box.operations, [])


class SimulateStructureTest(BaseNodeTest):

    def test_omit_in_simulate_is_refused(self):
        omitter = Omitter()

        with self.assertRaises(StructureError) as raised:
            omitter.render()
        self.assertIn('Omitter', str(raised.exception))
        self.assertIn('simulate', str(raised.exception))

    def test_omission_at_rest_holds_across_bindings(self):
        gated = Gated(guard=False)
        names = []
        for time in (0.0, 0.5, 1.0):
            gated.set_keyframe(time)
            names.append([c.name for c in gated.render()])

        self.assertEqual(names, [['a'], ['a'], ['a']])


class LegacyRenderTest(BaseNodeTest):

    def test_a_render_reading_time_keeps_animating_and_warns_once(self):
        node = LegacyTime()
        seen = caught(lambda: (node.set_keyframe(0.5),
                               node.set_keyframe(1.0)))

        self.assertEqual(serialized(node.box), [['t', ['10.0', '0', '0']]])
        self.assertEqual(len(seen), 1)
        message = str(seen[0].message)
        self.assertIn('LegacyTime', message)
        self.assertIn('time', message)
        self.assertIn('simulate()', message)

        again = caught(lambda: LegacyTime().set_keyframe(0.25))
        self.assertEqual(again, [])

    def test_a_render_reading_a_driver_warns(self):
        node = LegacyDriver()
        seen = caught(lambda: (node.set_state(motor=1000),
                               node.set_state(motor=2000)))

        self.assertEqual(serialized(node.box), [['t', ['2.0', '0', '0']]])
        self.assertEqual(len(seen), 1)
        self.assertIn("'motor'", str(seen[0].message))

    def test_a_render_binding_a_port_warns(self):
        node = LegacyBinding()
        seen = caught(lambda: (node.render(), node.render()))

        self.assertEqual(len(seen), 1)
        self.assertIn("bound port 'angle'", str(seen[0].message))
        self.assertTrue(node.__dict__.get('_legacy_render'))

    def test_a_render_reading_a_port_warns(self):
        node = LegacyPort()
        seen = caught(lambda: (node.render(), node.render()))

        self.assertEqual(serialized(node.rotor), [['r', '15.0', [0, 0, 1]]])
        self.assertEqual(len(seen), 1)
        self.assertIn("'angle'", str(seen[0].message))
