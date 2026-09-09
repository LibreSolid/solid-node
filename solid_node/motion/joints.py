# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""A pair that places a body.

Empty in this cycle (`motion-package`, OpenSpec) by design: naming a
class here now would let the cycle that fills it be written against a
guess. It will hold `Revolute` and `Prismatic` -- a pair, declared on
the node it moves, each owning one coordinate -- filled by cycle 2 of
`workflow/motion/roadmap.md`.
"""
