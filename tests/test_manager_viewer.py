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
from solid_node.viewers.bundle import ViewerUnavailable

REPORT = {'path': '/tmp/solid-widget.js', 'index': '/tmp/index.html',
          'apiVersion': 5, 'version': '0.1.0'}


class ViewerCommandTest(TestCase):

    def test_reports_the_installed_viewer_as_json(self):
        output = io.StringIO()
        with patch('solid_node.manager.viewer.describe', return_value=REPORT), \
             redirect_stdout(output):
            Viewer().handle(Namespace())
        self.assertEqual(json.loads(output.getvalue()), REPORT)

    def test_missing_viewer_exits_with_remedy_and_no_stdout(self):
        output, errors = io.StringIO(), io.StringIO()
        with patch('solid_node.manager.viewer.describe',
                   side_effect=ViewerUnavailable('Install the viewer extra.')), \
             redirect_stdout(output), redirect_stderr(errors), \
             self.assertRaises(SystemExit) as raised:
            Viewer().handle(Namespace())
        self.assertEqual(raised.exception.code, 1)
        self.assertEqual(output.getvalue(), '')
        self.assertIn('Install the viewer extra.', errors.getvalue())
