# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import argparse
import os
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
    parser = argparse.ArgumentParser(description='Solid Node')

    parser.add_argument(
        'path',
        type=str,
        help='Path of the python source file for a Node to work on',
    )

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
        command.add_arguments(command_parser)
        index[name] = command

    args = parser.parse_args()

    if args.command is None:
        return parser.print_help()

    if os.path.isdir(args.path):
        args.path = os.path.join(args.path, '__init__.py')

    command = index[args.command]

    command.handle(args)
