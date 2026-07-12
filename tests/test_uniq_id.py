# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from unittest import TestCase
from solid2 import cube
from solid_node.node import Solid2Node
from solid_node.node.base import _build_uniq_id
from .base import BaseNodeTest


class BuildUniqIdTest(TestCase):
    """Direct unit tests for _build_uniq_id(args, kwargs)."""

    def test_positional_args_unchanged(self):
        # Existing fixture filenames (e.g. simple_cylinder-10,5.stl) rely on
        # this exact positional format staying the same.
        self.assertEqual(_build_uniq_id((10, 5), {}), '10,5')

    def test_kwargs_rendered_as_key_value_sorted_by_key(self):
        self.assertEqual(
            _build_uniq_id((), {'height': 5, 'radius': 10}),
            'height=5,radius=10',
        )

    def test_kwargs_order_does_not_affect_result(self):
        a = _build_uniq_id((), {'a': 1, 'b': 2})
        b = _build_uniq_id((), {'b': 2, 'a': 1})
        self.assertEqual(a, b)

    def test_positional_and_keyword_calls_do_not_collide(self):
        # Regression for B9: Node(5, 10) and Node(height=5, radius=10) both
        # used to render as "5,10", silently sharing one .stl path even
        # though they represent different geometry.
        positional = _build_uniq_id((5, 10), {})
        keyword = _build_uniq_id((), {'height': 5, 'radius': 10})
        self.assertNotEqual(positional, keyword)


class _ArgsNode(Solid2Node):
    """A minimal node that forwards args/kwargs straight through to the
    base node, unlike flat_project.SimpleCylinder (which always forwards
    positionally to super().__init__ regardless of how it itself was
    called). This is what makes a positional vs. keyword call collide
    under the old _build_uniq_id."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def render(self):
        return cube(1)


class UniqIdCollisionTest(BaseNodeTest):

    def test_positional_and_keyword_calls_get_different_ids(self):
        positional = _ArgsNode(5, 10)
        keyword = _ArgsNode(height=5, radius=10)

        self.assertNotEqual(positional.uniq_id, keyword.uniq_id)
        self.assertNotEqual(positional.stl_file, keyword.stl_file)

    def test_keyword_call_order_does_not_affect_uniq_id(self):
        a = _ArgsNode(a=1, b=2)
        b = _ArgsNode(b=2, a=1)

        self.assertEqual(a.uniq_id, b.uniq_id)
