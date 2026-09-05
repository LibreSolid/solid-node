# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Reports the installed viewer bundle and its API version as JSON."""

import json
import sys

from solid_node.viewers.bundle import ViewerUnavailable, describe


class Viewer:
    """Reports the installed viewer bundle and its API version as JSON."""

    needs_node = False

    def add_arguments(self, parser):
        pass

    def handle(self, args):
        try:
            report = describe()
        except ViewerUnavailable as error:
            sys.stderr.write(f'{error}\n')
            sys.exit(1)
        print(json.dumps(report))
