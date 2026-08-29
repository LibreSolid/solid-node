# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""A valvetrain reduced to the thing the framework could not model: a
spring whose free height is a function of the valve's lift, beside a
rigid retainer that rides on it.

The v8-engine project designed around this absence -- increment 7 states
that "modeling an undeformed decorative spring would create false
interference" -- so the fixture is that geometry, small enough to
evaluate in a test.
"""

from .spring import (Cable, Retainer, Spring, UnportedSpring, Valvetrain,
                     WrongBackendSpring)
