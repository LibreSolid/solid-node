# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import io
import os
import tempfile
from argparse import Namespace
from contextlib import redirect_stderr, redirect_stdout
from unittest import TestCase

from solid_node.manager.new import New


EXPECTED_INIT = '''from solid_node.node import Solid2Node
from solid2 import cube, cylinder, translate

class DemoProject(Solid2Node):

    def render(self):
        return translate(-25, -25, 0)(
            cube(50, 50, 50)
        ) - cylinder(r=10, h=100)
'''


class NewCommandTest(TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def test_creates_expected_project_structure(self):
        target = os.path.join(self.tmpdir.name, 'myproj')
        args = Namespace(name=target)

        with redirect_stdout(io.StringIO()):
            New().handle(args)

        init_path = os.path.join(target, 'root', '__init__.py')
        gitignore_path = os.path.join(target, '.gitignore')

        self.assertTrue(os.path.isfile(init_path))
        self.assertTrue(os.path.isfile(gitignore_path))

        with open(init_path) as f:
            init_content = f.read()
        with open(gitignore_path) as f:
            gitignore_content = f.read()

        self.assertEqual(init_content, EXPECTED_INIT)
        self.assertIn('_build/', gitignore_content)
        self.assertIn('snapshot.png', gitignore_content)

    def test_generated_init_is_valid_python_matching_template(self):
        target = os.path.join(self.tmpdir.name, 'myproj2')
        args = Namespace(name=target)

        with redirect_stdout(io.StringIO()):
            New().handle(args)

        init_path = os.path.join(target, 'root', '__init__.py')
        with open(init_path) as f:
            source = f.read()

        compile(source, init_path, 'exec')
        self.assertEqual(source, EXPECTED_INIT)

    def test_refuses_to_overwrite_existing_directory(self):
        target = os.path.join(self.tmpdir.name, 'existing')
        os.makedirs(target)
        marker = os.path.join(target, 'keepme.txt')
        with open(marker, 'w') as f:
            f.write('do not touch')

        args = Namespace(name=target)

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as ctx:
                New().handle(args)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn(target, stderr.getvalue())

        # Nothing should have been clobbered.
        self.assertTrue(os.path.isfile(marker))
        self.assertFalse(os.path.isdir(os.path.join(target, 'root')))
