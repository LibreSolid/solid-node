# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import os
import shutil
import sys
import re
from importlib import resources


class New:
    """Create a new solid-node project with a starting structure."""

    needs_node = False

    def add_arguments(self, parser):
        parser.add_argument('name', type=str,
                            help='Name of the project directory to create')

    def handle(self, args):
        origin = args.name
        directory, name = os.path.split(origin.rstrip(os.sep) or origin)

        # The scaffold directory is named after the normalized package, not
        # the raw argument: `solid new snowman-3` must not leave a hyphen in
        # the one path component (the outer directory) the rest of this
        # method does not otherwise touch, while `myproject/pyproject.toml`
        # still declares the same identifier-safe name everywhere else.
        package = re.sub(r'[^0-9A-Za-z_]', '_', name)
        package = package.strip('_') or 'project'
        class_name = ''.join(part.capitalize() for part in package.split('_'))
        target = os.path.join(directory, package) if directory else package

        if os.path.exists(target):
            sys.stderr.write(f"Error: '{target}' already exists.\n")
            sys.exit(1)

        templates = resources.files('solid_node.manager') / 'templates' / 'project'

        package_dir = os.path.join(target, package)
        os.makedirs(package_dir)
        open(os.path.join(package_dir, '__init__.py'), 'w').close()

        module_src = templates / 'root' / '__init__.py'
        with resources.as_file(module_src) as module_path:
            with open(module_path) as source:
                content = source.read().replace('DemoProject', class_name)
        with open(os.path.join(package_dir, f'{package}.py'), 'w') as output:
            output.write(content)

        test_src = templates / 'test.py'
        with resources.as_file(test_src) as test_path:
            with open(test_path) as source:
                test_content = source.read().replace(
                    'DemoProject', class_name)
        with open(os.path.join(package_dir, f'test_{package}.py'), 'w') as output:
            output.write(test_content)

        with open(os.path.join(target, 'pyproject.toml'), 'w') as output:
            output.write('[tool.solid-node]\n')
            output.write(f'model = "{package}.{package}:{class_name}"\n')

        gitignore_src = templates / 'gitignore'
        with resources.as_file(gitignore_src) as gitignore_path:
            shutil.copyfile(gitignore_path, os.path.join(target, '.gitignore'))

        print(f"Created new solid-node project at {target}/")
        print()
        print("Next steps:")
        print(f"  cd {target}")
        print("  solid develop")
        print("  Open http://localhost:8000 in your browser")
