# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The ADR-023 idempotent-render sweep keys on the ANIMATOR tag.

The tag is what makes a re-render absolute: an assembly drops only the
operations it applied and leaves static placement alone. It was named
`_driver`/`_driven_nodes`; ADR-056 gives "driver" a different, load
bearing meaning (a simulation input), so the animation tag is named
`_animator`/`_animated_nodes` and nothing in the sweep answers to the
old name any more. These assertions pin the attribute the sweep reads,
which behavioral keyframe tests cannot distinguish from a rename.
"""

from .base import BaseNodeTest
from .meta_project.nested import Nested


class AnimatorTagTest(BaseNodeTest):

    def rendered_nested(self):
        """A rendered Nested: the inner assembly translates the cube, so
        the cube carries exactly one animator-tagged operation."""
        node = Nested()
        node.render()
        node.inner.render()
        return node

    def test_render_tags_operations_with_the_animating_assembly(self):
        node = self.rendered_nested()
        operation = node.inner.cube.operations[-1]

        self.assertIs(operation._animator, node.inner)
        self.assertIn(node.inner.cube, node.inner._animated_nodes)

    def test_the_old_driver_names_are_gone(self):
        node = self.rendered_nested()
        operation = node.inner.cube.operations[-1]

        self.assertFalse(hasattr(operation, '_driver'))
        self.assertFalse(hasattr(node.inner, '_driven_nodes'))

    def test_the_sweep_drops_only_animator_tagged_operations(self):
        node = Nested()
        # Applied outside any render: untagged, and never swept.
        node.inner.cube.translate([0, 7, 0])
        node.render()
        node.inner.render()
        node.inner.render()

        serialized = [op.serialized for op in node.inner.cube.operations]
        self.assertEqual(serialized, [['t', ['0', '7', '0']],
                                      ['t', ['(10 * $t)', '0', '0']]])
