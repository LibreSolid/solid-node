# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from unittest import TestCase
from unittest.mock import patch

from solid_node.cli import manage


class CommandFirstGrammarTest(TestCase):
    """CLI grammar is `solid <command> <node-path>`: the command comes
    first, and the positional `path` argument belongs to the individual
    command's subparser rather than to the top-level parser."""

    def test_develop_parses_and_dispatches_with_path(self):
        with patch.object(sys, 'argv', ['solid', 'develop', 'somefile.py']):
            with patch('solid_node.manager.develop.Develop.handle') as handle:
                manage()

        self.assertTrue(handle.called)
        args = handle.call_args[0][0]
        self.assertEqual(args.path, 'somefile.py')

    def test_build_parses_and_dispatches_with_path(self):
        with patch.object(sys, 'argv', ['solid', 'build', 'somefile.py']):
            with patch('solid_node.manager.build.Build.handle') as handle:
                manage()

        self.assertTrue(handle.called)
        self.assertEqual(handle.call_args[0][0].path, 'somefile.py')

    def test_build_normalizes_directory_path_to_init_file(self):
        with patch.object(sys, 'argv', ['solid', 'build', 'tests/flat_project']):
            with patch('solid_node.manager.build.Build.handle') as handle:
                manage()

        self.assertEqual(handle.call_args[0][0].path,
                         'tests/flat_project/__init__.py')

    def test_build_rejects_callback_option(self):
        with patch.object(sys, 'argv', ['solid', 'build', 'model.py',
                                        '--callback', 'http://listener']):
            with self.assertRaises(SystemExit) as ctx:
                manage()

        self.assertEqual(ctx.exception.code, 2)

    def test_develop_rejects_callback_with_openscad(self):
        with patch.object(sys, 'argv', ['solid', 'develop', 'model.py',
                                        '--openscad', '--callback',
                                        'http://listener']):
            with self.assertRaises(SystemExit) as ctx:
                manage()

        self.assertEqual(ctx.exception.code, 2)

    def test_develop_rejects_callback_with_web_dev(self):
        with patch.object(sys, 'argv', ['solid', 'develop', 'model.py',
                                        '--web-dev', '--callback',
                                        'http://listener']):
            with self.assertRaises(SystemExit) as ctx:
                manage()

        self.assertEqual(ctx.exception.code, 2)

    def test_test_normalizes_directory_path_to_init_file(self):
        with patch.object(sys, 'argv', ['solid', 'test', 'tests/flat_project']):
            with patch('solid_node.manager.test.Test.handle') as handle:
                manage()

        args = handle.call_args[0][0]
        self.assertEqual(
            args.path,
            'tests/flat_project/__init__.py',
        )

    def test_old_order_exits_with_hint(self):
        with patch.object(sys, 'argv', ['solid', 'somefile.py', 'develop']):
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as ctx:
                    manage()

        self.assertEqual(ctx.exception.code, 2)
        self.assertIn('solid {command} {path}', stderr.getvalue())

    def test_no_args_prints_help_and_does_not_crash(self):
        with patch.object(sys, 'argv', ['solid']):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                manage()

        self.assertIn('usage', stdout.getvalue().lower())

    def test_new_dispatches_without_requiring_path(self):
        with patch.object(sys, 'argv', ['solid', 'new', 'myproj']):
            with patch('solid_node.manager.new.New.handle') as handle:
                manage()

        self.assertTrue(handle.called)
        args = handle.call_args[0][0]
        self.assertEqual(args.name, 'myproj')
        self.assertFalse(hasattr(args, 'path'))
