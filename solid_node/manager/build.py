# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import traceback

from solid_node.core.builder import Builder, BuildOutcome, write_error
from solid_node.core.loader import (
    AmbiguousNodeError, ProjectManifestError, read_project, resolve_node,
    select_model,
)
from solid_node.core.processes import Process


MODEL_NOT_FOUND = 66


def build_once(path, overrides):
    """One build pass, in its own fresh interpreter.

    Module level, and taking plain values, because the subprocess this runs
    in does not inherit this one's memory -- it is handed this function and
    its arguments to reconstruct. See `solid_node.core.processes`.
    """
    Builder(
        path,
        watch=False,
        lifecycle=True,
        overrides=overrides,
    ).start()


class Build:
    """Build a node once and publish its complete current artifacts."""

    needs_node = True

    def add_arguments(self, parser):
        parser.add_argument(
            '--all', action='store_true',
            help='Build every model the project declares, each into its '
                 'own build directory')

    def handle(self, args):
        self.overrides = list(getattr(args, 'set', None) or [])
        if getattr(args, 'all', False):
            return self.build_all(args.path)
        try:
            selection = select_model(args.path)
        except ProjectManifestError as error:
            sys.stderr.write(f'Model not found: {error}\n')
            sys.exit(MODEL_NOT_FOUND)
        selection.anchor()
        code = self.build(selection.reference)
        if code:
            sys.exit(code)

    def build_all(self, path):
        """Every declared model, in declaration order, each reported as it
        settles. One model's failure does not stop the walk."""
        if path:
            sys.stderr.write('Error: --all takes no reference\n')
            sys.exit(2)
        try:
            project = read_project()
        except ProjectManifestError as error:
            sys.stderr.write(f'Model not found: {error}\n')
            sys.exit(MODEL_NOT_FOUND)
        if not project.named:
            sys.stderr.write(
                f'Error: {project.manifest} declares no models; --all walks '
                f'a [tool.solid-node.models] table\n')
            sys.exit(1)
        failed = []
        for model in project.models:
            select_model(model.name).anchor()
            try:
                code = self.build(model.reference)
            except Exception:
                # The single-model command lets a project's own import error
                # keep its traceback; here it is one model's failure among
                # several, recorded where `solid models` will find it, and
                # the walk goes on.
                message = traceback.format_exc()
                sys.stderr.write(message)
                write_error(message, model.build_dir)
                code = BuildOutcome.FAILED.value
            if code:
                failed.append(model.name)
            sys.stderr.write(
                f'{model.name}: {"current" if not code else f"failed ({code})"}\n')
        sys.exit(1 if failed else 0)

    def build(self, path):
        """One model to completion. Returns 0 when it is current, else
        the exit status the failure deserves."""
        self.path = path
        try:
            resolve_node(self.path)
        except (ProjectManifestError, AmbiguousNodeError) as error:
            # The reference did not name a node. Report why -- an ambiguous
            # file, a class outside the project and a missing file are
            # different problems, and "Model not found" describes only one of
            # them. Anything else is a bug and keeps its traceback.
            sys.stderr.write(f'Model not found: {error}\n')
            return MODEL_NOT_FOUND

        while True:
            proc = Process(target=build_once,
                           args=(self.path, self.overrides))
            proc.start()
            proc.join()
            if proc.exitcode in (BuildOutcome.RENDERED.value,
                                 BuildOutcome.SOURCE_CHANGED.value):
                continue
            if proc.exitcode == BuildOutcome.CURRENT.value:
                return 0
            return proc.exitcode or BuildOutcome.FAILED.value
