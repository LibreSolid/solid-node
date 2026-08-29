# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The flexible leaf: a non-rigid leaf whose shape follows its ports.

Everything here is technology-independent -- what a flexible leaf IS,
regardless of which backend evaluates the sweep. The backend is a stub
whose "shape" is a set of parameter names and a cube scaled by them, so
a failure in this file is a failure of the leaf kind and never of a CAD
library.

The two halves are the two halves of the design. Rigidity: a flexible
part deforms, so it is not rigid, cannot be fused, caches no rigid
artifact and is not a printed piece -- while remaining a leaf, with no
children and no access to animation time. Parameters: the declared ports
ARE the parameter surface, connected by the parent assembly exactly as
any port is, checked against the rendered shape in both directions, and
never defaulted when a binding is missing.
"""

import os
from unittest.mock import patch

import trimesh
from solid2 import cube

from solid_node.node import (AssemblyNode, FusionNode, Solid2Node,
                             TranslationalPort)
from solid_node.node.base import _topmost_rigid_nodes
from solid_node.node.flexible import FlexibleNode
from solid_node.node.leaf import LeafNode
from solid_node.node.qualified import DriverToken
from solid_node.simulation import Driver

from .base import BaseNodeTest


class Spec:
    """A stand-in flexible shape: the parameter names it references."""

    def __init__(self, *params):
        self.params = frozenset(params)


class StubFlexibleNode(FlexibleNode):
    """A flexible adapter over `Spec`, standing in for a real backend.

    Its evaluation is a cube whose side is the sum of the bound values,
    which is enough to tell one binding's geometry from another's.
    """

    def _shape_parameters(self, rendered):
        return rendered.params

    def _snapshot_mesh(self, rendered, values):
        side = sum(values.values())
        return trimesh.creation.box((side, side, side))

    def _snapshot_stl(self, rendered, values):
        return self._snapshot_mesh(rendered, values).export(file_type='stl')


class Spring(StubFlexibleNode):

    height = TranslationalPort(unit='mm')

    def render(self):
        return Spec('height')


class TaperedSpring(StubFlexibleNode):
    """The same part with a structural knob: a coil count changes what
    render() returns, so it is a constructor parameter and an identity."""

    height = TranslationalPort(unit='mm')

    def __init__(self, coils, **kwargs):
        super().__init__(coils=coils, **kwargs)

    def render(self):
        return Spec('height')


class UnportedSpring(StubFlexibleNode):
    """A shape parameter no port carries."""

    def render(self):
        return Spec('height')


class OverportedSpring(StubFlexibleNode):
    """A port the shape names no parameter for."""

    height = TranslationalPort(unit='mm')
    twist = TranslationalPort(unit='mm')

    def render(self):
        return Spec('height')


class Post(Solid2Node):

    def render(self):
        return cube(4, center=True)


class Rig(AssemblyNode):
    """The parent that wires the spring: a driver, an expression over it,
    and an ordinary connect() into the leaf's port."""

    lift = Driver(default=0.0, range=(0.0, 12.0), unit='mm')

    def __init__(self):
        self.spring = Spring()
        super().__init__()

    def render(self):
        self.connect(40.0 - self.lift, self.spring.height)
        return [self.spring]


class FusedSpring(FusionNode):

    def __init__(self):
        self.spring = Spring()
        self.post = Post()
        super().__init__()

    def render(self):
        return [self.post, self.spring]


def bound_rig(lift=2.0):
    rig = Rig()
    rig.set_state(lift=lift)
    return rig


class FlexibleRigidityTest(BaseNodeTest):
    """A third case in the rigidity story: the non-rigid leaf."""

    def test_a_flexible_leaf_is_not_rigid(self):
        self.assertFalse(Spring().rigid)

    def test_a_flexible_leaf_is_still_a_leaf(self):
        spring = Spring()

        self.assertIsInstance(spring, LeafNode)
        self.assertEqual(spring.children, tuple())

    def test_a_fusion_rejects_a_flexible_child_naming_both(self):
        fusion = FusedSpring()

        with self.assertRaises(Exception) as raised:
            fusion.assemble()

        # Validation runs before the parent links its children, so the
        # flexible leaf is still named for its class here.
        message = str(raised.exception)
        self.assertIn(fusion.name, message)
        self.assertIn('Spring', message)

    def test_a_rejected_fusion_produces_no_geometry(self):
        fusion = FusedSpring()

        with self.assertRaises(Exception):
            fusion.assemble()

        self.assertFalse(os.path.exists(fusion.stl_file))

    def test_time_still_raises_on_a_flexible_leaf(self):
        with self.assertRaises(Exception) as raised:
            Spring().time

        self.assertIn('time', str(raised.exception))

    def test_reading_stl_raises_as_on_any_non_rigid_node(self):
        spring = Spring()

        with self.assertRaises(Exception) as raised:
            spring.stl

        self.assertIn('not rigid', str(raised.exception))

    def test_it_never_takes_the_cached_rigid_shortcut(self):
        rig = bound_rig()
        rig.assemble()

        self.assertFalse(rig.spring._render_can_be_skipped())

    def test_it_generates_no_cached_rigid_artifact(self):
        rig = bound_rig()
        rig.assemble()

        with patch('solid_node.node.base.require_openscad',
                   side_effect=AssertionError(
                       'a flexible part must not check OpenSCAD')), \
             patch('solid_node.node.base.Popen', side_effect=AssertionError(
                 'a flexible part must not launch OpenSCAD')):
            rig.spring.generate_stl()

        self.assertFalse(os.path.exists(rig.spring.stl_file))

    def test_it_is_never_a_topmost_rigid_node(self):
        rig = bound_rig()
        rig.assemble()

        self.assertEqual(list(_topmost_rigid_nodes(rig)), [])


