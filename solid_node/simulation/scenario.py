# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Scenario tests: a CAD TestCase that steps its node.

A scenario is an ordinary test method. It asks for a fresh simulation,
scripts events and assertions on it, runs a bounded slice, and asserts
whatever the run produced -- so every CAD assertion the test case
already carries is available at any tick, unchanged.

This base composes rather than integrates. It extends the public CAD
TestCase and needs nothing from the `solid test` runner: the runner
builds the node and binds instant 0 before each method, and a fresh
Sim rebinds the entire snapshot at construction, so the runner's
preparation is harmless and its behaviour needs no change to host a
scenario. The same class therefore runs under plain pytest, where
nothing prepares anything, by building the node itself.

The node is built once per declaring class and shared by that class's
scenarios. Reuse is safe for the reason the whole design rests on:
every render is absolute, so a scenario starting from a fresh state
bank cannot observe what an earlier scenario left behind. Rebuilding
would only pay for STLs again.
"""

from solid_node.test import TestCase

from .sim import Sim


_built_nodes = {}


class ScenarioTest(TestCase):
    """Base for scenario test classes.

    Declare `node` (the assembly class this scenario steps) and `dt`
    (the fixed step, in seconds). Set `meshes = True` when a scenario
    asserts on geometry -- it is what makes the run build STLs, and a
    scenario about state alone should not pay for them.
    """

    node = None
    dt = None
    meshes = False

    def simulation(self, dt=None):
        """A fresh simulation over this scenario's node.

        Fresh per call, never per class: the state bank a simulation
        owns is the whole of what a run mutates, so two scenarios of
        one class share nothing but the geometry they were built from.
        """
        step = self.dt if dt is None else dt
        if step is None:
            raise ValueError(
                f'{type(self).__name__} must declare dt: a scenario is '
                'deterministic because its step size is fixed')
        return Sim(self.scenario_node(), step, meshes=self.meshes)

    def scenario_node(self):
        """The assembly this scenario steps, built once.

        Under the `solid test` runner `node` is already the built
        instance the runner handed over; under pytest it is still the
        declared class, and building it here is what keeps one scenario
        class running under both.
        """
        node = self.node
        if node is None:
            raise ValueError(
                f'{type(self).__name__} must declare node: the assembly '
                'class its scenarios step')
        if isinstance(node, type):
            node = _built_nodes.get(node) or _built_nodes.setdefault(
                node, node())
            # Adopt it exactly as the CAD runner would, so a scenario
            # body reads the same under either runner.
            self.set_node(node)
        return node
