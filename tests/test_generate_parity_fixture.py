# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""`tools/generate_parity_fixture.py`'s coverage check, task 4.1 (ADR-080).

`uncovered_builtins` used to read only the cases' own `expression` text.
With a `bindings` table, `sin(` can live in an entry and appear in no
case's own expression -- the sharing corpus (`tests/expression_project/
sharing.py`) is built exactly so `floor` reaches this scan only through a
binding, once for real. This is the tool's own coverage function under
direct test, so the guard is caught by the framework's suite -- not only
by running the generator by hand.
"""

import importlib.util
import os
from unittest import TestCase


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL_PATH = os.path.join(ROOT, 'tools', 'generate_parity_fixture.py')


def _load_tool():
    """Load the generator as a module without running its `main()` --
    `spec_from_file_location` rather than a package import, because
    `tools/` is a script directory, not a package (no `__init__.py`), by
    design: this tool is meant to be run, not imported by a project."""
    spec = importlib.util.spec_from_file_location(
        'generate_parity_fixture', TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CoverageAcrossBindingsAndCasesTest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tool = _load_tool()

    def test_a_name_in_a_case_expression_is_covered_as_before(self):
        cases = [{'expression': '(floor($t) + 1.0)'}]

        self.assertNotIn('floor', self.tool.uncovered_builtins(cases, []))

    def test_a_name_appearing_only_inside_a_binding_is_covered(self):
        """The exact hole design.md D10 names: a builtin call moved
        entirely into a `bindings` entry, with no case's own expression
        naming it."""
        cases = [{'expression': '_b0'}]
        bindings = [{'name': '_b0', 'expression': 'floor($t)'}]

        without_the_table = self.tool.uncovered_builtins(cases, [])
        with_the_table = self.tool.uncovered_builtins(cases, bindings)

        self.assertIn('floor', without_the_table)
        self.assertNotIn('floor', with_the_table)

    def test_a_name_in_neither_still_fails(self):
        cases = [{'expression': '_b0'}]
        bindings = [{'name': '_b0', 'expression': '($t + 1.0)'}]

        self.assertIn('floor', self.tool.uncovered_builtins(cases, bindings))

    def test_the_real_fixture_build_covers_every_emitted_builtin(self):
        """The full regeneration: every corpus together, coverage checked
        the way `build()` checks it before writing anything."""
        fixture = self.tool.build()

        self.assertEqual(
            self.tool.uncovered_builtins(fixture['cases'], fixture['bindings']),
            [])

    def test_the_sharing_corpus_puts_floor_only_inside_a_binding(self):
        """Not just a synthetic case above: the real sharing corpus's own
        `floor` call reaches the fixture exclusively through a binding
        entry, because `time_only`'s and `time_nested`'s cases hold only
        the bound name or a superset expression naming it -- proving the
        scan this task adds is load-bearing for a real corpus, not only
        for a hand-built example."""
        cases, table, bindings = self.tool.sharing_cases()

        self.assertTrue(bindings)
        case_text = ' '.join(case['expression'] for case in cases)
        binding_text = ' '.join(entry['expression'] for entry in bindings)
        self.assertNotIn('floor(', case_text)
        self.assertIn('floor(', binding_text)
