# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import os
import shutil
import sys
from importlib import resources


class New:
    """Create a new solid-node project with a starting structure."""

    needs_node = False

    def add_arguments(self, parser):
        parser.add_argument('name', type=str,
                            help='Name of the project directory to create')

    def handle(self, args):
        target = args.name

        if os.path.exists(target):
            sys.stderr.write(f"Error: '{target}' already exists.\n")
            sys.exit(1)

        templates = resources.files('solid_node.manager') / 'templates' / 'project'

        root_dir = os.path.join(target, 'root')
        os.makedirs(root_dir)

        init_src = templates / 'root' / '__init__.py'
        with resources.as_file(init_src) as init_path:
            shutil.copyfile(init_path, os.path.join(root_dir, '__init__.py'))

        gitignore_src = templates / 'gitignore'
        with resources.as_file(gitignore_src) as gitignore_path:
            shutil.copyfile(gitignore_path, os.path.join(target, '.gitignore'))

        print(f"Created new solid-node project at {target}/")
        print()
        print("Next steps:")
        print(f"  cd {target}")
        print("  solid develop root")
        print("  Open http://localhost:8000 in your browser")
