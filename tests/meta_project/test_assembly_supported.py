# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase

from .assembly_supported import AssemblySupported


class AssemblySupportedTest(TestCase):
    node = AssemblySupported

    def test_resting_stack_is_supported(self):
        self.assertAssemblySupported(self.node.stack)

    def test_hanging_hook_is_supported(self):
        self.assertAssemblySupported(self.node.hanging)

    def test_press_fit_is_supported_when_declared(self):
        self.assertAssemblySupported(
            self.node.fitted,
            supports=[(self.node.fitted.block, self.node.fitted.post)])

    def test_mutually_leaning_pair_is_supported_through_the_ground(self):
        self.assertAssemblySupported(self.node.leaning, max_drop=1.5)

    def test_whole_assembly_is_supported_from_its_anchors(self):
        self.assertAssemblySupported(
            self.node,
            ground=[self.node.stack.base, self.node.hanging.post,
                    self.node.fitted.post, self.node.leaning.slab],
            supports=[(self.node.fitted.block, self.node.fitted.post)])