class FlexibleParameterSurfaceTest(BaseNodeTest):
    """The declared ports are the parameter surface, and nothing else."""

    def test_the_parent_assembly_connects_a_flexible_leafs_port(self):
        rig = bound_rig(lift=2.0)

        self.assertEqual(rig.spring.height.value, 38.0)

    def test_rebinding_the_driver_rebinds_the_port(self):
        rig = bound_rig(lift=2.0)

        rig.set_state(lift=5.0)

        self.assertEqual(rig.spring.height.value, 35.0)

    def test_the_bound_values_are_the_declared_ports(self):
        rig = bound_rig(lift=2.0)

        self.assertEqual(rig.spring.bound_values(), {'height': 38.0})

    def test_an_unbound_port_fails_naming_the_node_and_the_port(self):
        spring = Spring()

        with self.assertRaises(Exception) as raised:
            spring.bound_values()

        message = str(raised.exception)
        self.assertIn('Spring', message)
        self.assertIn('height', message)

    def test_an_unbound_port_is_never_defaulted(self):
        spring = Spring()

        with self.assertRaises(Exception):
            spring.assemble()

    def test_a_symbolic_binding_fails_rather_than_guessing(self):
        spring = Spring()
        spring.height.value = DriverToken('rig.lift')

        with self.assertRaises(Exception) as raised:
            spring.bound_values()

        message = str(raised.exception)
        self.assertIn('Spring', message)
        self.assertIn('height', message)
        self.assertIn('rig.lift', message)

    def test_a_shape_parameter_without_a_port_is_rejected(self):
        node = UnportedSpring()

        with self.assertRaises(Exception) as raised:
            node.validate(node.render())

        message = str(raised.exception)
        self.assertIn('UnportedSpring', message)
        self.assertIn('height', message)
        self.assertIn('none', message)

    def test_a_port_without_a_shape_parameter_is_rejected(self):
        node = OverportedSpring()

        with self.assertRaises(Exception) as raised:
            node.validate(node.render())

        message = str(raised.exception)
        self.assertIn('OverportedSpring', message)
        self.assertIn('twist', message)
        self.assertIn('height', message)

    def test_the_mismatch_error_carries_both_name_sets(self):
        node = OverportedSpring()

        with self.assertRaises(Exception) as raised:
            node.validate(node.render())

        message = str(raised.exception)
        self.assertIn('height, twist', message)


class FlexibleIdentityTest(BaseNodeTest):
    """Identity stays structural: a binding is not an artifact key."""

    def test_two_instances_of_a_no_arg_flexible_leaf_share_one_id(self):
        one = Spring()
        other = Spring()
        one.height.value = 10.0
        other.height.value = 20.0

        self.assertEqual(one.uniq_id, other.uniq_id)
        self.assertEqual(one.stl_file, other.stl_file)

    def test_a_structural_constructor_argument_still_differentiates(self):
        self.assertNotEqual(TaperedSpring(coils=6).uniq_id,
                            TaperedSpring(coils=7).uniq_id)

    def test_the_same_structural_argument_is_the_same_identity(self):
        self.assertEqual(TaperedSpring(coils=6).uniq_id,
                         TaperedSpring(coils=6).uniq_id)


class FlexibleMeshTest(BaseNodeTest):
    """The mesh is this instant's evaluation, never a cached artifact."""

    def test_the_mesh_is_evaluated_at_the_current_binding(self):
        rig = bound_rig(lift=2.0)
        rig.assemble()

        self.assertAlmostEqual(rig.spring.mesh.volume, 38.0 ** 3, places=3)

    def test_a_new_binding_gives_a_new_mesh(self):
        rig = bound_rig(lift=2.0)
        rig.assemble()
        first = rig.spring.mesh.volume

        rig.set_state(lift=5.0)

        self.assertNotAlmostEqual(rig.spring.mesh.volume, first, places=3)
        self.assertAlmostEqual(rig.spring.mesh.volume, 35.0 ** 3, places=3)
