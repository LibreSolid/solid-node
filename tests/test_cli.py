# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import io
import os
import sys
from contextlib import redirect_stderr, redirect_stdout
from unittest import TestCase
from unittest.mock import patch

from solid_node.cli import manage


#: The commands that operate on a node (`needs_node`), and the handler each
#: dispatches to. `new` and `viewer` are excluded: they take no reference.
NODE_SCOPED_COMMANDS = {
    'build': 'solid_node.manager.build.Build',
    'develop': 'solid_node.manager.develop.Develop',
    'export': 'solid_node.manager.export.Export',
    'test': 'solid_node.manager.test.Test',
    'snapshot': 'solid_node.manager.snapshot.Snapshot',
}


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

    def test_build_rejects_directory_reference(self):
        with patch.object(sys, 'argv', ['solid', 'build', 'tests/flat_project']):
            with self.assertRaises(SystemExit) as ctx:
                manage()
        self.assertEqual(ctx.exception.code, 2)

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

    def test_develop_accepts_callback_with_no_web(self):
        """An external viewer host wants the rebuild loop and the
        build-ready notification, but not the framework's own viewer."""
        with patch.object(sys, 'argv', ['solid', 'develop', 'model.py',
                                        '--no-web', '--callback',
                                        'http://listener']):
            with patch('solid_node.manager.develop.Develop.handle') as handle:
                manage()

        args = handle.call_args[0][0]
        self.assertTrue(args.no_web)
        self.assertEqual(args.callback, 'http://listener')

    def _assert_no_web_conflict(self, *flags):
        """Exit 2 alone would also be satisfied by argparse rejecting
        `--no-web` as an unrecognized argument, which proves nothing about
        the conflict rule -- so require the error to name the conflict."""
        stderr = io.StringIO()
        with patch.object(sys, 'argv', ['solid', 'develop', 'model.py',
                                        '--no-web', *flags]):
            with redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as ctx:
                    manage()

        self.assertEqual(ctx.exception.code, 2)
        message = stderr.getvalue()
        self.assertNotIn('unrecognized arguments', message)
        self.assertIn('--no-web', message)

    def test_develop_rejects_no_web_with_web(self):
        self._assert_no_web_conflict('--web')

    def test_develop_rejects_no_web_with_web_dev(self):
        self._assert_no_web_conflict('--web-dev')

    def test_develop_rejects_no_web_with_debug_web(self):
        self._assert_no_web_conflict('--debug-web')

    def test_test_rejects_directory_reference(self):
        with patch.object(sys, 'argv', ['solid', 'test', 'tests/flat_project']):
            with self.assertRaises(SystemExit) as ctx:
                manage()
        self.assertEqual(ctx.exception.code, 2)

    def test_node_commands_accept_no_reference(self):
        """Every node-scoped command, not just `build`, may be run bare. The
        positional arrives as None, which is what `resolve_node` reads as
        "use the manifest's model" (proved in test_loader_references)."""
        for command, target in NODE_SCOPED_COMMANDS.items():
            with self.subTest(command=command):
                with patch.object(sys, 'argv', ['solid', command]):
                    with patch(f'{target}.handle') as handle:
                        manage()
                self.assertTrue(handle.called)
                self.assertIsNone(handle.call_args[0][0].path)

    def test_node_commands_reject_a_directory_naming_the_spellings(self):
        """A directory is not a reference. The error has to say what is, or the
        user is left guessing at a grammar that changed under them."""
        directory = os.path.dirname(os.path.abspath(__file__))
        for command, target in NODE_SCOPED_COMMANDS.items():
            with self.subTest(command=command):
                stderr = io.StringIO()
                with patch.object(sys, 'argv', ['solid', command, directory]):
                    with patch(f'{target}.handle') as handle:
                        with redirect_stderr(stderr):
                            with self.assertRaises(SystemExit) as ctx:
                                manage()

                self.assertEqual(ctx.exception.code, 2)
                self.assertFalse(handle.called)
                message = stderr.getvalue()
                self.assertIn('package.module:Class', message)
                self.assertIn('path/to/file.py', message)
                self.assertIn('path/to/file.py:Class', message)

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

    def test_viewer_dispatches_without_requiring_path(self):
        with patch.object(sys, 'argv', ['solid', 'viewer']):
            with patch('solid_node.manager.viewer.Viewer.handle') as handle:
                manage()

        self.assertTrue(handle.called)
        self.assertFalse(hasattr(handle.call_args[0][0], 'path'))
