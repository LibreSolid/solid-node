# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Traversal-scoped, linear child naming and mutation timing."""

from unittest import TestCase

from solid2 import cube

from solid_node.core.serializer import serialize_node
from solid_node.node.assembly import AssemblyNode, _rendered_children
from solid_node.node.base import AbstractBaseNode
from solid_node.node.qualified import drive_tree


class ProbeLeaf(AbstractBaseNode):
    """The minimum rigid child each traversal can address."""

    _type = 'ProbeLeaf'
    rigid = True

    def __init__(self, name=None, action=None):
        self._explicit_name = name is not None
        self.name = name or type(self).__name__
        self._parent = None
        self.action = action
        self.operations = []
        self.color = None
        self.files = set()
        self.scope = {}

    @property
    def mtime(self):
        return 0

    def assemble(self, root=None):
        if self.action is not None:
            self.action()
        return cube(1)


class ProbeAssembly(AssemblyNode):
    """A no-artifact assembly suitable for recursive walk instrumentation."""

    def __init__(self, parts=(), name=None, action=None):
        self._explicit_name = name is not None
        self.name = name or type(self).__name__
        self._parent = None
        self._states = {}
        self.parts = parts
        self.action = action
        self.operations = []
        self.color = None
        self.files = set()
        self.scope = {}
        self.root = '.'
        self.render_calls = 0
        self.name_index_calls = 0
        self.single_name_scans = 0

    @property
    def mtime(self):
        return 0

    def render(self):
        self.render_calls += 1
        if self.action is not None:
            self.action()
        # Keep traversal membership fixed while a child mutates the public
        # ownership list.  These tests isolate the ratified naming-snapshot
        # timing; they make no claim about mutating a list being iterated.
        return list(self.parts)

    def _child_name_index(self):
        self.name_index_calls += 1
        return super()._child_name_index()

    def _attr_name_for(self, child):
        self.single_name_scans += 1
        return super()._attr_name_for(child)


class _WideFixture:

    def wide(self, count, child_type=ProbeLeaf):
        children = [child_type() for _ in range(count)]
        root = ProbeAssembly(children)
        return root, children

    def assertLinearSnapshot(self, root, children, run):
        class CountingAlias(list):

            def __init__(self, values):
                super().__init__(values)
                self.iterations = 0

            def __iter__(self):
                self.iterations += 1
                return super().__iter__()

        root.instrumented_alias = CountingAlias(children)
        run(root)
        self.assertEqual(root.name_index_calls, 1)
        self.assertEqual(root.single_name_scans, 0)
        self.assertEqual(root.instrumented_alias.iterations, 1)
        self.assertEqual(
            [child.name for child in children],
            [f'parts-{index}' for index in range(len(children))])
        self.assertTrue(all(child._parent is root for child in children))
        self.assertEqual(root.render_calls, 1)


class WideTraversalNamingTest(_WideFixture, TestCase):
    """Wide publication and simulation walks scan ownership once."""

    def test_serializer_is_linear_at_all_ratified_widths(self):
        for count in (128, 512, 2048):
            with self.subTest(count=count):
                root, children = self.wide(count)
                self.assertLinearSnapshot(
                    root, children,
                    lambda node: serialize_node(
                        node, lambda child: child.name))

    def test_driver_simulation_walk_is_linear_at_all_ratified_widths(self):
        for count in (128, 512, 2048):
            with self.subTest(count=count):
                root, children = self.wide(count, ProbeAssembly)
                self.assertLinearSnapshot(
                    root, children,
                    lambda node: drive_tree(
                        node, lambda *arguments: 0))

    def test_stl_linking_and_state_propagation_use_the_same_batch(self):
        root, children = self.wide(128)
        self.assertLinearSnapshot(
            root, children,
            lambda node: node.as_scad(node.render()))

        root, children = self.wide(128)
        self.assertLinearSnapshot(
            root, children, _rendered_children)

    def test_twenty_ticks_build_exactly_one_index_per_parent_traversal(self):
        root, children = self.wide(2048, ProbeAssembly)

        for _ in range(20):
            drive_tree(root, lambda *arguments: 0)

        self.assertEqual(root.name_index_calls, 20)
        self.assertEqual(root.single_name_scans, 0)
        self.assertEqual(
            [child.name for child in children],
            [f'parts-{index}' for index in range(len(children))])
        self.assertTrue(all(child._parent is root for child in children))

    def test_empty_batches_do_not_build_an_unused_index(self):
        consumers = (
            ('serializer', lambda node: serialize_node(
                node, lambda child: child.name)),
            ('simulation', lambda node: drive_tree(
                node, lambda *arguments: 0)),
            ('stl', lambda node: node.as_scad(node.render())),
            ('state', _rendered_children),
        )

        for name, run in consumers:
            with self.subTest(consumer=name):
                root = ProbeAssembly()
                run(root)
                self.assertEqual(root.name_index_calls, 0)
                self.assertEqual(root.single_name_scans, 0)


