# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Traversal-scoped, linear child naming and mutation timing."""

from unittest import TestCase

from solid2 import cube

from solid_node.core.serializer import serialize_node
from solid_node.node.assembly import AssemblyNode, _rest_children
from solid_node.node.base import AbstractBaseNode
from solid_node.node.qualified import drive_tree

# `whole-tree-fixpoint` split the state-propagation walk in two: the
# rest-only descent that DELIVERS a `set_state` snapshot (`_rest_children`,
# renamed from `_rendered_children`, which used to call `render()` and
# therefore simulate as it delivered) and the single enumeration that
# follows. The naming/batching behaviour these tests hold linear belongs
# to the descent, under either name.
_rendered_children = _rest_children


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

    def assertLinearSnapshot(self, root, children, run, name_index_calls=1):
        class CountingAlias(list):

            def __init__(self, values):
                super().__init__(values)
                self.iterations = 0

            def __iter__(self):
                self.iterations += 1
                return super().__iter__()

        root.instrumented_alias = CountingAlias(children)
        run(root)
        self.assertEqual(root.name_index_calls, name_index_calls)
        self.assertEqual(root.single_name_scans, 0)
        # One iteration per `_link_children` call: as many as index builds.
        self.assertEqual(root.instrumented_alias.iterations, name_index_calls)
        self.assertEqual(
            [child.name for child in children],
            [f'parts-{index}' for index in range(len(children))])
        self.assertTrue(all(child._parent is root for child in children))
        self.assertEqual(root.render_calls, 1)


class WideTraversalNamingTest(_WideFixture, TestCase):
    """Wide publication and simulation walks scan ownership once."""

    def test_serializer_is_linear_at_all_ratified_widths(self):
        # `render()` links root's own children now (`whole-tree-fixpoint`);
        # `serialize_node` still links again on the same batch, needed
        # for a render that creates a fresh child -- two index builds
        # per call, not one, still linear in the child count.
        for count in (128, 512, 2048):
            with self.subTest(count=count):
                root, children = self.wide(count)
                self.assertLinearSnapshot(
                    root, children,
                    lambda node: serialize_node(
                        node, lambda child: child.name),
                    name_index_calls=2)

    def test_driver_simulation_walk_is_linear_at_all_ratified_widths(self):
        # `whole-tree-fixpoint`: `drive_tree` now delivers every node's
        # snapshot over a REST-ONLY walk (so a descendant's driver is
        # bound before render() can cascade into its phase), then
        # renders the tree once for the real enumeration -- two linking
        # passes over root's own children instead of one, each still
        # O(children), so the walk stays LINEAR, at twice the constant.
        for count in (128, 512, 2048):
            with self.subTest(count=count):
                root, children = self.wide(count, ProbeAssembly)
                self.assertLinearSnapshot(
                    root, children,
                    lambda node: drive_tree(
                        node, lambda *arguments: 0),
                    name_index_calls=2)

    def test_stl_linking_and_state_propagation_use_the_same_batch(self):
        # `render()` links its own children now (`whole-tree-fixpoint`);
        # `as_scad` still links again on the same batch it is handed, so
        # this specific walk costs two index builds, not one.
        root, children = self.wide(128)
        self.assertLinearSnapshot(
            root, children,
            lambda node: node.as_scad(node.render()),
            name_index_calls=2)

        root, children = self.wide(128)
        self.assertLinearSnapshot(
            root, children, _rendered_children)

    def test_twenty_ticks_build_exactly_one_index_per_parent_traversal(self):
        root, children = self.wide(2048, ProbeAssembly)

        for _ in range(20):
            drive_tree(root, lambda *arguments: 0)

        # Two index builds per tick (deliver's rest-only walk, then the
        # enumeration's own render()), see test_driver_simulation_walk...
        self.assertEqual(root.name_index_calls, 40)
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
        # `mutator` and `sibling` are `ProbeAssembly` (AssemblyNode) here,
        # unlike `_pair()`'s plain `ProbeLeaf`s above: `whole-tree-fixpoint`
        # makes `parent.render()` itself drive `mutator`'s own phase as
        # part of the SAME call (every phase now precedes the first
        # geometry read), so `mutator`'s action -- and the mutation it
        # causes -- has ALREADY happened by the time `render()` returns
        # to the serializer, before its own (still necessary, for a
        # render that creates a fresh child) re-link ever runs. There is
        # no longer an "entry snapshot" separate from that: the FIRST
        # traversal already sees the reversed order this walk was
        # written to expect only on a later, separate one.
        parent = ProbeAssembly()
        sibling = ProbeAssembly()
        mutator = ProbeAssembly()

        def mutate():
            parent.parts.reverse()

        mutator.action = mutate
        parent.parts = [mutator, sibling]

        first = serialize_node(parent, lambda child: child.name)
        self.assertEqual([child['name'] for child in first['children']],
                         ['parts-1', 'parts-0'])
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

        # As above: `mutator`'s action fires during `drive_tree`'s own
        # rest-only delivery pass (which discovers structure through
        # the same render() every copy runs once), before the trailing
        # `root.render()` re-links against the now-mutated `parts` --
        # so the NAMES it leaves behind reflect the mutation, same as
        # the serializer above. `visited`, recorded during delivery,
        # still reflects the entry order: the read that matters for a
        # qualified id happens once, at delivery, not at this re-link.
        drive_tree(parent, lambda *arguments: 0,
                   visit=lambda node, path: visited.append((node, path)))
        self.assertEqual((mutator.name, sibling.name), ('parts-1', 'parts-0'))
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
