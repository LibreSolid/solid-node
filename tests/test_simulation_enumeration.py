# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The one tree-wide driver enumeration authority.

`declared_drivers(cls)` reads a single class, which is the whole of
what stage 2 needed: a machine that declared its drivers on the root.
A real machine declares them on its mechanisms, and the root may
declare none at all -- the spike's `Sim(machine, dt)` failed on its own
first render for exactly that reason.

This walk is the cure and, deliberately, the ONLY one: the simulation
state bank, instruction-target resolution, the loader's default
binding, and the serialized document's driver table all read it, so the
id in the document and the key in the bank are the same string by
construction rather than by two implementations agreeing.

It binds each node's declared defaults as it descends, because it has
to render to find children and a state-consuming assembly cannot be
rendered under no snapshot at all.
"""

from solid_node.node.qualified import DriverIdError
from solid_node.simulation.enumeration import (
    bind_declared_defaults, qualified_drivers, qualified_instructions,
)

from .base import BaseNodeTest
from .meta_project.axis import Axis as RootAxis
from .meta_project.machine import Axis, ListMachine, Machine
from .meta_project.nested import Nested


class QualifiedEnumerationTest(BaseNodeTest):

    def test_drivers_on_descendants_are_enumerated_qualified(self):
        found = qualified_drivers(Machine())

        self.assertEqual(sorted(found), ['x_axis.motor', 'y_axis.motor'])
        declaration = found['x_axis.motor']
        self.assertEqual(declaration.default, 8000)
        # Design units: 100mm of travel, the far end of which is the
        # native default of 8000 microsteps beside it.
        self.assertEqual(declaration.range, (0, 100))
        self.assertEqual(declaration.unit, 'ustep')
        self.assertIs(declaration.dtype, int)
        self.assertAlmostEqual(declaration.scale, 40.0 / 3200)

    def test_a_root_declared_driver_keeps_its_bare_name(self):
        self.assertEqual(sorted(qualified_drivers(RootAxis())), ['x'])

    def test_enumeration_binds_the_declared_defaults_as_it_walks(self):
        """A driver-declaring tree cannot be walked without binding:
        finding the children means rendering, and the render reads the
        driver. So the walk binds the declarations' own defaults."""
        machine = Machine()

        qualified_drivers(machine)

        self.assertEqual(machine.x_axis.motor, 8000)
        self.assertEqual(machine.y_axis.motor, 8000)

    def test_an_illegal_id_segment_fails_loudly(self):
        with self.assertRaises(DriverIdError) as caught:
            qualified_drivers(ListMachine())

        self.assertIn('axes-0', str(caught.exception))

    def test_instructions_qualify_by_the_declaring_node(self):
        found = qualified_instructions(Machine())

        self.assertEqual(sorted(found), ['x_axis.Home', 'y_axis.Home'])
        node, path, instruction = found['x_axis.Home']
        self.assertEqual(path, ('x_axis',))
        self.assertEqual(instruction.targets, {'motor': 0.0})

    def test_a_root_declared_instruction_keeps_its_bare_name(self):
        self.assertEqual(sorted(qualified_instructions(RootAxis())),
                         ['Crash', 'Home'])


class DefaultBindingTest(BaseNodeTest):
    """What the build/test loader calls: bind across the tree, and
    leave a tree that declares nothing completely alone."""

    def test_a_driver_declaring_tree_binds_its_defaults(self):
        machine = Machine()

        self.assertEqual(sorted(bind_declared_defaults(machine)),
                         ['x_axis.motor', 'y_axis.motor'])
        self.assertEqual(machine.x_axis.motor, 8000)

    def test_a_driverless_tree_is_not_even_rendered(self):
        """`Nested` declares no driver anywhere, so loading it must do
        exactly what it always did: nothing. Not even the walk's render,
        whose operations would be a behaviour change of its own."""
        node = Nested()

        self.assertEqual(bind_declared_defaults(node), {})
        # Nothing bound (time still reads symbolically) and nothing
        # rendered (the walk's translate would be here otherwise).
        self.assertEqual(str(node.time), '$t')
        self.assertEqual(node.inner.cube.operations, [])