class NamingPrecedenceAndFreshnessTest(TestCase):

    def test_two_phase_precedence_exclusions_fallback_and_explicit_name(self):
        parent = ProbeAssembly()
        shared = ProbeLeaf()
        second = ProbeLeaf()
        private = ProbeLeaf()
        fallback = ProbeLeaf()
        explicit = ProbeLeaf(name='chosen')
        tuple_child = ProbeLeaf()
        parent.list_first = [shared, second, explicit]
        parent.tuple_alias = (tuple_child,)
        parent._private = [private]
        parent.children = [private]
        parent.direct_first = shared
        parent.direct_second = shared
        parent.list_second = [second, shared]

        parent._link_children(
            [shared, second, private, fallback, explicit, tuple_child,
             shared])

        self.assertEqual(shared.name, 'direct_first')
        self.assertEqual(second.name, 'list_first-1')
        self.assertEqual(private.name, 'ProbeLeaf')
        self.assertEqual(fallback.name, 'ProbeLeaf')
        self.assertEqual(explicit.name, 'chosen')
        self.assertEqual(tuple_child.name, 'tuple_alias-0')
        self.assertTrue(all(child._parent is parent
                            for child in (shared, second, private,
                                          fallback, explicit, tuple_child)))

    def test_single_link_remains_fresh_for_reorder_alias_and_parent_change(self):
        first_parent = ProbeAssembly()
        first = ProbeLeaf()
        second = ProbeLeaf()
        first_parent.parts = [first, second]

        first_parent._link_child(first)
        self.assertEqual(first.name, 'parts-0')

        first_parent.parts.reverse()
        first_parent._link_child(first)
        self.assertEqual(first.name, 'parts-1')

        first_parent.alias = first
        first_parent._link_child(first)
        self.assertEqual(first.name, 'alias')

        first_parent.parts.remove(first)
        first_parent.alias = second
        first_parent._link_child(first)
        self.assertEqual(first.name, 'ProbeLeaf')

        second_parent = ProbeAssembly()
        second_parent.replacement = first
        second_parent._link_child(first)
        self.assertEqual(first.name, 'replacement')
        self.assertIs(first._parent, second_parent)

    def test_batch_snapshot_is_rebuilt_after_append_remove_and_replacement(self):
        parent = ProbeAssembly()
        first, second, third = ProbeLeaf(), ProbeLeaf(), ProbeLeaf()
        parent.parts = [first, second]
        parent._link_children(parent.parts)
        self.assertEqual((first.name, second.name), ('parts-0', 'parts-1'))

        parent.parts[:] = [second, third]
        parent._link_children(parent.parts)
        self.assertEqual((second.name, third.name), ('parts-0', 'parts-1'))

        parent.parts.append(first)
        parent._link_children(parent.parts)
        self.assertEqual(first.name, 'parts-2')
        parent.parts.remove(first)
        parent._link_child(first)
        self.assertEqual(first.name, 'ProbeLeaf')


class MidTraversalMutationTest(TestCase):

    def _pair(self):
        parent = ProbeAssembly()
        sibling = ProbeLeaf()
        mutator = ProbeLeaf()
        visited = []

        def mutate():
            visited.append((mutator, mutator.name))
            parent.parts.reverse()

        def observe():
            visited.append((sibling, sibling.name))

        mutator.action = mutate
        sibling.action = observe
        parent.parts = [mutator, sibling]
        return parent, mutator, sibling, visited

    def test_stl_recursion_uses_entry_snapshot_until_next_traversal(self):
        parent, mutator, sibling, visited = self._pair()

        parent.as_scad(parent.render())
        self.assertEqual((mutator.name, sibling.name), ('parts-0', 'parts-1'))
        self.assertIs(sibling._parent, parent)
        self.assertEqual(visited, [(mutator, 'parts-0'),
                                   (sibling, 'parts-1')])

        parent.as_scad(parent.render())
        self.assertEqual((sibling.name, mutator.name), ('parts-0', 'parts-1'))

    def test_serializer_recursion_uses_entry_snapshot_until_next_traversal(self):
        parent = ProbeAssembly()
        sibling = ProbeAssembly()
        mutator = ProbeAssembly()

        def mutate():
            parent.parts.reverse()

        mutator.action = mutate
        parent.parts = [mutator, sibling]

        first = serialize_node(parent, lambda child: child.name)
        self.assertEqual([child['name'] for child in first['children']],
                         ['parts-0', 'parts-1'])
        self.assertIs(sibling._parent, parent)

        second = serialize_node(parent, lambda child: child.name)
        self.assertEqual([child['name'] for child in second['children']],
                         ['parts-1', 'parts-0'])

    def test_qualified_recursion_uses_entry_snapshot_until_next_traversal(self):
        parent = ProbeAssembly()
        sibling = ProbeAssembly()
        mutator = ProbeAssembly()

        visited = []

        def mutate():
            parent.parts.reverse()
            mutator.action = None

        mutator.action = mutate
        parent.parts = [mutator, sibling]

        drive_tree(parent, lambda *arguments: 0,
                   visit=lambda node, path: visited.append((node, path)))
        self.assertEqual((mutator.name, sibling.name), ('parts-0', 'parts-1'))
        self.assertIs(sibling._parent, parent)
        self.assertEqual(visited,
                         [(parent, ()),
                          (mutator, ('parts-0',)),
                          (sibling, ('parts-1',))])

        visited.clear()
        drive_tree(parent, lambda *arguments: 0,
                   visit=lambda node, path: visited.append((node, path)))
        self.assertEqual((sibling.name, mutator.name), ('parts-0', 'parts-1'))
        self.assertEqual(visited,
                         [(parent, ()),
                          (mutator, ('parts-1',)),
                          (sibling, ('parts-0',))])
