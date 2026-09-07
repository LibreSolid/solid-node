# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""A synthetic corpus tree that deliberately reuses values (ADR-080,
design.md D13).

The existing corpora (`spike/expressions/machine_model.py`,
`tests/expression_project/vocabulary.py`) share little, so this tree pins
the `bindings` table's own semantics rather than the module's vocabulary:

- a value built purely over `$t`, published whole as one operation's
  expression and again, nested, inside another -- so it is bound, and the
  operation naming it whole is the shape a consumer's "an operation whose
  expression is a binding name over `$t` is still a time-dependent
  operation" rule turns on;
- a value built purely over the declared driver `share`, the same way --
  the shape "a binding name is not an undeclared driver id" turns on;
- a value built by ADDING the two together, referenced from more than one
  node's operations, so the table carries an entry naming two earlier
  entries as well as one referenced from several cases.

Not the grasshopper clock (design.md D13): a 31.6 MB corpus committed here
would defeat the change that shrinks it. This tree is small on purpose.
"""

from solid2 import cube

import solid_node.math as m
from solid_node.node import AssemblyNode, Solid2Node
from solid_node.simulation import Driver


class Marker(Solid2Node):
    """A cube. The geometry is not the point."""

    def __init__(self, label, **kwargs):
        super().__init__(label, **kwargs)
        self.label = label

    def render(self):
        return cube(2, center=True)


class SharedValueTree(AssemblyNode):
    """One driver, six markers, and three subexpressions each used more
    than once."""

    share = Driver(default=0, range=(0, 100), unit='step', dtype=int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.time_only = Marker('time_only')
        self.time_nested = Marker('time_nested')
        self.driver_only = Marker('driver_only')
        self.driver_nested = Marker('driver_nested')
        self.combo_a = Marker('combo_a')
        self.combo_b = Marker('combo_b')

    def render(self):
        return [self.time_only, self.time_nested, self.driver_only,
                self.driver_nested, self.combo_a, self.combo_b]

    def simulate(self):
        time_term = m.floor(360.0 * self.time)
        driver_term = self.share * 2.0
        combo = time_term + driver_term

        # `time_term`, whole: the operation whose expression resolves,
        # through the table, to `$t` alone.
        self.time_only.rotate(time_term, [0, 0, 1])
        # `time_term`, nested: what forces it to be shared.
        self.time_nested.rotate(time_term + 1.0, [0, 0, 1])

        # `driver_term`, whole: the operation whose expression resolves,
        # through the table, to a declared driver id alone.
        self.driver_only.rotate(driver_term, [1, 0, 0])
        # `driver_term`, nested.
        self.driver_nested.translate([driver_term, 0, 0])

        # `combo` names both earlier entries, occurs twice in one
        # operation (occurrences, not distinct parents) and again in a
        # second node's operation -- referenced from more than one case.
        self.combo_a.translate([combo, combo, 0])
        self.combo_b.rotate(combo, [0, 1, 0])
