# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Loading binds declared driver defaults.

A driver-declaring assembly's render() reads its drivers, so it cannot
be rendered at all until something binds them -- and `solid build`,
`solid test` and `solid develop` all render long before any simulation
exists. Until this change the assembly had to state its own opening
snapshot in `__init__`, which is the declarations repeated in a second
place and drifting from them.

The binding lives in the loader, which is the layer that may import the
simulation package. `solid_node/node/` never does, and putting a hook
there for the simulation layer to register into would only hide that
dependency rather than place it (ADR-056 stage 3a, D9).

A tree that declares no driver is not touched: not bound, not even
walked. That is a requirement and not an optimization -- the walk would
render the tree, and an extra render at load time is a behaviour change
for every project that has no drivers at all.
"""

import os

from solid_node.core.loader import load_node

from .base import BaseNodeTest

BASEDIR = os.path.dirname(os.path.abspath(__file__))


class LoaderDefaultBindingTest(BaseNodeTest):

    def load(self, reference):
        return load_node(os.path.join(BASEDIR, reference))

    def test_a_driver_declaring_tree_loads_with_its_defaults_bound(self):
        node = self.load('meta_project/machine.py:Machine')

        self.assertEqual(node.x_axis.state['motor'], 8000)
        self.assertEqual(node.y_axis.state['motor'], 8000)

    def test_the_loaded_tree_renders_without_an_unbound_error(self):
        node = self.load('meta_project/machine.py:Machine')

        node.render()

        self.assertEqual(
            [op.serialized for op in node.x_axis.carriage.operations],
            [['t', ['100.0', '0', '0']]])

    def test_a_root_declared_driver_binds_by_its_bare_name(self):
        node = self.load('meta_project/axis.py:Axis')

        self.assertEqual(node.state['x'], 800)

    def test_a_driverless_project_loads_untouched(self):
        node = self.load('meta_project/nested.py:Nested')

        self.assertEqual(dict(node.state), {})
        self.assertEqual(node.inner.cube.operations, [])
