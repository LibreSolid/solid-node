# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Framework-level regression for issue #19: a FRESH node.assemble()
(no set_keyframe -- exactly the viewer/build path `solid develop`
takes) on a genuinely non-linear kinematic must complete, not raise,
and must serialize the operation as the expected asin(...)-containing
$t expression.

Uses tests/meta_project/conrod.py (a real fixture, exercised
end-to-end via `solid test` by tests/test_meta.py's
NonLinearSymbolicMathMetaTest) directly, instantiated and assembled
in-process the way tests/test_two_pipes.py exercises flat_project
fixtures -- this is the layer BELOW the meta harness: it inspects the
serialized operation directly rather than parsing `solid test`
subprocess output."""

from .base import BaseNodeTest
from .meta_project.conrod import Conrod


class ConrodSymbolicAssemblyTest(BaseNodeTest):

    def test_fresh_assemble_does_not_raise_on_symbolic_time(self):
        # Pre-fix: math.asin(...) of a $t-derived value raised
        # `TypeError: must be real number, not OpenSCADConstant`
        # here, during Conrod.render() -> node.assemble().
        node = Conrod()

        node.assemble()

    def test_serializes_the_expected_asin_dollar_t_expression(self):
        node = Conrod()

        node.assemble()

        rotations = [
            op for op in node.rod.operations
            if op.serialized[0] == 'r'
        ]
        self.assertEqual(len(rotations), 1)

        angle_expr = rotations[0].serialized[1]
        self.assertIn('asin(', angle_expr)
        self.assertIn('$t', angle_expr)
        self.assertEqual(angle_expr, 'asin((0.25 * sin((360.0 * $t))))')
