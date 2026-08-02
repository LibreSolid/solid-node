# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Reports the installed viewer bundle and its API version as JSON."""

import json
import sys
from pathlib import Path

from solid_node.viewers.bundle import (
    api_version, bundle_path, has_bundle, missing_bundle_remedy,
)


class Viewer:
    """Reports the installed viewer bundle and its API version as JSON."""

    needs_node = False

    def add_arguments(self, parser):
        pass

    def handle(self, args):
        if not has_bundle():
            sys.stderr.write(missing_bundle_remedy() + '\n')
            sys.exit(1)
        print(json.dumps({
            'path': str(Path(bundle_path()).resolve()),
            'apiVersion': api_version(),
        }))
