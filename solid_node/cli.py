import argparse
import os
from solid_node.manager.develop import Develop
from solid_node.manager.test import Test

commands = [
    Develop(),
    Test(),
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
