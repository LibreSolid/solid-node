# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The framework's one lookup of the viewer it does not carry.

solid-node-viewer registers the `solid_node.viewer` entry point; the
framework resolves it and nothing else. These tests drive the lookup with
fake entry points so they hold whether or not the viewer is installed here.
"""

import ast
import inspect
import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from solid_node.viewers import bundle
from solid_node.viewers.bundle import ViewerUnavailable


def fake_entry(result=None, error=None):
    entry = Mock()
    entry.name = 'bundle'
    describe = Mock(side_effect=error) if error else Mock(return_value=result)
    entry.load.return_value = describe
    return entry


REPORT = {
    'path': '/site/solid_node_viewer/widget/dist/solid-widget.js',
    'index': '/site/solid_node_viewer/widget/index.html',
    'apiVersion': 5,
    'version': '0.1.0',
}


class LookupTest(TestCase):

    def test_the_lookup_imports_only_the_standard_library(self):
        tree = ast.parse(inspect.getsource(bundle))
        imports = {node.names[0].name for node in ast.walk(tree)
                   if isinstance(node, ast.Import)}
        froms = {node.module for node in ast.walk(tree)
                 if isinstance(node, ast.ImportFrom)}
        self.assertTrue(imports <= {'sys'}, imports)
        self.assertTrue(froms <= {'importlib.metadata', 'pathlib'}, froms)

    def test_without_the_entry_point_the_viewer_is_not_installed(self):
        with patch.object(bundle, 'entry_points', return_value=[]):
            self.assertFalse(bundle.has_bundle())
            with self.assertRaises(ViewerUnavailable) as raised:
                bundle.describe()
            remedy = bundle.missing_bundle_remedy()
        self.assertIn('pip install "solid-node[viewer]"', remedy)
        self.assertEqual(str(raised.exception), remedy)
        self.assertNotIn('npm', remedy)

    def test_the_entry_point_answers_paths_and_version(self):
        with patch.object(bundle, 'entry_points', return_value=[fake_entry(REPORT)]):
            self.assertTrue(bundle.has_bundle())
            self.assertEqual(bundle.describe(), REPORT)
            self.assertEqual(bundle.bundle_path(), Path(REPORT['path']))
            self.assertEqual(bundle.index_path(), Path(REPORT['index']))
            self.assertEqual(bundle.api_version(), 5)

    def test_an_installed_viewer_without_a_bundle_speaks_for_itself(self):
        entry = fake_entry(error=FileNotFoundError('Viewer bundle not found; run npm'))
        with patch.object(bundle, 'entry_points', return_value=[entry]):
            self.assertFalse(bundle.has_bundle())
            self.assertEqual(bundle.missing_bundle_remedy(),
                             'Viewer bundle not found; run npm')

    def test_the_lookup_asks_the_documented_group_for_the_documented_entry(self):
        other = fake_entry(REPORT)
        other.name = 'something-else'
        ours = fake_entry(REPORT)
        ours.name = 'bundle'
        with patch.object(bundle, 'entry_points', return_value=[other, ours]) as points:
            bundle.describe()
        points.assert_called_once_with(group='solid_node.viewer')
        other.load.assert_not_called()

    def test_the_viewer_runs_through_this_interpreter(self):
        self.assertEqual(bundle.viewer_command(),
                         [sys.executable, '-m', 'solid_node_viewer'])
