# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Fixture projects for the meta-test harness (tests/test_meta.py).

Each module here is a small but REAL solid-node project: real nodes,
real STL builds, real mesh assertions, run end-to-end through
`solid test`. Their node tests are deliberately green (the contract
genuinely holds) or deliberately red (the contract is genuinely
violated), and the meta-tests assert that the runner reports each one
with the correct color, for the correct reason.

These files are not pytest tests themselves — they are excluded from
collection in tests/conftest.py and only ever run inside the
subprocess the meta harness spawns.
"""
