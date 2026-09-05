# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
import sys
from importlib import import_module

#: Command name -> the module and class that implement it, in the order
#: `solid -h` lists them.
#:
#: The table holds locations rather than instances because almost nothing
#: the CLI does needs a command object. The migration guard, the subparser
#: names, and argparse's invalid-choice report all work from names alone,
#: and every one of them used to cost seven module imports -- including
#: `cadquery`, reached through the node package. `manage()` now imports the
#: one command it is about to run.
#:
#: Naming the class in a string is what makes that possible, and it is also
#: the one risk: a rename or a move fails when that command is invoked
#: rather than when the CLI loads. tests/test_cli_lazy_imports.py walks the
#: whole table once so the failure lands in the suite instead.
COMMANDS = {
    'build': ('solid_node.manager.build', 'Build'),
    'develop': ('solid_node.manager.develop', 'Develop'),
    'test': ('solid_node.manager.test', 'Test'),
    'snapshot': ('solid_node.manager.snapshot', 'Snapshot'),
    'new': ('solid_node.manager.new', 'New'),
    'export': ('solid_node.manager.export', 'Export'),
    'viewer': ('solid_node.manager.viewer', 'Viewer'),
    'models': ('solid_node.manager.models', 'Models'),
}

#: The tokens that make the top-level parser print its own help. That is the
#: one output that depends on every command, so it is the one path allowed
#: to load them all.
HELP_FLAGS = ('-h', '--help')


def load_dotenv():
    """Load KEY=value lines from ./.env into os.environ.

    Real environment variables take precedence. This is how worktrees
    created by scripts/dev-env get their own ports (SOLID_NODE_PORT,
    SOLID_NODE_FRONTEND_PORT).
    """
    if not os.path.isfile('.env'):
        return
    with open('.env') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip())


def resolve_command(name):
    """Import a command's module and return an instance of its class.

    A failing import is left to propagate: a broken installation should say
    which module it could not load, not disappear into a missing command.
    """
    module, class_name = COMMANDS[name]
    return getattr(import_module(module), class_name)()


def add_command_parser(subparsers, name, command):
    """Register `command` under `name` with its help, options and, when it
    operates on a node, the shared `reference` positional."""
    command_parser = subparsers.add_parser(
        name,
        help=command.__doc__,
    )
    if getattr(command, 'needs_node', True):
        command_parser.add_argument(
            'path', nargs='?',
            type=str,
            metavar='reference',
            help='Node reference: a declared model name, package.module:Class, path/to/file.py, or path/to/file.py:Class',
        )
        # Registered once, here, beside the reference it applies to: every
        # command that loads a node takes the root's parameters the same
        # way, and none re-declares the flag.
        command_parser.add_argument(
            '--set', action='append', default=[], metavar='NAME=VALUE',
            help='Set a declared parameter of the root node, parsed by its '
                 'kind (repeatable)',
        )
    command.add_arguments(command_parser)
    return command_parser


def manage():
    """
    Runs cli commands, available in managers.* namespace
    """
    load_dotenv()

    # Old grammar was `solid <path> <command>`. If it looks like someone is
    # still using that order, fail fast with a clear hint instead of
    # silently misinterpreting the path as a command name.
    if len(sys.argv) > 2 and sys.argv[1] not in COMMANDS and sys.argv[2] in COMMANDS:
        sys.stderr.write(
            "The CLI grammar changed in 0.4: commands come first. "
            "Try: solid {command} {path} [options]\n"
        )
        sys.exit(2)

    parser = argparse.ArgumentParser(description='Solid Node')

    subparsers = parser.add_subparsers(
        dest='command',

        title='Commands',
        description='Pick an action to do on Node',
        help='use -h {command} for more options',
    )

    # The grammar puts the command first, but argparse also honours a `--`
    # before it, so take the first token that names a command rather than
    # assuming a position. No top-level option takes a value, so no earlier
    # token can be an option's argument that happens to spell a command.
    selected = next((arg for arg in sys.argv[1:] if arg in COMMANDS), None)

    if selected is not None:
        resolved = {selected: resolve_command(selected)}
    elif len(sys.argv) == 1 or sys.argv[1] in HELP_FLAGS:
        # Each command's help is its docstring, and only the class carries
        # it. `solid -h` therefore costs what it always cost; nothing
        # automated runs it, and duplicating seven docstrings into the table
        # to avoid that would only invite them to drift.
        resolved = {name: resolve_command(name) for name in COMMANDS}
    else:
        # An unknown command. argparse reports it against the registered
        # names, which is the same error as before with nothing loaded.
        resolved = {}

    for name in COMMANDS:
        command = resolved.get(name)
        if command is None:
            # A name for argparse to match and to list; the options behind
            # it belong to an invocation that is not happening.
            subparsers.add_parser(name)
        else:
            add_command_parser(subparsers, name, command)

    args = parser.parse_args()

    if args.command is None:
        return parser.print_help()

    command = resolved[args.command]

    if getattr(command, 'needs_node', True) and args.path and os.path.isdir(args.path):
        parser.error('A directory is not a node reference; use a declared model name, package.module:Class, path/to/file.py, or path/to/file.py:Class')

    command.handle(args)
