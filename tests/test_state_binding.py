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
from solid_node.node.qualified import DriverIdError
from solid_node.simulation import Driver

from .base import BaseNodeTest
from .meta_project.machine import Axis, ListMachine
from .meta_project.machine import Machine as QualifiedMachine
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


class IdleAxis(AssemblyNode):
    """Declares a driver it does not consume: the snapshot can then be
    inspected entry by entry, including after a clear, without the
    unbound-read contract firing on the propagation's own re-render."""

    motor = Driver(default=0)

    def __init__(self, label):
        super().__init__(label)
        self.cube = Cube()

    def render(self):
        return [self.cube]


class IdleMachine(AssemblyNode):

    def __init__(self):
        super().__init__()
        self.x_axis = IdleAxis('x')
        self.y_axis = IdleAxis('y')

    def render(self):
        return [self.x_axis, self.y_axis]


class QualifiedStateBindingTest(BaseNodeTest):
    """Instance-qualified entries: two instances of one class hold
    independent values for their same-named driver, `time` stays the
    one global entry, and a bare name that could mean either of them
    fails instead of silently meaning both."""

    def test_sibling_instances_bind_independently(self):
        node = QualifiedMachine()

        node.set_state(**{'x_axis.motor': 8000, 'y_axis.motor': 2000})

        self.assertEqual(node.x_axis.state['motor'], 8000)
        self.assertEqual(node.y_axis.state['motor'], 2000)
        self.assertEqual(translations(node.x_axis.carriage),
                         [['t', ['100.0', '0', '0']]])
        self.assertEqual(translations(node.y_axis.carriage),
                         [['t', ['25.0', '0', '0']]])

    def test_the_consumed_segment_is_stripped_on_descent(self):
        """The addressed instance receives the LOCAL name its render()
        reads, not the qualified one; nothing else receives it."""
        node = QualifiedMachine()

        node.set_state(**{'x_axis.motor': 800, 'y_axis.motor': 0})

        self.assertEqual(dict(node.state), {})
        self.assertEqual(dict(node.x_axis.state), {'motor': 800})

    def test_time_stays_global(self):
        node = QualifiedMachine()

        node.set_state(time=0.25, **{'x_axis.motor': 0, 'y_axis.motor': 0})

        self.assertEqual(node.time, 0.25)
        self.assertEqual(node.x_axis.time, 0.25)
        self.assertEqual(node.y_axis.time, 0.25)

    def test_an_ambiguous_bare_name_fails_loudly(self):
        node = QualifiedMachine()
        node.set_state(**{'x_axis.motor': 8000, 'y_axis.motor': 2000})

        with self.assertRaises(ValueError) as caught:
            node.set_state(motor=1234)

        message = str(caught.exception)
        self.assertIn('x_axis.motor', message)
        self.assertIn('y_axis.motor', message)
        # Neither instance's state changed.
        self.assertEqual(node.x_axis.state['motor'], 8000)
        self.assertEqual(node.y_axis.state['motor'], 2000)

    def test_an_ambiguous_bare_name_on_an_unbound_tree_still_says_so(self):
        """Caught by the expression spike's revalidation run: rolling
        the failed bind back re-renders, and a tree nobody had bound
        yet cannot be rendered -- so the cleanup raised the unbound-read
        error over the ambiguity error that caused it."""
        node = QualifiedMachine()

        with self.assertRaises(ValueError) as caught:
            node.set_state(motor=1234)

        self.assertIn('x_axis.motor', str(caught.exception))

    def test_an_unambiguous_bare_name_still_binds(self):
        """One declaring instance in the tree: the stage-2 flat form is
        still exactly right, and still means what it said."""
        node = Axis('x')

        node.set_state(motor=1600)

        self.assertEqual(node.state['motor'], 1600)
        self.assertEqual(translations(node.carriage),
                         [['t', ['20.0', '0', '0']]])

    def test_clear_state_accepts_a_qualified_name(self):
        """Cleared on one instance only. The fixture declares a driver
        its render() does not read, for the same reason `Idle` above
        does: a render that consumed the entry would fail loudly on the
        very next propagation, which is a different requirement."""
        node = IdleMachine()
        node.set_state(**{'x_axis.motor': 8000, 'y_axis.motor': 2000})

        node.clear_state('x_axis.motor')

        self.assertEqual(dict(node.x_axis.state), {})
        self.assertEqual(node.y_axis.state['motor'], 2000)

    def test_propagation_links_children_before_recursing(self):
        """Qualification is only correct where `_link_child` has run,
        so the propagation walk links exactly as the scad and
        serializer passes do -- on a never-assembled tree."""
        node = QualifiedMachine()

        node.set_state(**{'x_axis.motor': 0, 'y_axis.motor': 0})

        self.assertEqual(node.x_axis.name, 'x_axis')
        self.assertEqual(node.y_axis.name, 'y_axis')
        self.assertIs(node.x_axis._parent, node)

    def test_a_driver_behind_an_illegal_segment_fails_loudly(self):
        node = ListMachine()

        with self.assertRaises(DriverIdError) as caught:
            node.set_state(**{'axes-0.motor': 0})

        self.assertIn('axes-0', str(caught.exception))
