# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Lists the project's models and the state of each one's build."""

import json
import os
import sys

from solid_node.core.loader import ProjectManifestError, read_project


def model_state(build_dir):
    """What the model's build directory says, and nothing more: no node is
    loaded, so currency against the sources is not judged here."""
    if os.path.isfile(os.path.join(build_dir, 'errors.json')):
        return 'failed'
    if os.path.isfile(os.path.join(build_dir, 'viewer.json')):
        return 'published'
    return 'unbuilt'


def describe(project):
    return {
        'root': project.root,
        'build_root': project.build_root,
        'default': project.default.name if project.default else None,
        'models': [{
            'name': model.name,
            'reference': model.reference,
            'default': model is project.default,
            'build_dir': model.build_dir,
            'state': model_state(model.build_dir),
        } for model in project.models],
    }


class Models:
    """Lists the project's models and the state of each one's build."""

    needs_node = False

    def add_arguments(self, parser):
        parser.add_argument(
            '--json', action='store_true',
            help='Print one JSON object a host can read')

    def handle(self, args):
        try:
            project = read_project()
        except ProjectManifestError as error:
            sys.stderr.write(f'Error: {error}\n')
            sys.exit(1)
        report = describe(project)
        if getattr(args, 'json', False):
            print(json.dumps(report))
            return
        for model in report['models']:
            line = f"{model['name'] or '-'}  {model['state']}  {model['reference']}"
            if model['default']:
                line += '  (default)'
            print(line)
