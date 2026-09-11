"""Construction-time sharing, exercised through the public motion algebra."""

import gc
import json
import weakref
import pathlib
import subprocess
import tempfile
import tracemalloc
from unittest import TestCase
from unittest.mock import patch

from solid2.core.object_base import OpenSCADConstant, scad_inline

from solid_node import math as m
from solid_node.core.expressions import bind_expressions
from solid_node.node.operations import Rotation, Translation, unserialize
from solid_node.node.qualified import DriverToken
from solid_node.scad_expression import GraphValue, restore_scalar
from solid_node.expression_graph import postorder
from solid_node.node import AssemblyNode
from solid_node.simulation import Driver
from tests.test_expression_bindings import Leaf
from tests.flexible_project.spring import Spring
from tests.base import BaseNodeTest


class CarryProfileMachine(AssemblyNode):
    drive = Driver(default=0, range=(0, 1))

    def __init__(self):
        super().__init__()
        self.leaf, self.spring = Leaf(), Spring()

    def render(self):
        return [self.leaf, self.spring]

    def simulate(self):
        carry = self.drive + self.time
        for _ in range(14):
            carry = m.sin(carry + carry)
        profile = m.piecewise(carry, [(i/35, (i%3)/2) for i in range(36)])
        self.connect(40 + profile, self.spring.height)
        self.leaf.translate([profile, profile + 1, 0])


class GraphProducerTest(BaseNodeTest):
    def test_real_export_and_build_share_flexible_and_rigid_roots(self):
        from solid_node.core.export import export_node
        from solid_node.core.builder import Builder
        node = CarryProfileMachine()
        node.set_state(drive=.25)
        with tempfile.TemporaryDirectory() as output:
            document = export_node(node, output, widget=False)
            self.assertEqual(document['version'], 4)
            self.assertLess(len(json.dumps(document)), 50000)
            self.assertNotIn('let(', json.dumps(document))
            self.assertEqual(node.drive, .25)
            builder = Builder('unused.py', build_dir=self.build_dir, watch=False)
            builder.node = node
            self.assertTrue(builder._write_viewer_snapshot())
            built = json.loads((pathlib.Path(self.build_dir)/'viewer.json').read_text())
            self.assertEqual(built['bindings'], document['bindings'])
            self.assertEqual(node.drive, .25)

    def test_dependency_and_diagnostics_do_not_render_the_graph(self):
        from solid_node.scad_expression import depends_on_time, get_animation_time
        x = DriverToken('drive')
        for _ in range(1000):
            x = x + x
        with patch.object(GraphValue, '__str__', side_effect=AssertionError('eager text')):
            self.assertFalse(depends_on_time(x))
            self.assertTrue(depends_on_time(x + get_animation_time()))
            spring = Spring()
            spring.height = x
            self.assertLess(len(repr(spring.height)), 200)
            with self.assertRaises(TypeError) as caught:
                spring.bound_values()
        self.assertLess(len(str(caught.exception)), 1000)


