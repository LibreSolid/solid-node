# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Shared validation for public simulation values stated in seconds."""

import math
from numbers import Real


def finite_seconds(value, what):
    """Return a finite real time value, rejecting bools and text."""
    if (isinstance(value, bool) or not isinstance(value, Real)
            or not math.isfinite(value)):
        raise ValueError(
            f'{what} must be a finite real number of seconds, not {value!r}')
    return value
