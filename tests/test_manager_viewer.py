# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import io
import json
from argparse import Namespace
from contextlib import redirect_stderr, redirect_stdout
from unittest import TestCase
from unittest.mock import patch

from solid_node.manager.viewer import Viewer


class ViewerCommandTest(TestCase):

    def test_reports_existing_bundle_as_json(self):
        output = io.StringIO()
        with patch('solid_node.manager.viewer.bundle_path',
                   return_value='/tmp/solid-widget.js'), \
             patch('solid_node.manager.viewer.api_version', return_value=1), \
             patch('solid_node.manager.viewer.has_bundle', return_value=True), \
             redirect_stdout(output):
            Viewer().handle(Namespace())

        self.assertEqual(json.loads(output.getvalue()), {
            'path': '/tmp/solid-widget.js', 'apiVersion': 1,
        })

    def test_missing_bundle_exits_with_remedy_and_no_stdout(self):
        output = io.StringIO()
        errors = io.StringIO()
        with patch('solid_node.manager.viewer.has_bundle', return_value=False), \
             patch('solid_node.manager.viewer.missing_bundle_remedy',
                   return_value='Build it with npm.'), \
             redirect_stdout(output), redirect_stderr(errors), \
             self.assertRaises(SystemExit) as raised:
            Viewer().handle(Namespace())

        self.assertEqual(raised.exception.code, 1)
        self.assertEqual(output.getvalue(), '')
        self.assertIn('Build it with npm.', errors.getvalue())
