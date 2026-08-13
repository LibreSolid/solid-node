# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""A minimised reproduction of the gearbox under-merge finding
(openspec/changes/printed-piece-identity/proposal.md): one part placed
several times (RepeatedBolt), plus two differently-named classes whose
render() produces byte-identical geometry (BushingA / BushingB), the
same shape the shop's gearbox project shows for its six bushing classes.
"""

from .bolt import RepeatedBolt
from .bushings import BushingA, BushingB
from .assembly import PiecesAssembly
