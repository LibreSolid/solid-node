# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import os
import sys
from multiprocessing import Process

from solid_node.core.builder import Builder, BuildOutcome, BuildSession


MODEL_NOT_FOUND = 66


class Build:
    """Build a node once and publish its complete current artifacts."""

    needs_node = True

    def add_arguments(self, parser):
        pass

    def builder(self, build_dir, published_build_dir):
        Builder(
            self.path,
            build_dir=build_dir,
            published_build_dir=published_build_dir,
            watch=False,
            lifecycle=True,
        ).start()

    def handle(self, args):
        self.path = args.path
        if not os.path.isfile(self.path):
            sys.stderr.write(f'Model not found: {self.path}\n')
            sys.exit(MODEL_NOT_FOUND)

        session = BuildSession()
        try:
            while True:
                proc = Process(
                    target=self.builder,
                    args=(session.staging_dir, session.build_dir),
                )
                proc.start()
                proc.join()
                if proc.exitcode == BuildOutcome.RENDERED.value:
                    continue
                if proc.exitcode == BuildOutcome.CURRENT.value:
                    return
                sys.exit(proc.exitcode or BuildOutcome.FAILED.value)
        finally:
            session.discard()
