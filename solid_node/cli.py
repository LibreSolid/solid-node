# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
import sys
from solid_node.manager.develop import Develop
from solid_node.manager.test import Test
from solid_node.manager.snapshot import Snapshot

commands = [
    Develop(),
    Test(),
    Snapshot(),
]

def manage():
    """
    Runs cli commands, available in managers.* namespace
    """
    command_names = {command.__class__.__name__.lower() for command in commands}

    # Old grammar was `solid <path> <command>`. If it looks like someone is
    # still using that order, fail fast with a clear hint instead of
    # silently misinterpreting the path as a command name.
    if len(sys.argv) > 2 and sys.argv[1] not in command_names and sys.argv[2] in command_names:
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

    index = {}
    for command in commands:
        name = command.__class__.__name__.lower()
        command_parser = subparsers.add_parser(
            name,
            help=command.__doc__,
        )
        if getattr(command, 'needs_node', True):
            command_parser.add_argument(
                'path',
                type=str,
                help='Path of the python source file for a Node to work on',
            )
        command.add_arguments(command_parser)
        index[name] = command

    args = parser.parse_args()

    if args.command is None:
        return parser.print_help()

    command = index[args.command]

    if getattr(command, 'needs_node', True) and os.path.isdir(args.path):
        args.path = os.path.join(args.path, '__init__.py')

    command.handle(args)
