# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""An internal render() that returns nothing, and structural omission.

On a declarative class render() positions and selects. When it returns
None the children are the realized declared children in declaration
order minus those it omitted; a returned list keeps today's contract to
the letter; a class with nothing to position needs no render() at all.
Structure varies with parameters, never with time: an omitted set that
changes between renders of one instance raises.
"""

from solid2 import cube

from solid_node.core.serializer import serialize_node
from solid_node.node import AssemblyNode, FusionNode, Solid2Node
from solid_node.node.declarative import StructureError
from solid_node.parameters import Flag, Length

from .base import BaseNodeTest
from .declarative_project.engine import Cylinders, Engine
from .declarative_project.windmill import Windmill


class Box(Solid2Node):

    size = Length(1.0, min=0)

    def render(self):
        return cube(self.size, center=True)


def names(node):
    return [child.name for child in node.render()]


class RenderReturnsNothingTest(BaseNodeTest):

    def test_a_grouping_node_needs_no_methods(self):
        class Group(AssemblyNode):
            first = Box()
            second = Box(size=2.0)
            third = Box(size=3.0)

        group = Group()
        rendered = group.render()

        self.assertEqual([child.name for child in rendered],
                         ['first', 'second', 'third'])
        self.assertIs(rendered[1], group.second)
        self.assertIs(group.second._parent, None)
        document = serialize_node(group, lambda rigid: rigid.name)
        self.assertEqual([child['name'] for child in document['children']],
                         ['first', 'second', 'third'])

    def test_positioning_without_a_return_is_absolute_across_keyframes(self):
        class Spinner(AssemblyNode):
            box = Box()

            def render(self):
                self.box.rotate(360 * self.time, [0, 0, 1])

        spinner = Spinner()

        spinner.set_keyframe(0.25)
        first = [op.serialized for op in spinner.box.operations]
        spinner.set_keyframe(0.5)
        second = [op.serialized for op in spinner.box.operations]

        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)
        self.assertNotEqual(first, second)
        self.assertEqual(names(spinner), ['box'])

    def test_a_returned_list_keeps_its_contract(self):
        class Picky(AssemblyNode):
            kept = Box()
            dropped = Box(size=2.0)

            def render(self):
                return [self.kept]

        picky = Picky()
        picky.assemble()

        self.assertEqual([child.name for child in picky.children], ['kept'])
        self.assertIsNone(picky.dropped._parent)

    def test_the_build_sees_the_substituted_list(self):
        engine = Engine(count=4)
        engine.assemble()

        self.assertEqual([child.name for child in engine.children],
                         ['cylinders', 'block'])
        self.assertEqual([child.name for child in engine.cylinders.children],
                         ['units-0', 'units-1', 'units-2', 'units-3'])
        self.assertIs(engine.block._parent, engine)

    def test_a_fusion_positions_its_declared_parts(self):
        class Weldment(FusionNode):
            base = Box(size=4.0)
            post = Box(size=2.0)

            def render(self):
                self.post.translate([0, 0, 3.0])

        weldment = Weldment()
        weldment.assemble()

        self.assertEqual([child.name for child in weldment.children],
                         ['base', 'post'])
        self.assertEqual([op.serialized for op in weldment.post.operations],
                         [['t', ['0', '0', '3.0']]])
        self.assertIn('union', weldment.scad_code)

    def test_a_leaf_render_returning_none_is_still_an_error(self):
        class Empty(Solid2Node):
            def render(self):
                return None

        with self.assertRaises(Exception) as ctx:
            Empty().assemble()
        self.assertIn('Empty', str(ctx.exception))

    def test_a_legacy_render_is_untouched(self):
        class Legacy(AssemblyNode):
            def __init__(self):
                self.box = Box()
                super().__init__()

            def render(self):
                return [self.box]

        legacy = Legacy()

        rendered = legacy.render()

        # The author's list, as returned: no substitution, and the name
        # is still derived at link time as it always was.
        self.assertEqual(rendered, [legacy.box])
        self.assertEqual(legacy.box.name, 'Box')


class OmissionTest(BaseNodeTest):

    def test_a_flag_removes_a_part(self):
        installed, bare = Windmill(), Windmill(guard_installed=False)

        self.assertEqual(names(installed), ['tower', 'rotor', 'guard'])
        self.assertEqual(names(bare), ['tower', 'rotor'])

        bare.assemble()
        self.assertEqual([child.name for child in bare.children],
                         ['tower', 'rotor'])
        self.assertIsNone(bare.guard._parent)
        self.assertNotIn(bare.guard.uniq_id, bare.scad_code)
        document = serialize_node(bare, lambda rigid: rigid.name)
        self.assertEqual([child['name'] for child in document['children']],
                         ['tower', 'rotor'])

    def test_omission_is_decided_afresh_each_render(self):
        bare = Windmill(guard_installed=False)

        bare.render()
        bare.render()

        self.assertEqual(names(bare), ['tower', 'rotor'])
        self.assertEqual(names(Windmill()), ['tower', 'rotor', 'guard'])

    def test_omission_under_a_fused_solid(self):
        class Weldment(FusionNode):
            with_post = Flag(True)
            base = Box(size=4.0)
            post = Box(size=2.0)

            def render(self):
                if not self.with_post:
                    self.post.omit()

        weldment = Weldment(with_post=False)
        weldment.assemble()

        self.assertEqual([child.name for child in weldment.children],
                         ['base'])
        self.assertNotIn(weldment.post.uniq_id, weldment.scad_code)
        self.assertNotEqual(Weldment().uniq_id, weldment.uniq_id)

    def test_time_cannot_change_structure(self):
        class Blinker(AssemblyNode):
            box = Box()
            lid = Box(size=2.0)

            def render(self):
                if self.time > 0.5:
                    self.lid.omit()

        blinker = Blinker()
        blinker.set_keyframe(0.25)

        with self.assertRaises(StructureError) as ctx:
            blinker.set_keyframe(0.75)
        message = str(ctx.exception)
        self.assertIn('Blinker', message)
        self.assertIn('lid', message)

    def test_indices_never_renumber(self):
        class Bank(AssemblyNode):
            units = Box().repeat(8)

            def render(self):
                self.units[3].omit()

        bank = Bank()
        rendered = bank.render()

        self.assertEqual([child.name for child in rendered],
                         [f'units-{i}' for i in (0, 1, 2, 4, 5, 6, 7)])
        self.assertEqual(bank.units[4].name, 'units-4')
        self.assertEqual(bank.units[4].uniq_id, bank.units[3].uniq_id)

    def test_omitting_a_repeated_member_leaves_the_rest_in_the_build(self):
        class Bank(AssemblyNode):
            units = Box().repeat(3)

            def render(self):
                self.units[1].omit()

        bank = Bank()
        bank.assemble()

        self.assertEqual([child.name for child in bank.children],
                         ['units-0', 'units-2'])

    def test_the_whole_engine_builds(self):
        cylinders = Cylinders(count=2)
        cylinders.assemble()
        cylinders.build_stls()

        for unit in cylinders.units:
            self.assertGreater(unit.piston.mesh.volume, 0)
