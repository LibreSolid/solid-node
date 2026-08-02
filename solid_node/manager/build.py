# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import os
import sys
from multiprocessing import Process

from solid_node.core.builder import Builder, BuildOutcome


MODEL_NOT_FOUND = 66


class Build:
    """Build a node once and publish its complete current artifacts."""

    needs_node = True

    def add_arguments(self, parser):
        pass

    def builder(self):
        Builder(
            self.path,
            watch=False,
            lifecycle=True,
        ).start()

    def handle(self, args):
        self.path = args.path
        if not os.path.isfile(self.path):
            sys.stderr.write(f'Model not found: {self.path}\n')
            sys.exit(MODEL_NOT_FOUND)

        while True:
            proc = Process(target=self.builder)
            proc.start()
            proc.join()
            if proc.exitcode in (BuildOutcome.RENDERED.value,
                                 BuildOutcome.SOURCE_CHANGED.value):
                continue
            if proc.exitcode == BuildOutcome.CURRENT.value:
                return
            sys.exit(proc.exitcode or BuildOutcome.FAILED.value)
