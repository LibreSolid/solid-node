# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import sys
import logging
from solid_node.core.loader import load_node
from solid_node.core.export import export_node


logger = logging.getLogger('manager.export')


class Export:
    """Exports a node as a static embeddable artifact: manifest.json
    plus the STL meshes, ready to be served by any static file host."""

    needs_node = True

    def add_arguments(self, parser):
        parser.add_argument(
            '-o', '--output',
            type=str,
            default='export',
            help='Output directory (default: export)',
        )
        parser.add_argument(
            '--fps',
            type=int,
            default=30,
            help='Animation frames per second (default: 30)',
        )
        parser.add_argument(
            '--frames',
            type=int,
            default=360,
            help='Number of frames in one animation cycle, '
                 'the resolution of $t (default: 360)',
        )

    def handle(self, args):
        try:
            node = load_node(args.path)
        except Exception as e:
            sys.stderr.write(f'Error loading node: {e}\n')
            sys.exit(1)

        export_node(node, args.output, fps=args.fps, frames=args.frames)
        print(f'Exported to {args.output}')
