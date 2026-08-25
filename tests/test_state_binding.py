# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Multi-driver state binding on AssemblyNode.

A machine that is not periodic -- a printer executing instructions, a
car with independent steering and throttle -- has a pose that depends
on several independent inputs, and cannot be written as a function of
the single looping `$t` timeline ADR-008 provides. `set_state` binds a
snapshot of named numeric driver values, propagating exactly as
`set_keyframe` always has; `time` becomes one entry among several and
`set_keyframe` becomes the time-only surface over it.

These tests sit at the same layer as test_keyframe_reversal.py: real
assemblies rendered in process, with the serialized operations
inspected directly. Only the scenario that is explicitly about pose
builds STLs, because only a mesh can answer it.
"""

from solid_node.node import AssemblyNode

from .base import BaseNodeTest
from .meta_project.nested import Nested
from .meta_project.parts import Cube


def translations(node):
    return [op.serialized for op in node.operations
            if op.serialized[0] == 't']


class Machine(AssemblyNode):
    """Two independent drivers with no shared timeline: a stepper count
    advancing the rotor 0.001mm per step, and a lift height in mm.
    Neither is derivable from `$t` -- that is the whole point."""

    def __init__(self):
        self.rotor = Cube()
        self.platform = Cube(size=2.0)
        super().__init__()

    def render(self):
        self.rotor.translate([self.state['motor'] * 0.001, 0, 0])
        self.platform.translate([0, 0, self.state['lift']])
        return [self.rotor, self.platform]


class Idle(AssemblyNode):
    """An assembly that binds state without consuming it, so a snapshot
    can be inspected while it is still being assembled entry by entry
    -- a render reading an entry not yet bound would fail loudly, which
    is a different requirement."""

    def __init__(self):
        self.cube = Cube()
        super().__init__()

    def render(self):
        return [self.cube]


class StateBindingTest(BaseNodeTest):

    def test_two_named_drivers_bind_numerically(self):
        node = Machine()
        node.set_state(motor=4000, lift=2.5)

        self.assertEqual(node.state['motor'], 4000)
        self.assertEqual(node.state['lift'], 2.5)
        self.assertEqual(translations(node.rotor), [['t', ['4.0', '0', '0']]])
        self.assertEqual(translations(node.platform),
                         [['t', ['0', '0', '2.5']]])

    def test_bound_state_poses_the_meshes_absolutely(self):
        node = Machine()
        node.set_state(motor=4000, lift=2.5)
        node.assemble()
        node.build_stls()

        self.assertAlmostEqual(node.rotor.mesh.center_mass[0], 4.0,
                               delta=0.01)
        self.assertAlmostEqual(node.platform.mesh.center_mass[2], 2.5,
                               delta=0.01)

        node.set_state(motor=1000)

        self.assertAlmostEqual(node.rotor.mesh.center_mass[0], 1.0,
                               delta=0.01)
        self.assertAlmostEqual(node.platform.mesh.center_mass[2], 2.5,
                               delta=0.01)

    def test_merging_preserves_unrelated_entries(self):
        node = Idle()
        node.set_state(motor=4000)
        node.set_state(lift=1.0)

        self.assertEqual(dict(node.state), {'motor': 4000, 'lift': 1.0})

    def test_re_binding_a_name_replaces_only_that_entry(self):
        node = Idle()
        node.set_state(motor=4000, lift=1.0)
        node.set_state(motor=8000)

        self.assertEqual(dict(node.state), {'motor': 8000, 'lift': 1.0})

    def test_unbound_state_access_fails_loudly(self):
        node = Machine()

        with self.assertRaises(KeyError) as caught:
            node.render()

        message = str(caught.exception)
        self.assertIn('motor', message)
        self.assertIn('set_state', message)

    def test_state_values_must_be_plain_numbers(self):
        node = Idle()

        with self.assertRaises(TypeError):
            node.set_state(motor='4000')

    def test_state_cycles_do_not_accumulate_operations(self):
        node = Machine()
        # Static placement, applied outside any assembly render: never
        # swept, no matter how many snapshots are bound afterwards.
        node.platform.translate([0, 5, 0])

        for step in (1000, 2000, 3000):
            node.set_state(motor=step, lift=step / 1000)

        self.assertEqual(translations(node.rotor), [['t', ['3.0', '0', '0']]])
        self.assertEqual(translations(node.platform),
                         [['t', ['0', '5', '0']], ['t', ['0', '0', '3.0']]])

    def test_clearing_state_restores_symbolic_time(self):
        node = Nested()
        node.set_state(time=0.5, motor=100)
        self.assertEqual(node.time, 0.5)

        node.clear_state()

        self.assertEqual(dict(node.state), {})
        self.assertEqual(str(node.time), '$t')
        self.assertEqual(str(node.inner.time), '$t')
        self.assertEqual([op.serialized for op in node.inner.cube.operations],
                         [['t', ['(10 * $t)', '0', '0']]])

    def test_clearing_named_state_leaves_the_rest_bound(self):
        node = Idle()
        node.set_state(motor=4000, lift=1.0)

        node.clear_state('motor')

        self.assertEqual(dict(node.state), {'lift': 1.0})

    def test_state_propagates_into_nested_assemblies(self):
        node = Nested()
        node.set_state(time=0.5, motor=100)

        self.assertEqual(dict(node.inner.state),
                         {'time': 0.5, 'motor': 100})

    def test_binding_is_a_no_op_on_a_leaf(self):
        cube = Cube()

        cube.set_state(motor=10)
        cube.clear_state()

        self.assertFalse(hasattr(cube, 'state'))


class KeyframeEquivalenceTest(BaseNodeTest):
    """set_keyframe/clear_keyframe are exactly the time-only surface
    over the snapshot -- pinned here so the compatibility claim is a
    test, not a comment."""

    def test_set_keyframe_is_set_state_time(self):
        node = Nested()
        node.set_state(motor=100)

        node.set_keyframe(0.3)

        self.assertEqual(node.time, 0.3)
        self.assertEqual(dict(node.state), {'motor': 100, 'time': 0.3})
        self.assertEqual(node.inner.state['time'], 0.3)

    def test_clear_keyframe_is_clear_state_time(self):
        node = Nested()
        node.set_state(motor=100)
        node.set_keyframe(0.3)

        node.clear_keyframe()

        self.assertEqual(dict(node.state), {'motor': 100})
        self.assertEqual(str(node.time), '$t')
