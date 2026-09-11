# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""whole-tree-fixpoint, task 5: what must NOT change.

These are the change's compatibility claims, written as tests before the
solver moved: every one of them is GREEN on the unmodified tree and MUST
stay green once the tree pass lands. They exercise the `kinematics`
capability -- the enumeration itself, and the driver snapshot's ordering
ahead of it -- rather than one relation's own solve, which is
`test_couplings.py`'s and `test_joints.py`'s business.
"""

from solid2 import cube

from solid_node.motion.couplings import declared_relations
from solid_node.motion.joints import Revolute
from solid_node.motion.ports import RotationalPort
from solid_node.node import AssemblyNode, Solid2Node
from solid_node.simulation import Driver

from .base import BaseNodeTest
from .coupling_project.parts import Pulley
from .coupling_project.train import Arm, Train


class KLeaf(Solid2Node):
    turn = Revolute(axis=(0, 0, 1), unit='deg')

    def render(self):
        return cube(1, center=True)


class CompatibilityTest(BaseNodeTest):

    def test_a_descendants_simulate_reads_what_an_ancestors_relation_bound(self):
        """task 5.1: the hexapod's shape, three levels -- the child reads
        eight (here, three) coordinates the root's relations bound."""
        reads = {}

        class Grandchild(AssemblyNode):
            leaf = KLeaf()

            def simulate(self):
                reads['gait'] = self.gait
                reads['stride'] = self.stride
                reads['reach'] = self.reach

            @property
            def gait(self):
                return self.parent_value('gait')

            @property
            def stride(self):
                return self.parent_value('stride')

            @property
            def reach(self):
                return self.parent_value('reach')

            def parent_value(self, name):
                return getattr(self._parent, name).value

        class Child(AssemblyNode):
            gait = RotationalPort(unit='deg')
            stride = RotationalPort(unit='deg')
            reach = RotationalPort(unit='deg')
            grandchild = Grandchild()

        class Root(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            child = Child()

            angle.drives(child.gait, ratio=1.0)
            angle.drives(child.stride, ratio=2.0)
            angle.drives(child.reach, ratio=3.0)

        root = Root()
        root.set_state(angle=10.0)

        self.assertEqual(reads, {'gait': 10.0, 'stride': 20.0, 'reach': 30.0})

    def test_nothing_that_solves_today_is_deferred(self):
        """task 5.2: instrument the solver over the whole
        `coupling_project` fixture set and assert the deferred list is
        EMPTY."""
        from solid_node.node import assembly as _assembly

        original = _assembly.solve_relations
        deferred_counts = []

        def instrumented(assembly, enum):
            before = len(enum.deferred)
            original(assembly, enum)
            deferred_counts.append(len(enum.deferred) - before)

        _assembly.solve_relations = instrumented
        try:
            train = Train()
            train.set_state(escape_angle=24.0)
            arm = Arm()
            arm.set_state(shoulder_driver=10.0, elbow_driver=30.0)
        finally:
            _assembly.solve_relations = original

        self.assertTrue(deferred_counts, 'the instrumentation never ran')
        self.assertEqual(sum(deferred_counts), 0)

    def test_the_pass_order_is_unchanged_for_a_tree_that_defers_nothing(self):
        """task 5.3: declaration order within a class, copy order within
        a broadcast, the train solves backwards with no reordering."""
        train = Train()
        train.set_state(escape_angle=24.0)

        for relation in declared_relations(Train):
            with self.subTest(relation=repr(relation)):
                self.assertEqual(relation.record_of(train).direction,
                                 'backward')

    def test_a_descendant_simulates_against_the_snapshot_just_bound(self):
        """task 5.4, from probe_state_order.py: after set_state(step=10)
        then set_state(step=90), the child reads 90 throughout the
        second enumeration, INCLUDING while its parent's phase runs."""
        seen_during_parent_phase = []

        class Axis(AssemblyNode):
            step = Driver(default=0.0, unit='deg', range=(0.0, 100.0))
            leaf = KLeaf()

            def simulate(self):
                self.leaf.turn = self.step

        class Machine(AssemblyNode):
            axis = Axis()

            def simulate(self):
                seen_during_parent_phase.append(dict(self.axis._states))

        machine = Machine()
        machine.set_state(step=10.0, time=0.0)
        machine.set_state(step=90.0, time=0.0)

        self.assertEqual(seen_during_parent_phase[-1].get('step'), 90.0)
        self.assertEqual(machine.axis.leaf.turn.value, 90.0)

    def test_set_states_refusals_and_rollback_are_unchanged(self):
        """task 5.5."""
        class Named(AssemblyNode):
            motor = Driver(default=0.0, unit='deg')

        top = Named()
        top.set_state(motor=5.0)

        with self.assertRaises(ValueError):
            top.set_state(motr=6.0)
        self.assertEqual(top.motor, 5.0)

    def test_symbolic_mode_is_unchanged(self):
        """task 5.6: a tree with nothing bound publishes the same
        expressions through a DEFERRED relation (the movement sources
        from a coordinate its own child's relation solves) as through an
        immediate one."""
        from solid_node.core.serializer import serialize_node, symbolic_document

        # The driver stays at the ROOT `Deferred` declares it on --
        # `drive_tree` (qualified.py) delivers a node's OWN drivers into
        # its OWN `_states` immediately before that node's render(), and
        # a driver nested under a nested assembly is a DIFFERENT,
        # pre-existing seam (the loader's default binding walks the same
        # way) this compatibility check is not about; see evidence.md.
        class Down(AssemblyNode):
            steps = RotationalPort(unit='deg')
            column = KLeaf()

            steps.drives(column.turn, ratio=1.0)

        class Deferred(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            down = Down()
            sink = KLeaf()

            down.column.turn.drives(sink.turn, ratio=2.0)

            def simulate(self):
                self.down.steps = self.angle

        deferred = Deferred()
        with symbolic_document(deferred) as (_declarations, _instructions):
            document = serialize_node(deferred, lambda rigid: rigid.name)

        def find_sink(node):
            if node['name'] == 'sink':
                return node
            for child in node.get('children', ()):
                found = find_sink(child)
                if found is not None:
                    return found
            return None

        sink_node = find_sink(document)
        self.assertIsNotNone(sink_node)
        rotations = [operation[1] for operation in sink_node['operations']
                     if operation[0] == 'r']
        self.assertTrue(rotations)
        self.assertIn('angle', str(rotations[0]))
