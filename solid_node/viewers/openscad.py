# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""OpenSCAD-backed PNG rendering."""

import logging
import os
import shutil
import sys

from solid_node.openscad import require_openscad


logger = logging.getLogger('viewers.openscad')


class OpenScadRenderer:
    def render(self, node, args, output, runner):
        openscad = require_openscad(
            'the OpenSCAD snapshot renderer',
            'rendering the requested image launches OpenSCAD',
            'use --renderer web')
        base_command = self.build_command(node, args, output)
        base_command[0] = openscad
        command = self.wrap_command(base_command)
        logger.info('Rendering %s to %s', node.scad_file, output)
        logger.debug('OpenSCAD command: %s', ' '.join(command))
        result = runner(command, check=True, capture_output=True, text=True)
        if result.stdout:
            logger.debug(result.stdout)

    def build_command(self, node, args, output):
        command = ['openscad', '-o', output]
        if args.camera:
            command.extend(['--camera', args.camera])
        if args.autocenter:
            command.append('--autocenter')
        if args.viewall:
            command.append('--viewall')
        command.extend(['--imgsize', args.imgsize.lower().replace('x', ',')])

        projection = args.projection or 'perspective'
        command.extend(['--projection', 'o' if projection == 'ortho' else 'p'])
        command.extend(['--colorscheme', args.colorscheme or 'Cornfield'])
        if args.preview:
            command.append('--preview')
        if args.view:
            command.extend(['--view', args.view])
        command.append(node.scad_file)
        return command

    def wrap_command(self, command):
        if os.environ.get('DISPLAY'):
            return command
        xvfb_run = self.find_xvfb_run()
        if not xvfb_run:
            sys.stderr.write(
                "Error: no DISPLAY and 'xvfb-run' not found on PATH. "
                "Install xvfb (e.g. `apt-get install -y xvfb`) or run this "
                "command under `xvfb-run -a`.\n"
            )
            raise SystemExit(1)
        return [xvfb_run, '-a'] + command

    def find_xvfb_run(self):
        return shutil.which('xvfb-run')
