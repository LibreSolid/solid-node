# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for child-name derivation (skill-repo improvements.md
#16): two children of the same class under one parent used to
collide in the viewer's name-addressed tree, because node.name
defaulted to the class name for every instance, regardless of how
many parents used that class. The ratified replacement derives
node.name by this hierarchy:

    1. an explicit name= kwarg (always wins),
    2. else the attribute name the PARENT instance holds the child
       under (introspected off the parent's __dict__ in definition
       order); a child held inside a list/tuple attribute gets
       `<attr>-<index>`,
    3. else the class name (today's behavior), if the child isn't
       referenced by any of the parent's attributes at all.

These are plain unit tests against real node instances, so
AbstractBaseNode._link_child / _attr_name_for run for real -- but
LeafNode.assemble() only needs to render+serialize scad (no openscad
subprocess), so no STL is ever built here (same pattern as
tests/test_uniq_id.py).
"""

from solid_node.node import AssemblyNode, Solid2Node
from solid2 import cube
from .base import BaseNodeTest


class Cube(Solid2Node):

    def __init__(self, size=1.0, name=None):
        self.size = size
        super().__init__(size=size, name=name)

    def render(self):
        return cube(self.size, center=True)


class ExplicitNameWins(AssemblyNode):
    """name= always wins over attribute-derived naming, even though
    `self.gear` would otherwise derive the name `gear`."""

    def __init__(self):
        self.gear = Cube(name='drive_gear')
        super().__init__()

    def render(self):
        return [self.gear]


class PlainAttributeNaming(AssemblyNode):
    """A child held as a plain attribute is named after that
    attribute, not its class."""

    def __init__(self):
        self.input_gear = Cube()
        self.output_gear = Cube()
        super().__init__()

    def render(self):
        return [self.input_gear, self.output_gear]


class ListAttributeNaming(AssemblyNode):
    """A child held inside a list attribute is named `<attr>-<index>`."""

    def __init__(self):
        self.counter_gears = [Cube(), Cube(), Cube()]
        super().__init__()

    def render(self):
        return list(self.counter_gears)


class TupleAttributeNaming(AssemblyNode):
    """Tuples get the same `<attr>-<index>` treatment as lists."""

    def __init__(self):
        self.posts = (Cube(), Cube())
        super().__init__()

    def render(self):
        return list(self.posts)


class ClassNameFallback(AssemblyNode):
    """A child built inline in render() -- never assigned to any
    parent attribute -- keeps today's class-name default."""

    def __init__(self):
        super().__init__()

    def render(self):
        return [Cube()]


class PlainAttributePreferredOverList(AssemblyNode):
    """The same child object referenced by both a plain attribute and
    a list attribute: the plain attribute wins."""

    def __init__(self):
        self.gears = [Cube()]
        self.primary = self.gears[0]
        super().__init__()

    def render(self):
        return [self.primary]


class FirstPlainAttributeWins(AssemblyNode):
    """The same child object referenced by TWO plain attributes: the
    first one in definition (__dict__) order wins."""

    def __init__(self):
        shared = Cube()
        self.first = shared
        self.second = shared
        super().__init__()

    def render(self):
        return [self.first]


class ExplicitNameWinsTest(BaseNodeTest):

    def test_explicit_name_beats_attribute_derivation(self):
        node = ExplicitNameWins()
        node.assemble()
        self.assertEqual(node.gear.name, 'drive_gear')


class PlainAttributeNamingTest(BaseNodeTest):

    def test_children_named_after_holding_attribute(self):
        node = PlainAttributeNaming()
        node.assemble()
        self.assertEqual(node.input_gear.name, 'input_gear')
        self.assertEqual(node.output_gear.name, 'output_gear')


class ListAttributeNamingTest(BaseNodeTest):

    def test_list_members_named_attr_dash_index(self):
        node = ListAttributeNaming()
        node.assemble()
        names = [child.name for child in node.counter_gears]
        self.assertEqual(
            names,
            ['counter_gears-0', 'counter_gears-1', 'counter_gears-2'])


class TupleAttributeNamingTest(BaseNodeTest):

    def test_tuple_members_named_attr_dash_index(self):
        node = TupleAttributeNaming()
        node.assemble()
        names = [child.name for child in node.posts]
        self.assertEqual(names, ['posts-0', 'posts-1'])


class ClassNameFallbackTest(BaseNodeTest):

    def test_child_not_in_dict_keeps_class_name(self):
        node = ClassNameFallback()
        node.assemble()
        (child,) = node.children
        self.assertEqual(child.name, 'Cube')


class MultipleAttributePreferenceTest(BaseNodeTest):

    def test_plain_attribute_preferred_over_list_membership(self):
        node = PlainAttributePreferredOverList()
        node.assemble()
        self.assertEqual(node.primary.name, 'primary')

    def test_first_plain_attribute_wins_among_several(self):
        node = FirstPlainAttributeWins()
        node.assemble()
        # The same object is referenced under two attribute names --
        # only the first one (definition order) wins.
        self.assertIs(node.first, node.second)
        self.assertEqual(node.first.name, 'first')


class IdempotentAcrossReassembleTest(BaseNodeTest):

    def test_deriving_twice_does_not_stack_suffixes(self):
        node = PlainAttributeNaming()
        node.assemble()
        self.assertEqual(node.input_gear.name, 'input_gear')

        # Force a second full assemble()/as_scad() pass, the way
        # tests/base.py's load_solid() does after triggering STLs.
        node._assembled = False
        node.assemble()

        self.assertEqual(node.input_gear.name, 'input_gear')
        self.assertEqual(node.output_gear.name, 'output_gear')

    def test_list_members_keep_stable_names_across_reassemble(self):
        node = ListAttributeNaming()
        node.assemble()
        node._assembled = False
        node.assemble()

        names = [child.name for child in node.counter_gears]
        self.assertEqual(
            names,
            ['counter_gears-0', 'counter_gears-1', 'counter_gears-2'])
