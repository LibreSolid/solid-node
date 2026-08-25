# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Scenario tests run under the plain pytest suite.

The scenario class itself lives in tests/meta_project/test_axis.py,
where it is the companion test of a node file and therefore reachable
by `solid test`. Importing it here is the whole point: ONE class,
unmodified, collected by both runners. If the scenario base ever came
to depend on something only the CAD runner provides -- a built node,
an instant already selected, a checkpoint restored -- this import is
what would go red.

The class is imported rather than subclassed so that what pytest runs
is byte-for-byte what `solid test` runs.
"""

from .meta_project.test_axis import AxisScenarioTest         # noqa: F401
