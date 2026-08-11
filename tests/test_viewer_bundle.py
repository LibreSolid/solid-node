# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import json
import os
import ast
import inspect
import tempfile
from unittest import TestCase
from unittest.mock import patch


class ViewerBundleTest(TestCase):

    def test_reports_declared_api_version_without_cad_runtime(self):
        from solid_node.viewers import bundle

        tree = ast.parse(inspect.getsource(bundle))
        imports = [node.names[0].name for node in ast.walk(tree)
                   if isinstance(node, ast.Import)]
        self.assertEqual(imports, ['json'])
        self.assertEqual(bundle.api_version(), 3)

    def test_bundle_paths_and_remedy_share_one_source(self):
        from solid_node.viewers import bundle

        self.assertTrue(str(bundle.bundle_path()).endswith('dist/solid-widget.js'))
        self.assertTrue(str(bundle.index_path()).endswith('index.html'))
        self.assertIn('npm', bundle.missing_bundle_remedy())

    def test_api_version_is_read_from_package_declaration(self):
        from solid_node.viewers import bundle

        with tempfile.TemporaryDirectory() as root:
            package = os.path.join(root, 'package.json')
            with open(package, 'w') as stream:
                json.dump({'solidNodeViewerApi': 7}, stream)
            with patch.object(bundle, 'PACKAGE_JSON', package):
                self.assertEqual(bundle.api_version(), 7)
