# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The declared time base (OpenSpec change ``declared-time-base``).

A root assembly declares ``time = Time(loop=<seconds>)`` and from then
on ``self.time`` reads machine seconds on every path: the symbolic
``$t * loop`` when nothing is bound, the bound number under keyframes
and the stepped simulation, seconds through the testing decorators.
Descendants read the root's time base; a declaration below the root is
refused when read. Producers publish the loop beside ``fps`` and
``frames``; ``solid snapshot --time`` converts its fraction to seconds.

Originating project: 3DPrintedClocks ``wall_clock_01``, whose twelve
hour turn played in twelve seconds.
"""

import json
import math
import os
import tempfile
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from solid_node.core.builder import Builder
from solid_node.core.export import export_node
from solid_node.core.serializer import animation_block
from solid_node.node import AssemblyNode, Solid2Node, Time
from solid_node.node.timebase import declared_time
from solid_node.test import testing_steps as steps_of
from solid2 import cube

from .base import BaseNodeTest
from .meta_project.parts import Cube


LOOP = 12 * 3600.0


class Pointer(AssemblyNode):
    """A hand told where to point by its parent through time alone."""

    def __init__(self):
        self.cube = Cube()
        super().__init__()

    def render(self):
        return [self.cube]

    def simulate(self):
        # one turn an hour: degrees per second times seconds
        self.cube.rotate(360 * self.time / 3600, [0, 0, 1])


class Clock(AssemblyNode):

    time = Time(loop=LOOP)

    def __init__(self):
        self.pointer = Pointer()
        super().__init__()

    def render(self):
        return [self.pointer]


class Undeclared(AssemblyNode):

    def __init__(self):
        self.pointer = Pointer()
        super().__init__()

    def render(self):
        return [self.pointer]


class DeclaringChild(AssemblyNode):
    """A component that declares its own time base, composed under a
    root that declares none: refused when read, its own when alone."""

    time = Time(loop=60)

    def __init__(self):
        self.cube = Cube()
        super().__init__()

    def render(self):
        return [self.cube]

    def simulate(self):
        self.cube.rotate(6 * self.time, [0, 0, 1])


class ComposingRoot(AssemblyNode):

    def __init__(self):
        self.child = DeclaringChild()
        super().__init__()

    def render(self):
        return [self.child]


def rotation_strings(node):
    return [op.serialized for op in node.operations if op.serialized[0] == 'r']


class DeclarationTest(TestCase):

    def test_the_declaration_is_readable_off_the_class(self):
        self.assertIsInstance(Clock.time, Time)
        self.assertEqual(Clock.time.loop, LOOP)
        self.assertIsInstance(Clock.time.loop, float)

    def test_declared_time_reads_the_class_and_the_undeclared_case(self):
        self.assertIs(declared_time(Clock), Clock.time)
        self.assertIsNone(declared_time(Undeclared))
        self.assertIsNone(declared_time(SimpleNamespace))

    def test_a_subclass_inherits_the_declaration(self):
        class Later(Clock):
            pass
        self.assertIs(declared_time(Later), Clock.time)

    def test_loop_is_required_and_must_be_a_positive_finite_number(self):
        with self.assertRaises(TypeError):
            Time()
        for bad in (0, -1, math.inf, math.nan, '12h', None, True):
            with self.subTest(loop=bad):
                with self.assertRaisesRegex((TypeError, ValueError), 'loop'):
                    Time(loop=bad)

    def test_only_the_name_time_may_hold_a_declaration(self):
        with self.assertRaisesRegex(TypeError, "'time'"):
            class Misnamed(AssemblyNode):
                clock = Time(loop=60)

    def test_only_an_assembly_may_declare_one(self):
        with self.assertRaisesRegex(TypeError, 'AssemblyNode'):
            class Leaf(Solid2Node):
                time = Time(loop=60)

                def render(self):
                    return cube(1)

    def test_the_instance_attribute_cannot_be_assigned(self):
        clock = Clock()
        with self.assertRaisesRegex(AttributeError, 'set_keyframe'):
            clock.time = 3.0

    def test_time_is_exported_from_the_node_package(self):
        from solid_node import node
        self.assertIs(node.Time, Time)
        self.assertIn('Time', node.__all__)


class SymbolicTimeTest(BaseNodeTest):

    def test_unbound_time_is_t_times_the_loop_on_root_and_descendant(self):
        clock = Clock()
        # A real walker links the child before it renders; a bare
        # render() links nothing, by the declarative-nodes contract.
        clock.assemble()
        expected = str(clock.time)
        self.assertNotIsInstance(clock.time, float)
        self.assertIn('$t', expected)
        self.assertIn('43200', expected)
        self.assertEqual(str(clock.pointer.time), expected)

    def test_serialized_operations_carry_the_loop_not_a_constant(self):
        clock = Clock()
        clock.assemble()
        [rotation] = rotation_strings(clock.pointer.cube)
        angle = rotation[1]
        self.assertIn('$t', angle)
        self.assertIn('43200', angle)
        self.assertIn('360', angle)

    def test_an_undeclared_root_still_reads_bare_t(self):
        plain = Undeclared()
        plain.assemble()
        self.assertEqual(str(plain.time), '$t')
        self.assertEqual(str(plain.pointer.time), '$t')

    def test_a_declaring_assembly_loaded_alone_uses_its_own_loop(self):
        alone = DeclaringChild()
        alone.render()
        text = str(alone.time)
        self.assertIn('$t', text)
        self.assertIn('60', text)

    def test_a_declaration_below_the_root_is_refused_when_read(self):
        root = ComposingRoot()
        with self.assertRaisesRegex(TypeError, 'child.*ComposingRoot|ComposingRoot.*child'):
            root.assemble()


class BoundTimeTest(BaseNodeTest):

    def test_keyframes_bind_seconds_on_root_and_descendant(self):
        clock = Clock()
        clock.set_keyframe(2700)
        self.assertEqual(clock.time, 2700)
        self.assertEqual(clock.pointer.time, 2700)
        clock.pointer.render()
        [rotation] = rotation_strings(clock.pointer.cube)
        self.assertAlmostEqual(float(rotation[1]), 270.0)

    def test_clearing_restores_the_loop_expression(self):
        fresh = Clock()
        fresh.assemble()
        expected = rotation_strings(fresh.pointer.cube)

        clock = Clock()
        clock.set_keyframe(2700)
        clock.clear_keyframe()
        self.assertNotIsInstance(clock.time, float)
        self.assertIn('43200', str(clock.time))
        # clear_keyframe re-rendered the linked tree under symbolic time
        self.assertEqual(rotation_strings(clock.pointer.cube), expected)

    def test_set_state_equivalence(self):
        clock = Clock()
        clock.set_state(time=1.5)
        self.assertEqual(clock.time, 1.5)
        self.assertEqual(clock.pointer.time, 1.5)

    def test_testing_steps_hand_seconds_through(self):
        @steps_of(4, end=1.5)
        def sweep(self):
            pass
        self.assertEqual(sweep.testing_instants, [0, 0.5, 1.0, 1.5])
        clock = Clock()
        clock.set_keyframe(sweep.testing_instants[-1])
        self.assertEqual(clock.time, 1.5)


class PublishedLoopTest(BaseNodeTest):

    def test_animation_block_carries_the_loop_only_when_declared(self):
        self.assertEqual(animation_block(Clock(), 30, 360),
                         {'fps': 30, 'frames': 360, 'loop': LOOP})
        self.assertEqual(animation_block(Undeclared(), 12, 60),
                         {'fps': 12, 'frames': 60})
        self.assertEqual(animation_block(SimpleNamespace(), 30, 360),
                         {'fps': 30, 'frames': 360})

    def test_export_publishes_the_loop_and_keeps_the_version(self):
        clock = Clock()
        clock.assemble()
        out = os.path.join(self.build_dir, 'export_out')
        export_node(clock, out, fps=12, frames=60, widget=False)
        with open(os.path.join(out, 'manifest.json')) as fh:
            manifest = json.load(fh)
        self.assertEqual(manifest['animation'],
                         {'fps': 12, 'frames': 60, 'loop': LOOP})
        self.assertEqual(manifest['version'], 2)
        pointer = manifest['root']['children'][0]
        [rotation] = [op for op in pointer['children'][0]['operations']
                      if op[0] == 'r']
        self.assertIn('$t', rotation[1])
        self.assertIn('43200', rotation[1])

    def test_export_of_an_undeclared_root_has_no_loop_key(self):
        plain = Undeclared()
        plain.assemble()
        out = os.path.join(self.build_dir, 'export_out')
        export_node(plain, out, widget=False)
        with open(os.path.join(out, 'manifest.json')) as fh:
            manifest = json.load(fh)
        self.assertEqual(manifest['animation'], {'fps': 30, 'frames': 360})

    def test_the_builder_snapshot_publishes_the_loop(self):
        clock = Clock()
        clock.assemble()
        clock.build_stls()
        builder = Builder('model.py', build_dir=self.build_dir, watch=False)
        builder.node = clock
        builder._write_viewer_snapshot()
        with open(os.path.join(self.build_dir, 'viewer.json')) as fh:
            data = json.load(fh)
        self.assertEqual(data['animation'],
                         {'fps': 30, 'frames': 360, 'loop': LOOP})


class SnapshotTimeTest(TestCase):

    def prepare(self, node, time):
        from solid_node.manager.snapshot import Snapshot
        snapshot = Snapshot.__new__(Snapshot)
        snapshot.path = 'model.py'
        snapshot.time = time
        with (patch('solid_node.manager.snapshot.load_node',
                    return_value=node),
              patch('solid_node.manager.snapshot.project_build_lock'),
              patch.object(node, 'set_keyframe') as keyframe,
              patch.object(node, 'assemble')):
            snapshot._load_and_prepare_node()
        return keyframe

    def test_a_fraction_lands_on_the_declared_instant(self):
        keyframe = self.prepare(Clock(), 0.5)
        keyframe.assert_called_once_with(0.5 * LOOP)

    def test_an_undeclared_root_is_keyframed_at_the_fraction(self):
        keyframe = self.prepare(Undeclared(), 0.5)
        keyframe.assert_called_once_with(0.5)
