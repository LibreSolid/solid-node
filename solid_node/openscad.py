# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Conditional availability contract for the OpenSCAD executable."""

import shutil
from functools import lru_cache


class OpenScadUnavailable(RuntimeError):
    """A requested operation cannot run without the OpenSCAD binary."""

    def __init__(self, needed_by, reason, alternative=None):
        remedy = "install OpenSCAD and ensure 'openscad' is on PATH"
        if alternative:
            remedy = f'{remedy}, or {alternative}'
        super().__init__(
            f'{needed_by} requires the OpenSCAD binary because {reason}; '
            f'{remedy}')


@lru_cache(maxsize=1)
def openscad_binary():
    """Resolve OpenSCAD once for this process, only when a path needs it."""
    return shutil.which('openscad')


def require_openscad(needed_by, reason, alternative=None):
    """Return the executable path or raise one actionable dependency error."""
    binary = openscad_binary()
    if binary is None:
        raise OpenScadUnavailable(needed_by, reason, alternative)
    return binary
