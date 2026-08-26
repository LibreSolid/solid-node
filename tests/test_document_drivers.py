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
    DOCUMENT_VERSION, drivers_table, serialize_node, symbolic_drivers,
)
from solid_node.simulation.enumeration import bind_declared_defaults

from .base import BaseNodeTest
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

        self.assertEqual(machine.x_axis.state['motor'], 8000)
        self.assertEqual(machine.y_axis.state['motor'], 2000)
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
            'range': [0, 8000],
            'unit': 'ustep',
            'dtype': 'int',
            'scale': 40.0 / 3200,
        })

    def test_the_table_is_json_serializable(self):
        machine = Machine()
        with symbolic_drivers(machine) as declarations:
            table = drivers_table(declarations)

        self.assertEqual(json.loads(json.dumps(table)), table)


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
