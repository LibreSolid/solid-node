# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Framework-level coverage for the inverse of set_keyframe.

`set_keyframe` used to be a one-way door: `AssemblyNode.time` reads
`_time` when present and falls back to solid2's `$t` only through an
AttributeError, and nothing ever removed `_time`. A host that keyframed
a node -- to read a mesh, run a test, or render one instant -- could
never get the symbolic timeline back, so anything it published
afterwards carried the constants that keyframe computed instead of the
`$t` expressions.

These tests sit at the same layer as test_conrod_symbolic.py: real
fixtures, assembled in-process, with the serialized operations
inspected directly rather than parsed out of `solid test` output.
"""

from solid_node.node import AssemblyNode

from .base import BaseNodeTest
from .meta_project.conrod import Conrod
from .meta_project.nested import Nested
from .meta_project.parts import Cube


def rotations(node):
    return [op for op in node.operations if op.serialized[0] == 'r']


def translations(node):
    return [op for op in node.operations if op.serialized[0] == 't']


class NonListRenderAssembly(AssemblyNode):
    """An assembly whose render() returns a single node rather than a
    list. `serialize_node` tolerates this deliberately (the partial-node
    representation lifecycle validation handles), so the keyframe
    methods must tolerate it too rather than raising while iterating."""

    def __init__(self):
        self.cube = Cube()
        super().__init__()

    def render(self):
        return self.cube


class ClearKeyframeRestoresSymbolicTimeTest(BaseNodeTest):

    def test_nested_assemblies_return_to_symbolic_time(self):
        node = Nested()
        node.set_keyframe(0.5)
        self.assertEqual(node.time, 0.5)
        self.assertEqual(node.inner.time, 0.5)

        node.clear_keyframe()

        # Symbolic time is solid2's $t, an OpenSCADConstant -- not a
        # float, and it must have reached the nested assembly too.
        self.assertNotIsInstance(node.time, float)
        self.assertNotIsInstance(node.inner.time, float)
        self.assertEqual(str(node.time), '$t')
        self.assertEqual(str(node.inner.time), '$t')

    def test_cleared_operations_match_a_never_keyframed_render(self):
        fresh = Nested()
        # Nested.render() returns the inner assembly; the operation
        # under test is applied by Inner.render().
        fresh.render()
        fresh.inner.render()
        expected = [op.serialized for op in fresh.inner.cube.operations]
        self.assertEqual(expected, [['t', ['(10 * $t)', '0', '0']]])

        node = Nested()
        node.set_keyframe(0.5)
        self.assertEqual(
            [op.serialized for op in node.inner.cube.operations],
            [['t', ['5.0', '0', '0']]])

        node.clear_keyframe()

        self.assertEqual(
            [op.serialized for op in node.inner.cube.operations], expected)

    def test_clearing_restores_a_non_linear_symbolic_expression(self):
        fresh = Conrod()
        fresh.render()
        expected = rotations(fresh.rod)[0].serialized[1]
        self.assertEqual(expected, 'asin((0.25 * sin((360.0 * $t))))')

        node = Conrod()
        node.set_keyframe(0.1)
        # Keyframed, the same expression is the numeric swing angle.
        self.assertNotIn('$t', rotations(node.rod)[0].serialized[1])

        node.clear_keyframe()

        self.assertEqual(rotations(node.rod)[0].serialized[1], expected)
        # The static placement applied by render() survives untouched,
        # exactly once.
        self.assertEqual([op.serialized for op in translations(node.rod)],
                         [['t', ['2', '0', '0']]])

    def test_a_keyframe_can_be_applied_again_after_clearing(self):
        node = Conrod()
        node.set_keyframe(0.1)
        keyframed = rotations(node.rod)[0].serialized[1]

        node.clear_keyframe()
        node.set_keyframe(0.1)

        self.assertEqual(node.time, 0.1)
        self.assertEqual(rotations(node.rod)[0].serialized[1], keyframed)

    def test_keyframe_cycles_do_not_accumulate_operations(self):
        node = Conrod()

        for instant in (0.1, 0.25, 0.4):
            node.set_keyframe(instant)
            node.clear_keyframe()

        # One driven rotation and one static translation, no matter how
        # many times the subtree was keyframed and released.
        self.assertEqual(len(rotations(node.rod)), 1)
        self.assertEqual(len(translations(node.rod)), 1)
        self.assertEqual(rotations(node.rod)[0].serialized[1],
                         'asin((0.25 * sin((360.0 * $t))))')


class PartialNodeKeyframeToleranceTest(BaseNodeTest):
    """Neither keyframe method may raise on an assembly whose render()
    returns something that is not a list or tuple."""

    def test_set_keyframe_tolerates_a_non_list_render(self):
        NonListRenderAssembly().set_keyframe(0.5)

    def test_clear_keyframe_tolerates_a_non_list_render(self):
        NonListRenderAssembly().clear_keyframe()
