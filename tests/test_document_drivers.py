# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Schema v2: symbolic driver serialization and the driver table.

An operation records whatever value render() computed, so a document
serialized from a numerically stepped node would publish the constants
of one instant -- exactly the defect `$t` already had, and export
already solved by returning the node to symbolic animation time before
serializing. Drivers get the same guarantee, through the same producer
obligation: bind every declared driver to its qualified token, render,
serialize, restore.

The binding goes through an internal path, never `set_state`.
`_validate_state` goes on judging every snapshot value a plain number,
because that is what keeps a bound pose a pure function of numbers; a
symbolic value is deliberately not one. Two doors, not one relaxed door.

The `.scad` path is unchanged and is regression-tested here: it
substitutes bound driver values numerically and keeps `$t` live, which
the spike proved needs no machinery at all.
"""

import json
import os

from solid_node.core.export import export_node
from solid_node.core.serializer import (
    DOCUMENT_VERSION, drivers_table, instructions_table, serialize_node,
    symbolic_document, symbolic_drivers,
)
from solid_node.simulation.enumeration import bind_declared_defaults

from .base import BaseNodeTest
from .meta_project.axis import Axis as RootAxis
from .meta_project.machine import Machine
from .meta_project.nested import Nested


def operations_of(document, *path):
    node = document
    for name in path:
        node = next(child for child in node['children']
                    if child['name'] == name)
    return node['operations']


class SymbolicSerializationTest(BaseNodeTest):

    def document(self, node):
        with symbolic_drivers(node) as declarations:
            root = serialize_node(node, lambda rigid: rigid.name)
        return root, declarations

    def test_a_stepped_node_still_serializes_driver_expressions(self):
        """The producer guarantee, extended from `$t` to drivers: the
        numeric snapshot a simulation bound must not reach the wire."""
        machine = Machine()
        machine.set_state(**{'x_axis.motor': 8000, 'y_axis.motor': 2000})

        root, _ = self.document(machine)

        self.assertEqual(operations_of(root, 'x_axis', 'carriage'),
                         [['t', ['(x_axis.motor * 0.0125)', '0', '0']]])
        self.assertEqual(operations_of(root, 'x_axis', 'pulley'),
                         [['r', '(x_axis.motor * 0.1125)', [0, 0, 1]]])

    def test_sibling_instances_serialize_distinct_ids(self):
        machine = Machine()
        bind_declared_defaults(machine)

        root, declarations = self.document(machine)

        self.assertEqual(operations_of(root, 'y_axis', 'carriage'),
                         [['t', ['(y_axis.motor * 0.0125)', '0', '0']]])
        self.assertEqual(sorted(declarations),
                         ['x_axis.motor', 'y_axis.motor'])

    def test_animation_time_stays_symbolic_beside_a_driver(self):
        machine = Machine()
        bind_declared_defaults(machine)

        root, _ = self.document(machine)

        self.assertEqual(
            operations_of(root, 'x_axis', 'cover'),
            [['t', ['((5.0 * cos((360.0 * $t))) + '
                    '((x_axis.motor * 0.0125) * 0.1))', '0', '0']]])

    def test_the_prior_binding_is_restored_afterwards(self):
        machine = Machine()
        machine.set_state(**{'x_axis.motor': 8000, 'y_axis.motor': 2000})

        self.document(machine)

        self.assertEqual(machine.x_axis.motor, 8000)
        self.assertEqual(machine.y_axis.motor, 2000)
        self.assertEqual(
            [op.serialized for op in machine.x_axis.carriage.operations],
            [['t', ['100.0', '0', '0']]])

    def test_the_numeric_door_is_not_relaxed(self):
        """A token still cannot be bound through `set_state`: the
        symbolic mode is a different path, not a weaker validator."""
        from solid_node.node.qualified import DriverToken

        machine = Machine()
        with self.assertRaises(TypeError):
            machine.set_state(**{'x_axis.motor': DriverToken('x_axis.motor')})

    def test_a_driverless_tree_is_left_alone(self):
        node = Nested()

        with symbolic_drivers(node) as declarations:
            self.assertEqual(declarations, {})

        self.assertEqual(node.inner.cube.operations, [])


class DriverTableTest(BaseNodeTest):

    def test_the_table_carries_the_declaration_verbatim(self):
        machine = Machine()
        with symbolic_drivers(machine) as declarations:
            table = drivers_table(declarations)

        self.assertEqual(sorted(table), ['x_axis.motor', 'y_axis.motor'])
        self.assertEqual(table['x_axis.motor'], {
            'default': 8000,
            'range': [0, 100],
            'unit': 'ustep',
            'dtype': 'int',
            'scale': 40.0 / 3200,
        })

    def test_the_range_travels_in_design_units_unconverted(self):
        """ADR-056 stage 3c: `range` is stated in DESIGN units and the
        producer publishes it as declared, beside the `scale` and
        `default` that are native. A presenter converts once, the way
        `Driver.native` does; a producer converting first would leave
        the client unable to tell which reading it received."""
        machine = Machine()
        with symbolic_drivers(machine) as declarations:
            table = drivers_table(declarations)
            declaration = declarations['x_axis.motor']

        published = table['x_axis.motor']
        self.assertEqual(published['range'], [0, 100])
        # 100 design millimetres of travel IS the native default: the
        # two readings of one end, related by the published scale.
        self.assertEqual(declaration.native(published['range'][1]),
                         published['default'])

    def test_the_table_never_clamps_a_bound_value_to_the_range(self):
        """A document serialized from a crashed machine still publishes
        the state it had: the range bounds a slider's travel, never the
        value the expressions read."""
        machine = Machine()
        machine.set_state(**{'x_axis.motor': -400, 'y_axis.motor': 20000})

        with symbolic_drivers(machine) as declarations:
            table = drivers_table(declarations)

        self.assertEqual(table['x_axis.motor']['range'], [0, 100])
        self.assertEqual(machine.x_axis.motor, -400)
        self.assertEqual(machine.y_axis.motor, 20000)

    def test_the_table_is_json_serializable(self):
        machine = Machine()
        with symbolic_drivers(machine) as declarations:
            table = drivers_table(declarations)

        self.assertEqual(json.loads(json.dumps(table)), table)


class InstructionTableTest(BaseNodeTest):
    """Schema v2's `instructions` table (ADR-056 stage 3b).

    An instruction is what a button press means, and a client that can
    evaluate driver expressions can also run one: the document therefore
    has to say which instructions exist, which drivers each moves, and
    for how long. The names and the target keys are QUALIFIED by the
    declaring node's path, for the same reason the driver ids are --
    `Home` on two axis instances means two different motions, and the
    key a client sends must be the key the bank holds.

    Targets stay in DESIGN units verbatim: the conversion to native
    state belongs to the driver declaration, which the table beside this
    one publishes, so a client converts exactly once and exactly as
    `Driver.native` does.
    """

    def table(self, node):
        with symbolic_document(node) as (_, instructions):
            return instructions_table(instructions)

    def test_the_table_qualifies_names_and_targets(self):
        self.assertEqual(self.table(Machine()), {
            'x_axis.Home': {'targets': {'x_axis.motor': 0.0},
                            'duration': 2.0},
            'y_axis.Home': {'targets': {'y_axis.motor': 0.0},
                            'duration': 2.0},
        })

    def test_a_root_declared_instruction_keeps_its_bare_name(self):
        self.assertEqual(self.table(RootAxis()), {
            'Home': {'targets': {'x': 0.0}, 'duration': 2.0},
            'Crash': {'targets': {'x': -5.0}, 'duration': 2.0},
        })

    def test_an_instructionless_tree_publishes_an_empty_table(self):
        self.assertEqual(self.table(Nested()), {})

    def test_the_table_is_json_serializable(self):
        table = self.table(Machine())

        self.assertEqual(json.loads(json.dumps(table)), table)

    def test_a_driver_declaring_export_publishes_the_instructions(self):
        machine = Machine()
        bind_declared_defaults(machine)
        out_dir = os.path.join(self.build_dir, 'export_out')

        manifest = export_node(machine, out_dir, widget=False)

        self.assertEqual(manifest['instructions'], {
            'x_axis.Home': {'targets': {'x_axis.motor': 0.0},
                            'duration': 2.0},
            'y_axis.Home': {'targets': {'y_axis.motor': 0.0},
                            'duration': 2.0},
        })

    def test_an_instructionless_export_publishes_an_empty_table(self):
        out_dir = os.path.join(self.build_dir, 'export_out')

        manifest = export_node(Nested(), out_dir, widget=False)

        self.assertEqual(manifest['version'], 2)
        self.assertEqual(manifest['drivers'], {})
        self.assertEqual(manifest['instructions'], {})

    def test_every_target_id_appears_in_the_drivers_table(self):
        """The two tables are one contract: a target a client cannot
        resolve to a declared driver is a document it cannot run."""
        machine = Machine()
        bind_declared_defaults(machine)
        out_dir = os.path.join(self.build_dir, 'export_out')

        manifest = export_node(machine, out_dir, widget=False)

        targeted = {identifier
                    for entry in manifest['instructions'].values()
                    for identifier in entry['targets']}
        self.assertTrue(targeted)
        self.assertLessEqual(targeted, set(manifest['drivers']))


class DocumentVersionTest(BaseNodeTest):

    def test_the_shared_schema_version_is_two(self):
        self.assertEqual(DOCUMENT_VERSION, 2)

    def test_a_driver_declaring_export_publishes_the_table(self):
        machine = Machine()
        bind_declared_defaults(machine)
        out_dir = os.path.join(self.build_dir, 'export_out')

        manifest = export_node(machine, out_dir, widget=False)

        self.assertEqual(manifest['version'], 2)
        self.assertEqual(sorted(manifest['drivers']),
                         ['x_axis.motor', 'y_axis.motor'])
        self.assertEqual(
            operations_of(manifest['root'], 'x_axis', 'pulley'),
            [['r', '(x_axis.motor * 0.1125)', [0, 0, 1]]])

    def test_every_referenced_id_appears_in_the_table(self):
        machine = Machine()
        bind_declared_defaults(machine)
        out_dir = os.path.join(self.build_dir, 'export_out')

        manifest = export_node(machine, out_dir, widget=False)

        referenced = set()

        def walk(node):
            for operation in node['operations']:
                values = ([operation[1]] if operation[0] == 'r'
                          else operation[1])
                for value in values:
                    for identifier in manifest['drivers']:
                        if identifier in value:
                            referenced.add(identifier)
            for child in node.get('children', ()):
                walk(child)

        walk(manifest['root'])
        self.assertEqual(referenced, set(manifest['drivers']))


class ScadSubstitutionTest(BaseNodeTest):
    """Spike verdict 4 as a regression test: the OpenSCAD path is
    untouched by schema v2 -- driver terms collapse to numerals because
    Python evaluates them eagerly, and `$t` stays live."""

    def scad(self, snapshot):
        machine = Machine()
        machine.set_state(**snapshot)
        machine.assemble()
        return machine.scad_code

    def test_bound_drivers_substitute_numerically_and_time_stays_live(self):
        code = self.scad({'x_axis.motor': 8000, 'y_axis.motor': 2000})

        self.assertNotIn('motor', code)
        self.assertIn('$t', code)
        self.assertIn('100.0', code)
        self.assertIn('25.0', code)

    def test_two_snapshots_of_one_model_emit_different_scad(self):
        first = self.scad({'x_axis.motor': 8000, 'y_axis.motor': 2000})
        second = self.scad({'x_axis.motor': 1600, 'y_axis.motor': 6400})

        self.assertNotEqual(first, second)
        self.assertIn('$t', second)