class ExpressionGraphTest(TestCase):
    def test_every_supported_operator_keeps_both_legacy_operand_orders(self):
        import operator
        ops = [operator.add, operator.sub, operator.mul, operator.truediv,
               operator.mod, operator.pow, operator.eq, operator.ne,
               operator.lt, operator.le, operator.gt, operator.ge]
        x, legacy = DriverToken('drive'), scad_inline('2')
        for op in ops:
            for left, right, a, b in [(x, legacy, 3, 2), (legacy, x, 2, 3)]:
                with self.subTest(operator=op.__name__, left=a):
                    value = op(left, right)
                    self.assertIsInstance(value, GraphValue)
                    self.assertEqual(value.evaluate({'drive': 3}), op(a, b))
        self.assertEqual((-x).evaluate({'drive': 3}), -3)
        self.assertEqual(abs(x).evaluate({'drive': -3}), 3)

    def test_native_collection_never_stringifies_and_reclaims_the_graph(self):
        from solid_node.core.serializer import bind_document
        retained = []
        for _ in range(3):
            x = DriverToken('drive')
            for _ in range(10000):
                x = x + x
            retained.append(weakref.ref(x._expression_node))
            with patch.object(GraphValue, '__str__', side_effect=AssertionError('eager text')):
                root = {'operations': [Rotation(x, [0, 0, 1])._graph_serialized()],
                        'children': [], 'flexible': {'params': {'height': x._expression_node}}}
                bindings = bind_document(root, ['drive'])
            self.assertEqual(len(bindings), 10000)
            self.assertLess(len(json.dumps([root, bindings])), 900000)
            del x, root, bindings
        gc.collect()
        self.assertTrue(all(ref() is None for ref in retained))

    def test_construction_memory_is_linear_in_unique_operations(self):
        peaks = []
        for size in (1000, 4000):
            gc.collect()
            tracemalloc.start()
            x = DriverToken('drive')
            for _ in range(size):
                x = x + x
            peaks.append(tracemalloc.get_traced_memory()[1])
            tracemalloc.stop()
            self.assertEqual(len(list(postorder([x._expression_node]))), size + 1)
            del x
        self.assertLess(peaks[1], peaks[0] * 5)

    def test_closure_scopes_and_collision_do_not_capture_inputs(self):
        cases = [('let(a=2, b=a+3) b*a', 10),
                 ('let(a=2) (let(a=3, b=a+1) b)+a', 6),
                 ('let(a=2, b=let(a=3) a) (a+b)', 5)]
        for text, expected in cases:
            self.assertEqual(float(restore_scalar(text)), expected)
        x = m.sin(DriverToken('_s0'))
        closed = str(x + x)
        self.assertIn('__s0', closed)
        self.assertAlmostEqual(restore_scalar(closed).evaluate({'_s0': 30}), 1)

    def test_generated_scad_closures_match_boundary_values_in_openscad(self):
        x = DriverToken('drive')
        shaped = m.piecewise(x, [(-1, 2), (0, 0), (1, 3)])
        value = shaped + shaped + m.sin(x) + m.cos(x)
        rows = []
        expected = []
        for instant in (-1, -1e-8, 0, 1e-8, .5, 1):
            rows.append(f'echo(let(drive={instant}) {value});')
            expected.append(2*m.piecewise(instant, [(-1, 2), (0, 0), (1, 3)])
                            + m.sin(instant) + m.cos(instant))
        # Exercise an actual solid2 wrapper returning to the native graph.
        from solid2.core.builtins.openscad_functions import sin as legacy_sin
        wrapped = legacy_sin(value)
        rewritten, bindings, warnings = bind_expressions([str(wrapped)], ['drive'])
        self.assertFalse(warnings)
        self.assertNotIn('let(', json.dumps([rewritten, bindings]))
        with tempfile.TemporaryDirectory() as directory:
            source = pathlib.Path(directory) / 'closures.scad'
            result = pathlib.Path(directory) / 'closures.echo'
            source.write_text('\n'.join(rows))
            subprocess.run(['/usr/bin/openscad', '-o', str(result), str(source)],
                           check=True, capture_output=True, timeout=30)
            output = result.read_text().splitlines()
        self.assertEqual(len(output), len(expected), output)
        for line, number in zip(output, expected):
            self.assertTrue(line.startswith('ECHO: '), line)
            # OpenSCAD echo prints six significant figures by default.
            self.assertAlmostEqual(float(line[6:]), number, delta=1e-5)

    def test_restored_numeric_placement_and_unresolved_refusal(self):
        op = unserialize(['t', ['let(a=sin(30)) (a + a)', '0', '0']])
        self.assertAlmostEqual(op.matrix()[0, 3], 1)
        from tests.test_expression_bindings import Leaf
        node = Leaf()
        self.assertAlmostEqual(node.as_number(restore_scalar('sin(30)')), .5)
        with self.assertRaisesRegex(ValueError, 'drive'):
            float(DriverToken('drive'))

    def test_explicit_evaluation_uses_symbolic_remainder(self):
        value = restore_scalar('let(a=drive % 3) (a + a)')
        self.assertEqual(value.evaluate({'drive': -4}), -2)

    def test_repeated_reuse_has_compact_standalone_output(self):
        x = DriverToken('drive')
        for _ in range(14):
            x = x + x
        text = str(x)
        self.assertLess(len(text), 2000)
        rewritten, bindings, warnings = bind_expressions([text], ['drive'])
        self.assertFalse(warnings)
        self.assertLess(len(json.dumps([rewritten, bindings])), 4000)

    def test_deep_shared_chain_publishes_without_recursion_fallback(self):
        x = DriverToken('drive')
        for i in range(10000):
            x = x + i
        rewritten, bindings, warnings = bind_expressions(
            [str(x), str(x)], ['drive'])
        self.assertFalse(warnings)
        self.assertTrue(bindings)
        self.assertEqual(rewritten[0], rewritten[1])

    def test_profile_reuses_carry_and_feeds_several_coordinates(self):
        carry = DriverToken('drive')
        for _ in range(6):
            carry = m.sin(carry + carry)
        points = [(i / 35, (i % 3) / 2) for i in range(36)]
        spread = m.piecewise(carry, points)
        text = str(spread)
        self.assertLess(len(text), 20000)
        outputs = [text, str(spread + 1), str(spread * 2)]
        rewritten, bindings, warnings = bind_expressions(outputs, ['drive'])
        self.assertFalse(warnings)
        self.assertTrue(bindings)
        self.assertNotIn('let(', json.dumps([rewritten, bindings]))

    def test_legacy_operand_order_and_public_math(self):
        x = DriverToken('drive')
        legacy = scad_inline('(other + 2)')
        pairs = [(x - legacy, '(drive - (other + 2))'),
                 (legacy - x, '((other + 2) - drive)'),
                 (legacy / x, '((other + 2) / drive)'),
                 (abs(x), 'abs(drive)'),
                 (m.sin(x), 'sin(drive)')]
        for actual, expected in pairs:
            self.assertIsInstance(actual, OpenSCADConstant)
            self.assertEqual(str(actual), expected)
        with self.assertRaises(Exception):
            bool(x < legacy)

    def test_standalone_operation_round_trip_preserves_input(self):
        x = m.sin(DriverToken('drive'))
        for operation in [Rotation(x + x, [0, 0, 1]),
                          Translation([x + x, 0, 1])]:
            original = operation.serialized
            copied = json.loads(json.dumps(original))
            restored = unserialize(copied)
            self.assertEqual(copied, original)
            self.assertEqual(restored.serialized, original)

    def test_discarded_values_are_collectible(self):
        x = m.sin(DriverToken('drive'))
        reference = weakref.ref(x)
        y = x + x
        del x
        del y
        gc.collect()
        self.assertIsNone(reference())
