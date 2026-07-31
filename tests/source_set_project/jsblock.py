# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import JScadNode


class JsBlock(JScadNode):
    """A jscad leaf, used to prove the adapter does not respawn the
    external renderer for an artifact that is already current. The
    tests mock Popen, so the jscad CLI is not required to run them.
    """

    jscad_source = 'jsblock.js'
