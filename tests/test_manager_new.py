# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import io
import os
import sys
import tempfile
from argparse import Namespace
from contextlib import redirect_stderr, redirect_stdout
from unittest import TestCase
from unittest.mock import patch

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

        init_path = os.path.join(target, 'myproj', 'myproj.py')
        manifest_path = os.path.join(target, 'pyproject.toml')
        gitignore_path = os.path.join(target, '.gitignore')

        self.assertTrue(os.path.isfile(init_path))
        self.assertTrue(os.path.isfile(manifest_path))
        self.assertTrue(os.path.isfile(gitignore_path))

        with open(init_path) as f:
            init_content = f.read()
        with open(gitignore_path) as f:
            gitignore_content = f.read()

        self.assertEqual(init_content, EXPECTED_INIT.replace('DemoProject', 'Myproj'))
        with open(manifest_path) as f:
            self.assertIn('model = "myproj.myproj:Myproj"', f.read())
        # `_build/` would not match the build path, which is a symlink to
        # a versioned directory; `_build*` covers both.
        self.assertIn('_build*', gitignore_content.split())
        self.assertIn('__pycache__/', gitignore_content.split())

    def test_generated_init_is_valid_python_matching_template(self):
        target = os.path.join(self.tmpdir.name, 'myproj2')
        args = Namespace(name=target)

        with redirect_stdout(io.StringIO()):
            New().handle(args)

        init_path = os.path.join(target, 'myproj2', 'myproj2.py')
        with open(init_path) as f:
            source = f.read()

        compile(source, init_path, 'exec')
        self.assertEqual(source, EXPECTED_INIT.replace('DemoProject', 'Myproj2'))

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
        self.assertFalse(os.path.isdir(os.path.join(target, 'existing')))


class ScaffoldAcceptanceTest(TestCase):
    """Structure and manifest content are covered above; this checks the
    thing that actually matters (task 6.1): the scaffolded project builds
    and tests with no further edits.

    `snowman-3` is deliberately not an identifier, and catches a real bug
    fixed alongside this test: `New.handle` normalized the inner package
    name (`snowman_3`) but left the OUTER directory as the raw argument
    (`snowman-3`), so the manifest's own `snowman_3.snowman_3:Snowman3`
    reference named a project one directory away from the one that was
    actually created, and `solid build`/`solid test` run from inside it
    could not discover their own manifest.
    """

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.addCleanup(os.chdir, os.getcwd())
        self.previous_sys_path = list(sys.path)
        self.addCleanup(sys.path.__setitem__, slice(None), self.previous_sys_path)
        # Other tests in this process set SOLID_BUILD_DIR at import time
        # (some to an absolute path); this scaffold's build must publish
        # into ITS OWN project, not wherever a prior module pointed.
        environment = patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop('SOLID_BUILD_DIR', None)

    def test_scaffolded_project_builds_and_tests_without_edits(self):
        os.chdir(self.tmpdir.name)
        with redirect_stdout(io.StringIO()):
            New().handle(Namespace(name='snowman-3'))

        project_dir = os.path.join(self.tmpdir.name, 'snowman_3')
        node_path = os.path.join(project_dir, 'snowman_3', 'snowman_3.py')
        manifest_path = os.path.join(project_dir, 'pyproject.toml')

        self.assertTrue(os.path.isfile(node_path),
                        f'expected {node_path} to exist')
        with open(manifest_path) as stream:
            self.assertIn('model = "snowman_3.snowman_3:Snowman3"',
                          stream.read())

        os.chdir(project_dir)
        sys.path.insert(0, project_dir)

        # Imported here, after the manifest exists and cwd/sys.path point
        # at the scaffold, exactly as a maker's first `solid build` /
        # `solid test` would run. Neither call is expected to raise or
        # exit nonzero; a SystemExit escaping either is this test's real
        # failure mode (build.py's own logging writes to the real stderr
        # fd through a handler bound before this test runs, so it is not
        # captured here and is not a meaningful thing to assert on).
        from solid_node.manager.build import Build
        from solid_node.manager.test import Test

        with redirect_stdout(io.StringIO()):
            Build().handle(Namespace(path=None))
            Test().handle(Namespace(path=None, failfast=False))

        self.assertTrue(os.path.isdir(os.path.join(project_dir, '_build')),
                        'solid build did not publish a build directory')
