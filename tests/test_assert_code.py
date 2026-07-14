# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from .base import BaseNodeTest


class _StubSolid:
    """Stands in for a real node: assertCode only ever touches
    `self.solid.scad_code`."""

    def __init__(self, scad_code):
        self.scad_code = scad_code


class AssertCodeTest(BaseNodeTest):
    """Regression for B13: assertCode iterated only over the *generated*
    token list, so:
    - a generated scad that is a strict prefix of the expected code found
      no mismatched token and passed silently (missing trailing
      statements went unnoticed);
    - an expected shorter than generated indexed past the end of the
      expected token list and raised a raw IndexError instead of a clean
      AssertionError.
    """

    def test_truncated_generated_is_caught(self):
        expected = """
        union() {
            cylinder(h = 10, r = 5);
            cube(2);
        }
        """
        # Missing the trailing `cube(2); }` — a strict prefix of
        # `expected` once whitespace is normalized.
        self.solid = _StubSolid("union() {\n    cylinder(h = 10, r = 5);\n")

        with self.assertRaises(AssertionError):
            self.assertCode(expected)

    def test_generated_longer_than_expected_is_caught_cleanly(self):
        expected = """
        cylinder(h = 10, r = 5);
        """
        self.solid = _StubSolid("cylinder(h = 10, r = 5);\ncube(2);\n")

        with self.assertRaises(AssertionError):
            self.assertCode(expected)

    def test_matching_code_still_passes(self):
        expected = """
        cylinder(h = 10, r = 5);
        """
        self.solid = _StubSolid("cylinder(h = 10, r = 5);\n")

        self.assertCode(expected)  # must not raise
