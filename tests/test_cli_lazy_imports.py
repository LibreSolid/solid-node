# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""What a `solid` invocation may import, and what it must still print.

Two things are under test here and they need opposite environments.

*What was imported* is only observable in a process that has not already
imported it, so those assertions run through `tests/import_probe.py` in a
fresh interpreter. Asserting on `sys.modules` in the test runner would
prove nothing: pytest has loaded the whole framework long before a test
body runs.

*What was printed* is a fidelity question, and the honest oracle for
"unchanged from today" is today's algorithm. `reference_parser` below is
the pre-change construction — import every command class, one subparser
each with its `__doc__` as help, the shared `path` positional when
`needs_node` — written out once, independently of the implementation. The
help tests compare `manage()` byte for byte against it, in-process, which
is legitimate because the help path is the one path allowed to load every
command anyway. Rendering both parsers in the same process also pins them
to the same terminal width, so the comparison says something about the
parser rather than about `COLUMNS`.
"""

import argparse
import io
import json
import sys
from contextlib import redirect_stdout
from importlib import import_module
from unittest import TestCase, skipUnless
from unittest.mock import patch

from solid_node.cli import COMMANDS, manage
from solid_node.viewers.bundle import has_bundle

from .import_probe import probe


#: Every command implementation module, spelled independently of the
#: registry: a test that read the registry to decide what may not be
#: imported would pass even if the registry lost an entry.
COMMAND_MODULES = {
    'solid_node.manager.build',
    'solid_node.manager.develop',
    'solid_node.manager.test',
    'solid_node.manager.snapshot',
    'solid_node.manager.new',
    'solid_node.manager.export',
    'solid_node.manager.viewer',
}

#: The order `solid -h` lists commands in, and has listed them in since
#: the command-first flip (ADR-024).
COMMAND_ORDER = ['build', 'develop', 'test', 'snapshot', 'new', 'export',
                 'viewer']

MIGRATION_HINT = ('The CLI grammar changed in 0.4: commands come first. '
                  'Try: solid {command} {path} [options]\n')

DISPATCH = 'from solid_node.cli import manage; manage()\n'


def reference_parser():
    """Build the argparse parser exactly as `manage()` built it before this
    change, importing every command eagerly.

    This is the oracle for "the help is unchanged", so it deliberately does
    not consult anything the implementation could get wrong. Returns the
    top-level parser and the per-command subparsers.
    """
    from solid_node.manager.build import Build
    from solid_node.manager.develop import Develop
    from solid_node.manager.export import Export
    from solid_node.manager.new import New
    from solid_node.manager.snapshot import Snapshot
    from solid_node.manager.test import Test
    from solid_node.manager.viewer import Viewer

    commands = [Build(), Develop(), Test(), Snapshot(), New(), Export(),
                Viewer()]

    # argparse derives `prog` from argv[0], and `manage()` lets it: the
    # reference has to be built under the same argv the comparison runs
    # under, or the usage lines differ for a reason that is not the change.
    with patch.object(sys, 'argv', ['solid']):
        parser = argparse.ArgumentParser(description='Solid Node')
        subparsers = parser.add_subparsers(
            dest='command',

            title='Commands',
            description='Pick an action to do on Node',
            help='use -h {command} for more options',
        )

    built = {}
    for command in commands:
        name = command.__class__.__name__.lower()
        command_parser = subparsers.add_parser(name, help=command.__doc__)
        if getattr(command, 'needs_node', True):
            command_parser.add_argument(
                'path', nargs='?',
                type=str,
                metavar='reference',
                help='Node reference: package.module:Class, path/to/file.py, or path/to/file.py:Class',
            )
            # The root-parameter flag every node-scoped command shares
            # (spec `cli`, root parameter overrides), part of the shape.
            command_parser.add_argument(
                '--set', action='append', default=[], metavar='NAME=VALUE',
                help='Set a declared parameter of the root node, parsed by '
                     'its kind (repeatable)',
            )
        command.add_arguments(command_parser)
        built[name] = command_parser

    return parser, built


def run_help(*argv):
    """Capture what `manage()` prints for a help invocation."""
    stdout = io.StringIO()
    with patch.object(sys, 'argv', ['solid', *argv]):
        with redirect_stdout(stdout):
            try:
                manage()
            except SystemExit as stop:
                assert stop.code in (None, 0), stop.code
    return stdout.getvalue()


def option_strings(parser):
    """Every option spelling a parser accepts, `-h` included."""
    return {string for action in parser._actions
            for string in action.option_strings}


class CommandImportIsolationTest(TestCase):
    """A command's process imports that command's module and no other's."""

    def test_importing_the_cli_loads_no_command_module(self):
        result = probe('import solid_node.cli\n')

        self.assertEqual(result.status, 0, result.stderr)
        self.assertEqual(
            sorted(result.imported_under('solid_node.manager')
                   & COMMAND_MODULES),
            [])

    def test_dispatching_viewer_loads_only_the_viewer_command(self):
        result = probe(DISPATCH, argv=['viewer'])

        self.assertTrue(result.imported('solid_node.manager.viewer'),
                        result.stderr)
        self.assertEqual(
            sorted(COMMAND_MODULES & result.modules),
            ['solid_node.manager.viewer'])

    @skipUnless(has_bundle(), 'no built viewer bundle in this installation')
    def test_dispatching_viewer_still_reports_the_bundle(self):
        """Loading less must not mean answering differently."""
        result = probe(DISPATCH, argv=['viewer'])

        self.assertEqual(result.status, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(sorted(report), ['apiVersion', 'path'])
        self.assertIsInstance(report['apiVersion'], int)

    def test_dispatching_new_loads_only_the_new_command(self):
        """`new` is the non-node command, and takes the other branch of the
        `needs_node` seam; it must be as isolated as `viewer`."""
        result = probe(DISPATCH, argv=['new', '-h'])

        self.assertEqual(result.status, 0, result.stderr)
        self.assertEqual(sorted(COMMAND_MODULES & result.modules),
                         ['solid_node.manager.new'])


class NamesAloneTest(TestCase):
    """The migration guard and the choice validation know command names.
    Neither has any reason to load a command, and neither may."""

    def test_legacy_grammar_exits_two_without_loading_a_command(self):
        result = probe(DISPATCH, argv=['somefile.py', 'develop'])

        self.assertEqual(result.status, 2)
        self.assertEqual(result.stderr, MIGRATION_HINT)
        self.assertEqual(result.stdout, '')
        self.assertEqual(sorted(COMMAND_MODULES & result.modules), [])

    def test_unknown_command_names_the_valid_commands(self):
        result = probe(DISPATCH, argv=['frobnicate'])

        self.assertNotEqual(result.status, 0)
        for name in COMMAND_ORDER:
            self.assertIn(name, result.stderr)
        self.assertEqual(sorted(COMMAND_MODULES & result.modules), [])


class HelpFidelityTest(TestCase):
    """Help output is unchanged: byte for byte against the eager parser."""

    def test_top_level_help_is_byte_identical(self):
        parser, _ = reference_parser()

        self.assertEqual(run_help('-h'), parser.format_help())

    def test_no_subcommand_still_prints_the_same_help(self):
        parser, _ = reference_parser()

        self.assertEqual(run_help(), parser.format_help())

    def test_top_level_help_lists_every_command_with_its_docstring(self):
        """The byte comparison above would also pass if the reference and
        the implementation were both wrong. Name the seven explicitly.

        Whitespace is discarded on both sides because argparse wraps help
        text, and wrapping may break a word on its hyphen (`solid-node`
        becomes `solid-\\nnode`). What is asserted is that each name is
        followed by its own docstring.
        """
        help_text = ''.join(run_help('-h').split())

        for name in COMMAND_ORDER:
            module, class_name = COMMANDS[name]
            command = getattr(import_module(module), class_name)
            expected = name + ''.join(command.__doc__.split())
            self.assertIn(expected, help_text, name)

    def test_help_lists_the_commands_in_registry_order(self):
        self.assertEqual(list(COMMANDS), COMMAND_ORDER)
        self.assertIn(','.join(COMMAND_ORDER), run_help('-h'))

    def test_per_command_help_is_byte_identical(self):
        _, reference = reference_parser()

        for name in COMMAND_ORDER:
            with self.subTest(command=name):
                self.assertEqual(run_help(name, '-h'),
                                 reference[name].format_help())

    def test_develop_help_lists_every_option_develop_accepts(self):
        self._assert_options_listed('develop')

    def test_snapshot_help_lists_every_option_snapshot_accepts(self):
        self._assert_options_listed('snapshot')

    def _assert_options_listed(self, name):
        """Read the option set off the command class itself, then require
        every spelling to appear in what `solid <command> -h` prints. The
        two commands checked this way are the ones with the largest and
        most conditional option sets."""
        _, reference = reference_parser()
        printed = run_help(name, '-h')

        expected = option_strings(reference[name])
        self.assertGreater(len(expected), 1, name)
        for option in expected:
            self.assertIn(option, printed, option)


class RegistryConformanceTest(TestCase):
    """The registry names modules and classes as strings, so a rename or a
    move now fails when that one command is invoked rather than when the
    CLI is imported. This walks every entry once so the whole table is
    proved in one place instead of in production."""

    def test_every_entry_resolves_and_honours_the_duck_typed_contract(self):
        for name, (module, class_name) in COMMANDS.items():
            with self.subTest(command=name):
                command_class = getattr(import_module(module), class_name)
                self.assertEqual(class_name.lower(), name)

                command = command_class()
                self.assertTrue(command.__doc__,
                                'the docstring is the subparser help')
                self.assertTrue(callable(command.add_arguments))
                self.assertTrue(callable(command.handle))
                self.assertIsInstance(getattr(command, 'needs_node', True),
                                      bool)
